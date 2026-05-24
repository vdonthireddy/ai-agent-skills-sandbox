// ==========================================================================
// Application State & Constants
// ==========================================================================
const API_BASE = window.location.origin;
let activeTools = {};
let activeSkills = {};
let activeRegisterType = "skill"; // "tool" or "skill"
let currentRunning = false;

// Templates for the editor
const TOOL_TEMPLATE = `@tool
def double_number(n: int) -> int:
    """
    Doubles the given integer input value.
    
    Args:
        n: The base integer to multiply.
    """
    return n * 2
`;

const SKILL_TEMPLATE = `@skill
def run_math_report(expr1: str, expr2: str) -> str:
    """
    Evaluates two math expressions, compares them, and saves the comparison in storage.
    
    Args:
        expr1: The first math expression.
        expr2: The second math expression.
    """
    # 1. Call low-level calculator tool
    res1 = calculator(expr1)
    res2 = calculator(expr2)
    
    # 2. Compare and draft a report
    comparison = f"Expression '{expr1}' = {res1}. Expression '{expr2}' = {res2}. "
    comparison += f"First is {'larger' if res1 > res2 else 'smaller or equal'}."
    
    # 3. Call low-level browser_storage tool to save state
    browser_storage("SET", "math_comparison", comparison)
    
    return comparison
`;

// Educational Guide Messages per Step Type
const EDUCATIONAL_GUIDE = {
    start: {
        title: "Agent Initialized",
        content: "The agent engine is spinning up! It compiles your registered tools and skills, converts their Python definitions into JSON Schemas, and loads the system prompts into memory.",
        tip: "Watch the connection from 'User Query' to 'LLM Planner' start pulsing."
    },
    thought: {
        title: "LLM Planning Phase",
        content: "The LLM is now analyzing the chat history, system instruction, and schemas. It reasons about what step it needs to take next. If a high-level composite Skill exists (e.g. 'research_city'), it will choose to call it rather than executing multiple low-level tools.",
        tip: "Notice the 'LLM Planner' node is glowing. This represents the model deciding what to do."
    },
    tool_call: {
        title: "Tool Request (Function Call)",
        content: "Instead of raw text, the model returned a structured JSON payload asking to call a function. The model describes which function to call and fills in the arguments dynamically based on its plan.",
        tip: "See the pulse moving from the 'LLM Planner' to the 'Skill Executor'."
    },
    tool_execute: {
        title: "Local Execution (Skill/Tool Run)",
        content: "Your local Python backend intercepted the model's request. It located the decorator-registered function (either a Tool or a Skill workflow) in memory and executed it. If it is a Skill, it coordinates other Tools internally inside Python.",
        tip: "The 'Skill Executor' is highlighted. This represents raw Python code running on your system."
    },
    observation: {
        title: "Feeding Back Context",
        content: "The result of your Python skill/tool is formatted as a special 'tool/function' response message. This is added to the conversational context and sent back to the LLM. The model reads this result to decide its next step.",
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

// Tab switching (Right panel)
const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanes = document.querySelectorAll(".tab-pane");

// Sidebar elements
const tabBtnTools = document.getElementById("tab-btn-tools");
const tabBtnSkills = document.getElementById("tab-btn-skills");
const toolsTab = document.getElementById("tools-tab");
const skillsTab = document.getElementById("skills-tab");
const compileTypeBadge = document.getElementById("compile-type-badge");
const editorFilename = document.getElementById("editor-filename");

// ==========================================================================
// Main Initialization
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    loadCapabilities();
    setupEventListeners();
    updateFlowchartState("idle");
    
    // Set default system prompt template display
    inspectorSystemPrompt.textContent = `You are a helpful AI Agent equipped with local Python tools and composite skills. 
You must solve the user's request step-by-step.
Before calling any tool or skill, explain your reasoning in a clear "Thought:" block.
Prefer using a high-level composite skill if it matches the request.`;
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
            chip.style.transform = "scale(0.95)";
            setTimeout(() => chip.style.transform = "scale(1)", 100);
        });
    });

    // Register Dynamic Skill/Tool
    btnRegisterSkill.addEventListener("click", registerCustomCapability);

    // Sidebar tab switching
    tabBtnTools.addEventListener("click", () => switchSidebarTab("tools"));
    tabBtnSkills.addEventListener("click", () => switchSidebarTab("skills"));

    // Right panel tab switching
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            // Only toggle tab headers that are in the tab-headers row
            btn.parentElement.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(tabId).classList.add("active");
        });
    });
}

// ==========================================================================
// Sidebar Tab Manager
// ==========================================================================
function switchSidebarTab(type) {
    activeRegisterType = type === "tools" ? "tool" : "skill";
    
    if (type === "tools") {
        tabBtnTools.classList.add("active");
        tabBtnSkills.classList.remove("active");
        toolsTab.style.display = "block";
        skillsTab.style.display = "none";
        compileTypeBadge.textContent = "@tool";
        editorFilename.textContent = "custom_tool.py";
        customSkillCode.value = TOOL_TEMPLATE;
    } else {
        tabBtnTools.classList.remove("active");
        tabBtnSkills.classList.add("active");
        toolsTab.style.display = "none";
        skillsTab.style.display = "block";
        compileTypeBadge.textContent = "@skill";
        editorFilename.textContent = "custom_skill.py";
        customSkillCode.value = SKILL_TEMPLATE;
    }
    showRegistrationStatus("info", `Switched editor mode to register dynamic ${activeRegisterType}s.`);
}

