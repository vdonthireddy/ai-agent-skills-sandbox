// ==========================================================================
// Application State & Constants
// ==========================================================================
const API_BASE = window.location.origin;
let activeSkills = {};
let currentRunning = false;

// Educational Guide Messages per Step Type
const EDUCATIONAL_GUIDE = {
    start: {
        title: "Agent Initialized",
        content: "The agent engine is spinning up! It compiles your registered skills, converts their Python definitions into JSON Schemas, and loads the system prompts into memory.",
        tip: "Watch the connection from 'User Query' to 'LLM Planner' start pulsing."
    },
    thought: {
        title: "LLM Planning Phase",
        content: "The LLM is now analyzing the chat history, system instruction, and tool schemas. It reasons about what step it needs to take next to answer your query. It does not guess data if a tool is available.",
        tip: "Notice the 'LLM Planner' node is glowing. This represents the model deciding what to do."
    },
    tool_call: {
        title: "Tool Request (Function Call)",
        content: "Instead of raw text, the model returned a structured JSON payload asking to call a function. The model describes which function to call and fills in the arguments dynamically based on its plan.",
        tip: "See the pulse moving from the 'LLM Planner' to the 'Skill Executor'."
    },
    tool_execute: {
        title: "Local Execution (Skill Execution)",
        content: "Your local Python backend intercepted the model's request. It located the decorator-registered function in memory, ran the actual Python code with the model's arguments, and grabbed the result.",
        tip: "The 'Skill Executor' is highlighted. This represents raw Python code running on your system."
    },
    observation: {
        title: "Feeding Back Context",
        content: "The result of your Python skill is formatted as a special 'tool/function' response message. This is added to the conversational context and sent back to the LLM. The model reads this result to decide its next step.",
        tip: "Watch the loop pulse travel from the 'Skill Executor' back to the 'LLM Planner'."
    },
    final_answer: {
        title: "Final Answer Generation",
        content: "The LLM analyzed all steps, saw that it has enough information, and generated the final text response to the user. The loop terminates.",
        tip: "The flowchart glows all the way to the 'Answer' node, signifying success!"
    },
    api_request: {
        title: "API Payload Logs",
        content: "We intercepted the raw JSON package sent to the Gemini endpoint. Inspect the 'LLM Context' and 'Raw JSON Logs' panels to see how the model receives tools.",
        tip: "Open the 'Raw JSON Logs' tab on the right to inspect the exact payload structure."
    }
};

// ==========================================================================
// DOM Elements
// ==========================================================================
const modeToggle = document.getElementById("mode-toggle");
const apiKeyContainer = document.getElementById("api-key-container");
const geminiApiKey = document.getElementById("gemini-api-key");
const skillsList = document.getElementById("skills-list");
const activeSkillsCount = document.getElementById("active-skills-count");
const customSkillCode = document.getElementById("custom-skill-code");
const btnRegisterSkill = document.getElementById("btn-register-skill");
const registrationStatus = document.getElementById("registration-status");
const consoleLogs = document.getElementById("console-logs");
const btnClearConsole = document.getElementById("btn-clear-console");
const userPrompt = document.getElementById("user-prompt");
const btnRunAgent = document.getElementById("btn-run-agent");
const templateChips = document.querySelectorAll(".template-chip");

// SVG Flow elements
const nodeInput = document.getElementById("node-input");
const nodeReasoner = document.getElementById("node-reasoner");
const nodeExecutor = document.getElementById("node-executor");
const nodeOutput = document.getElementById("node-output");
const pathInputReason = document.getElementById("path-input-reason");
const pathReasonTool = document.getElementById("path-reason-tool");
const pathToolReason = document.getElementById("path-tool-reason");
const pathReasonOutput = document.getElementById("path-reason-output");
const flowStateLabel = document.getElementById("flow-state-label");

// Inspector elements
const inspectorSystemPrompt = document.getElementById("inspector-system-prompt");
const inspectorSchemas = document.getElementById("inspector-schemas");
const inspectorRequest = document.getElementById("inspector-request");
const inspectorResponse = document.getElementById("inspector-response");

// Edu elements
const eduTitle = document.getElementById("edu-title");
const eduContent = document.getElementById("edu-content");

// Tab switching
const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanes = document.querySelectorAll(".tab-pane");

// ==========================================================================
// Main Initialization
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    loadSkills();
    setupEventListeners();
    updateFlowchartState("idle");
    
    // Set default system prompt template display
    inspectorSystemPrompt.textContent = `You are a helpful AI Agent equipped with local Python skills (tools). 
You must solve the user's request step-by-step.
Before calling any tool, explain your reasoning in a clear "Thought:" block.
Always use the tools available to gather information. Do not guess values.`;
});

// ==========================================================================
// Event Listeners Setup
// ==========================================================================
function setupEventListeners() {
    // Mode toggling (simulation vs live)
    modeToggle.addEventListener("change", (e) => {
        if (e.target.value === "live") {
            apiKeyContainer.style.display = "block";
            writeToConsole("system", "Switched to Live Gemini API Mode. Please enter your Gemini API Key to make live calls.");
        } else {
            apiKeyContainer.style.display = "none";
            writeToConsole("system", "Switched to Simulation Mode. Using local heuristics with dynamic skill execution.");
        }
    });

    // Clear Console
    btnClearConsole.addEventListener("click", () => {
        consoleLogs.innerHTML = `<div class="system-message">Console cleared. Ready.</div>`;
    });

    // Run Agent Click
    btnRunAgent.addEventListener("click", runAgentLoop);
    
    // Prompt Input Enter key
    userPrompt.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !currentRunning) {
            runAgentLoop();
        }
    });

    // Template chip selections
    templateChips.forEach(chip => {
        chip.addEventListener("click", () => {
            if (currentRunning) return;
            userPrompt.value = chip.getAttribute("data-prompt");
            // Micro animation
            chip.style.transform = "scale(0.95)";
            setTimeout(() => chip.style.transform = "scale(1)", 100);
        });
    });

    // Register Dynamic Skill
    btnRegisterSkill.addEventListener("click", registerCustomSkill);

    // Tab switching
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            tabButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(tabId).classList.add("active");
        });
    });
}

// ==========================================================================
// API Operations: Skills Management
// ==========================================================================
async function loadSkills() {
    try {
        const response = await fetch(`${API_BASE}/api/skills`);
        if (!response.ok) throw new Error("Failed to load skills list.");
        
        const skills = await response.json();
        activeSkills = {};
        skillsList.innerHTML = "";
        
        if (skills.length === 0) {
            skillsList.innerHTML = `<div class="loading-spinner">No registered skills found.</div>`;
            activeSkillsCount.textContent = "0 Skills Active";
            return;
        }

        activeSkillsCount.textContent = `${skills.length} Python Skills Active`;
        
        // Save to cache and render
        skills.forEach(skill => {
            activeSkills[skill.name] = skill;
            
            const card = document.createElement("div");
            card.className = "skill-card";
            card.innerHTML = `
                <h3>${skill.name}</h3>
                <p>${skill.description}</p>
            `;
            
            card.addEventListener("click", () => {
                // Highlight active skill card
                document.querySelectorAll(".skill-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                
                // Show source code and schema details in the panels
                customSkillCode.value = skill.source;
                showRegistrationStatus("info", `Viewing registered skill: '${skill.name}'. You can modify and register it again.`);
            });
            
            skillsList.appendChild(card);
        });

        // Update inspector schemas display
        const schemasOnly = skills.map(s => {
            return {
                name: s.name,
                description: s.description,
                parameters: s.parameters
            };
        });
        inspectorSchemas.textContent = JSON.stringify(schemasOnly, null, 2);

    } catch (error) {
        skillsList.innerHTML = `<div class="alert-box error">Error loading skills: ${error.message}</div>`;
    }
}

async function registerCustomSkill() {
    const code = customSkillCode.value;
    btnRegisterSkill.disabled = true;
    showRegistrationStatus("info", "Compiling python code on backend...");
    
    try {
        const response = await fetch(`${API_BASE}/api/skills`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code })
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || "Error compiling code.");
        }
        
        showRegistrationStatus("success", "Success! Code compiled and registered in the active agent memory.");
        writeToConsole("system", `Registered custom Python skill code successfully.`);
        loadSkills(); // Refresh sidebar list
    } catch (error) {
        showRegistrationStatus("error", error.message);
        writeToConsole("error", `Failed to register skill: ${error.message}`);
    } finally {
        btnRegisterSkill.disabled = false;
    }
}