// ==========================================================================
// API Operations: Tools & Skills Fetch
// ==========================================================================
async function loadCapabilities() {
    try {
        // 1. Fetch low-level tools
        const toolsResponse = await fetch(`${API_BASE}/api/tools`);
        if (!toolsResponse.ok) throw new Error("Failed to load tools registry.");
        const tools = await toolsResponse.json();
        
        // 2. Fetch high-level skills
        const skillsResponse = await fetch(`${API_BASE}/api/skills`);
        if (!skillsResponse.ok) throw new Error("Failed to load skills registry.");
        const skills = await skillsResponse.json();

        activeTools = {};
        activeSkills = {};
        
        const toolsList = document.getElementById("tools-list");
        const skillsList = document.getElementById("skills-list");
        
        toolsList.innerHTML = "";
        skillsList.innerHTML = "";
        
        // Render Tools
        tools.forEach(t => {
            activeTools[t.name] = t;
            const card = document.createElement("div");
            card.className = "skill-card";
            card.innerHTML = `
                <h3>${t.name}</h3>
                <p>${t.description}</p>
            `;
            card.addEventListener("click", () => {
                document.querySelectorAll(".skill-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                customSkillCode.value = t.source;
                compileTypeBadge.textContent = "@tool";
                editorFilename.textContent = "tools.py";
                activeRegisterType = "tool";
                showRegistrationStatus("info", `Viewing tool: '${t.name}'. You can modify and register it again.`);
            });
            toolsList.appendChild(card);
        });

        // Render Skills
        skills.forEach(s => {
            activeSkills[s.name] = s;
            const card = document.createElement("div");
            card.className = "skill-card";
            card.innerHTML = `
                <h3>${s.name}</h3>
                <p>${s.description}</p>
            `;
            card.addEventListener("click", () => {
                document.querySelectorAll(".skill-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                customSkillCode.value = s.source;
                compileTypeBadge.textContent = "@skill";
                editorFilename.textContent = "skills.py";
                activeRegisterType = "skill";
                showRegistrationStatus("info", `Viewing composite skill: '${s.name}'. You can modify and register it again.`);
            });
            skillsList.appendChild(card);
        });

        // Update total counter
        activeSkillsCount.textContent = `${tools.length} Tools & ${skills.length} Skills Active`;
        
        // Update combined schema inspector list
        const combinedSchemas = [];
        tools.forEach(t => {
            combinedSchemas.push({
                name: t.name,
                type: "Atomic Tool",
                description: t.description,
                parameters: t.parameters
            });
        });
        skills.forEach(s => {
            combinedSchemas.push({
                name: s.name,
                type: "Composite Skill",
                description: s.description,
                parameters: s.parameters
            });
        });
        inspectorSchemas.textContent = JSON.stringify(combinedSchemas, null, 2);

    } catch (error) {
        document.getElementById("tools-list").innerHTML = `<div class="alert-box error">Error: ${error.message}</div>`;
    }
}

async function registerCustomCapability() {
    const code = customSkillCode.value;
    btnRegisterSkill.disabled = true;
    showRegistrationStatus("info", `Compiling dynamic ${activeRegisterType} code on backend...`);
    
    const endpoint = activeRegisterType === "tool" ? "/api/tools" : "/api/skills";
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code })
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || "Error compiling code.");
        }
        
        showRegistrationStatus("success", `Success! Dynamic ${activeRegisterType} compiled and registered.`);
        writeToConsole("system", `Registered custom Python ${activeRegisterType} successfully.`);
        loadCapabilities(); // Refresh sidebar lists
    } catch (error) {
        showRegistrationStatus("error", error.message);
        writeToConsole("error", `Failed to register ${activeRegisterType}: ${error.message}`);
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

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop();

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
            writeToConsole("tool_call", `Calling capability '${step.name}' with arguments: ${argsStr}`);
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
    if (type === "final_answer") {
        msg.innerHTML = text.replace(/\n/g, "<br>");
    } else {
        msg.textContent = text;
    }
    consoleLogs.appendChild(msg);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

function updateFlowchartState(state, info = "") {
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
        
        nodeExecutor.querySelector(".node-sub").textContent = info;
        flowStateLabel.textContent = `State: LLM invoking '${info}'`;
    }
    else if (state === "tool_execute") {
        nodeExecutor.classList.add("active");
        pathToolReason.classList.add("active");
        flowStateLabel.textContent = "State: Local Python execution running";
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

function updateEduCard(stepType) {
    const cardData = EDUCATIONAL_GUIDE[stepType];
    if (!cardData) return;
    
    eduTitle.style.opacity = 0;
    eduContent.style.opacity = 0;
    
    setTimeout(() => {
        eduTitle.textContent = cardData.title;
        eduContent.innerHTML = `${cardData.content}<br><br><span style="color:#fde68a;">💡 ${cardData.tip}</span>`;
        eduTitle.style.opacity = 1;
        eduContent.style.opacity = 1;
    }, 150);
}