function showRegistrationStatus(type, message) {
    registrationStatus.style.display = "block";
    registrationStatus.className = `alert-box ${type}`;
    registrationStatus.textContent = message;
}

// ==========================================================================
// Agent Loop Execution & Chunk Streaming
// ==========================================================================
async function runAgentLoop() {
    const prompt = userPrompt.value.trim();
    if (!prompt) return;

    const mode = modeToggle.value;
    const apiKey = geminiApiKey.value.trim();

    if (mode === "live" && !apiKey) {
        writeToConsole("error", "API Key required for Live Gemini Mode. Enter a key in the status bar.");
        return;
    }

    // Set state
    currentRunning = true;
    btnRunAgent.disabled = true;
    btnRunAgent.querySelector(".spinner").style.display = "block";
    btnRunAgent.querySelector(".btn-text").textContent = "Running Loop...";
    
    writeToConsole("system", `Starting Agent execution loop. Prompt: "${prompt}"`);
    updateFlowchartState("start");
    updateEduCard("start");

    try {
        const response = await fetch(`${API_BASE}/api/agent/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                prompt,
                mode,
                api_key: mode === "live" ? apiKey : null
            })
        });

        if (!response.ok) {
            let errorMessage = "Backend execution failed.";
            try {
                const errJson = await response.json();
                if (errJson && errJson.detail) {
                    if (typeof errJson.detail === "string") {
                        errorMessage = errJson.detail;
                    } else if (Array.isArray(errJson.detail)) {
                        errorMessage = errJson.detail.map(err => {
                            const locStr = err.loc ? err.loc.join('.') : 'error';
                            return `${locStr}: ${err.msg}`;
                        }).join(', ');
                    } else {
                        errorMessage = JSON.stringify(errJson.detail);
                    }
                }
            } catch (jsonErr) {
                errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }

        // Read chunked HTTP SSE streams
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop(); // Hold onto uncompleted line

            for (const line of lines) {
                if (line.trim().startsWith("data: ")) {
                    try {
                        const stepData = JSON.parse(line.trim().slice(6));
                        processAgentStep(stepData);
                    } catch (e) {
                        console.error("SSE parse error", e, line);
                    }
                }
            }
        }
    } catch (error) {
        writeToConsole("error", error.message);
        updateFlowchartState("error");
    } finally {
        // Reset states
        currentRunning = false;
        btnRunAgent.disabled = false;
        btnRunAgent.querySelector(".spinner").style.display = "none";
        btnRunAgent.querySelector(".btn-text").textContent = "Execute Agent Loop";
    }
}

// ==========================================================================
// Console & Flowchart UI State Machine
// ==========================================================================
function processAgentStep(step) {
    const type = step.type;
    const content = step.content;

    switch (type) {
        case "thought":
            writeToConsole("thought", content);
            updateFlowchartState("thought");
            updateEduCard("thought");
            break;
            
        case "tool_call":
            const argsStr = JSON.stringify(step.args);
            writeToConsole("tool_call", `Calling skill '${step.name}' with arguments: ${argsStr}`);
            updateFlowchartState("tool_call", step.name);
            updateEduCard("tool_call");
            break;
            
        case "tool_execute":
            writeToConsole("tool_execute", `Outcome = ${step.output}`);
            updateFlowchartState("tool_execute");
            updateEduCard("tool_execute");
            break;
            
        case "final_answer":
            writeToConsole("final_answer", content);
            updateFlowchartState("final_answer");
            updateEduCard("final_answer");
            break;
            
        case "api_request":
            inspectorRequest.textContent = content;
            // Force focus on JSON Logs tab when requests happen
            document.querySelector("[data-tab='json-view']").click();
            updateEduCard("api_request");
            break;
            
        case "api_response":
            inspectorResponse.textContent = content;
            break;
            
        case "error":
            writeToConsole("error", content);
            updateFlowchartState("error");
            break;
            
        default:
            console.log("Unknown step type", step);
    }
}

function writeToConsole(type, text) {
    const msg = document.createElement("div");
    msg.className = `agent-${type}`;
    
    // Replace newlines with breaks for final answer block readability
    if (type === "final_answer") {
        msg.innerHTML = text.replace(/\n/g, "<br>");
    } else {
        msg.textContent = text;
    }
    
    consoleLogs.appendChild(msg);
    // Smooth scroll console container
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

// Visual State Flow manager for the SVG flowchart
function updateFlowchartState(state, info = "") {
    // Reset all paths and nodes
    const paths = [pathInputReason, pathReasonTool, pathToolReason, pathReasonOutput];
    const nodes = [nodeInput, nodeReasoner, nodeExecutor, nodeOutput];
    
    paths.forEach(p => p.classList.remove("active"));
    nodes.forEach(n => n.classList.remove("active", "executing", "success"));
    
    nodeExecutor.querySelector(".node-sub").textContent = "Python Code";

    if (state === "idle") {
        nodeInput.classList.add("active");
        flowStateLabel.textContent = "State: Idle / Waiting for query";
    }
    else if (state === "start") {
        nodeInput.classList.add("active");
        pathInputReason.classList.add("active");
        flowStateLabel.textContent = "State: Initializing Prompt Turn";
    }
    else if (state === "thought") {
        nodeReasoner.classList.add("active");
        flowStateLabel.textContent = "State: LLM reasoning and planning";
    }
    else if (state === "tool_call") {
        nodeReasoner.classList.add("active");
        nodeExecutor.classList.add("executing");
        pathReasonTool.classList.add("active");
        
        // Show active skill name
        nodeExecutor.querySelector(".node-sub").textContent = info;
        flowStateLabel.textContent = `State: LLM calling skill '${info}'`;
    }
    else if (state === "tool_execute") {
        nodeExecutor.classList.add("active");
        pathToolReason.classList.add("active");
        flowStateLabel.textContent = "State: Local Python function executing";
    }
    else if (state === "final_answer") {
        nodeReasoner.classList.add("active");
        nodeOutput.classList.add("success");
        pathReasonOutput.classList.add("active");
        flowStateLabel.textContent = "State: Done! Final answer compiled";
    }
    else if (state === "error") {
        flowStateLabel.textContent = "State: Execution Encountered Error";
    }
}

// Updates educational documentation dynamically to match current step context
function updateEduCard(stepType) {
    const cardData = EDUCATIONAL_GUIDE[stepType];
    if (!cardData) return;
    
    // Add micro fade-in animation
    eduTitle.style.opacity = 0;
    eduContent.style.opacity = 0;
    
    setTimeout(() => {
        eduTitle.textContent = cardData.title;
        eduContent.innerHTML = `${cardData.content}<br><br><span style="color:#fde68a;">💡 ${cardData.tip}</span>`;
        eduTitle.style.opacity = 1;
        eduContent.style.opacity = 1;
    }, 150);
}
