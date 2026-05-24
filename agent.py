import json
import time
import requests
import re
from typing import Generator, Dict, Any, List

from tools import tool_registry
from skills import skill_registry

SYSTEM_PROMPT = """You are a helpful AI Agent equipped with local Python tools and composite skills. 
You must solve the user's request step-by-step.
Before calling any tool or skill, explain your reasoning in a clear "Thought:" block.
Prefer using a high-level composite skill if it matches the request, as it coordinates multiple tools automatically.
Always use the tools/skills available to gather information. Do not guess values.
Format your thought and function calls clearly.
"""

def extract_city(text: str) -> str:
    """Helper to extract a city name from text."""
    cities = ["tokyo", "london", "san francisco", "new york", "paris", "sydney"]
    text_lower = text.lower()
    for city in cities:
        if city in text_lower:
            return city.title()
    match = re.search(r'in\s+([a-zA-Z\s]+?)(?:\s+and|\s+is|\s+to|\s+report|\s*\.|\s*$)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return "Paris"

def run_agent_simulated(prompt: str) -> Generator[Dict[str, Any], None, None]:
    """
    Simulates the agent loop dynamically using heuristics.
    Executes actual Python tools/skills under the hood.
    """
    yield {
        "step": 1,
        "type": "thought",
        "content": f"Initializing simulated agent. Prompt: '{prompt}'. Scanning Tool & Skill Registries..."
    }
    time.sleep(1.0)
    
    prompt_lower = prompt.lower()
    
    # New Scenario: Travel Research Report (Exposes the high-level Skill workflow)
    if "report" in prompt_lower and ("city" in prompt_lower or "travel" in prompt_lower or any(c in prompt_lower for c in ["tokyo", "london", "san francisco", "new york", "paris", "sydney"])):
        city = extract_city(prompt)
        yield {
            "step": 2,
            "type": "thought",
            "content": f"The user wants a full travel research report on {city}. Instead of calling get_weather, calculator, and browser_storage manually one-by-one, I will call the high-level composite skill 'research_city' which automates this entire workflow in one step."
        }
        time.sleep(1.2)
        
        yield {
            "step": 3,
            "type": "tool_call",
            "name": "research_city",
            "args": {"city": city}
        }
        time.sleep(1.0)
        
        try:
            # Execute the composite skill
            skill_res = skill_registry.skills["research_city"]["func"](city=city)
            yield {
                "step": 4,
                "type": "tool_execute",
                "name": "research_city",
                "output": skill_res
            }
            time.sleep(1.2)
            
            yield {
                "step": 5,
                "type": "thought",
                "content": f"The 'research_city' skill completed successfully. It gathered the weather, converted temp, compiled the outline, and saved it under '{city.lower()}_travel_report'. I will output the final summary."
            }
            time.sleep(1.0)
            
            yield {
                "step": 6,
                "type": "final_answer",
                "content": f"I executed the composite skill 'research_city' for {city}. The skill automatically executed the low-level weather, calculator, and database storage tools on the backend. The report is saved. (Executed composite python skill in Simulation Mode)"
            }
            
        except Exception as e:
            yield {
                "step": 4,
                "type": "error",
                "content": f"Error running composite skill research_city: {str(e)}"
            }
            
    # Scenario A: Weather + Calculation (sequential tools)
    elif "weather" in prompt_lower and ("square" in prompt_lower or "calculate" in prompt_lower or "math" in prompt_lower or "multiply" in prompt_lower or "*" in prompt_lower):
        city = extract_city(prompt)
        yield {
            "step": 2,
            "type": "thought",
            "content": f"The user wants the weather in {city} and a calculation. I will call the 'get_weather' tool."
        }
        time.sleep(1.2)
        
        yield {
            "step": 3,
            "type": "tool_call",
            "name": "get_weather",
            "args": {"city": city}
        }
        time.sleep(1.0)
        
        try:
            weather_res = tool_registry.tools["get_weather"]["func"](city=city)
            temp_match = re.search(r'(\d+)°C', weather_res)
            temp = float(temp_match.group(1)) if temp_match else 15.0
            
            yield {
                "step": 4,
                "type": "tool_execute",
                "name": "get_weather",
                "output": weather_res
            }
            time.sleep(1.2)
            
            yield {
                "step": 5,
                "type": "thought",
                "content": f"Temperature in {city} is {temp}°C. Now I will evaluate the square of this value ({temp} * {temp}) using the 'calculator' tool."
            }
            time.sleep(1.2)
            
            expression = f"{temp} * {temp}"
            yield {
                "step": 6,
                "type": "tool_call",
                "name": "calculator",
                "args": {"expression": expression}
            }
            time.sleep(1.0)
            
            calc_res = tool_registry.tools["calculator"]["func"](expression=expression)
            yield {
                "step": 7,
                "type": "tool_execute",
                "name": "calculator",
                "output": str(calc_res)
            }
            time.sleep(1.2)
            
            yield {
                "step": 8,
                "type": "thought",
                "content": "Calculations complete. Ready for final output."
            }
            time.sleep(1.0)
            
            yield {
                "step": 9,
                "type": "final_answer",
                "content": f"The weather in {city} is currently {temp}°C. Squaring this temperature value gives {calc_res}."
            }
            
        except Exception as e:
            yield {
                "step": 4,
                "type": "error",
                "content": f"Error running weather calculation pipeline: {str(e)}"
            }
            
    # Scenario B: Weather + Database Storage (sequential tools)
    elif "weather" in prompt_lower and ("store" in prompt_lower or "save" in prompt_lower or "storage" in prompt_lower or "db" in prompt_lower):
        city = extract_city(prompt)
        yield {
            "step": 2,
            "type": "thought",
            "content": f"The request requires fetching the weather in {city} and saving it. Let's retrieve the weather first."
        }
        time.sleep(1.2)
        
        yield {
            "step": 3,
            "type": "tool_call",
            "name": "get_weather",
            "args": {"city": city}
        }
        time.sleep(1.0)
        
        try:
            weather_res = tool_registry.tools["get_weather"]["func"](city=city)
            yield {
                "step": 4,
                "type": "tool_execute",
                "name": "get_weather",
                "output": weather_res
            }
            time.sleep(1.2)
            
            storage_key = f"{city.lower()}_weather"
            yield {
                "step": 5,
                "type": "thought",
                "content": f"Weather reports: '{weather_res}'. I need to save this using the 'browser_storage' tool."
            }
            time.sleep(1.2)
            
            yield {
                "step": 6,
                "type": "tool_call",
                "name": "browser_storage",
                "args": {"action": "SET", "key": storage_key, "value": weather_res}
            }
            time.sleep(1.0)
            
            store_res = tool_registry.tools["browser_storage"]["func"](action="SET", key=storage_key, value=weather_res)
            yield {
                "step": 7,
                "type": "tool_execute",
                "name": "browser_storage",
                "output": store_res
            }
            time.sleep(1.2)
            
            yield {
                "step": 8,
                "type": "thought",
                "content": "Data is saved. Ready to output the confirmation."
            }
            time.sleep(1.0)
            
            yield {
                "step": 9,
                "type": "final_answer",
                "content": f"I queried the weather in {city} ('{weather_res}') and saved it to browser storage under key '{storage_key}'."
            }
        except Exception as e:
            yield {
                "step": 4,
                "type": "error",
                "content": f"Error running storage simulation: {str(e)}"
            }

    # Scenario C: Basic Math (uses calculator tool)
    elif any(op in prompt_lower for op in ["+", "-", "*", "/", "divided", "times", "minus", "plus", "squared", "eval"]):
        match = re.search(r'([0-9+\-*/().\s]{3,})', prompt)
        expr = match.group(1).strip() if match else "2 + 2"
        expr = expr.rstrip('.?!')
        
        yield {
            "step": 2,
            "type": "thought",
            "content": f"I detect a math query. I will call the 'calculator' tool with expression: '{expr}'."
        }
        time.sleep(1.2)
        
        yield {
            "step": 3,
            "type": "tool_call",
            "name": "calculator",
            "args": {"expression": expr}
        }
        time.sleep(1.0)
        
        try:
            res = tool_registry.tools["calculator"]["func"](expression=expr)
            yield {
                "step": 4,
                "type": "tool_execute",
                "name": "calculator",
                "output": str(res)
            }
            time.sleep(1.2)
            
            yield {
                "step": 5,
                "type": "thought",
                "content": f"Evaluation successful. The answer is {res}."
            }
            time.sleep(1.0)
            
            yield {
                "step": 6,
                "type": "final_answer",
                "content": f"Evaluating '{expr}' yields: {res}."
            }
        except Exception as e:
            yield {
                "step": 4,
                "type": "error",
                "content": f"Calculation failed: {str(e)}"
            }
            
    # Default Scenario
    else:
        yield {
            "step": 2,
            "type": "thought",
            "content": "No local tools or skills match this query. Providing a direct simulated response."
        }
        time.sleep(1.5)
        
        yield {
            "step": 3,
            "type": "final_answer",
            "content": f"This is a simulated agent response to: '{prompt}'. Enter a Gemini API Key to enable Live Mode and execute custom skills dynamically!"
        }

def run_agent_live(prompt: str, api_key: str) -> Generator[Dict[str, Any], None, None]:
    """
    Runs the agent loop live against the Gemini API.
    Combines both the Tool Registry and the Skill Registry, exposing all to the LLM.
    """
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    # Combine declarations from both registries
    function_declarations = []
    
    # 1. Add low-level tools
    for name, tool_info in tool_registry.tools.items():
        function_declarations.append({
            "name": name,
            "description": f"[Atomic Tool] {tool_info['schema']['description']}",
            "parameters": tool_info["schema"]["parameters"]
        })
        
    # 2. Add high-level composite skills
    for name, skill_info in skill_registry.skills.items():
        function_declarations.append({
            "name": name,
            "description": f"[Composite Skill Workflow] {skill_info['schema']['description']}",
            "parameters": skill_info["schema"]["parameters"]
        })
        
    tools_payload = [{"functionDeclarations": function_declarations}] if function_declarations else []
    
    yield {
        "step": 1,
        "type": "thought",
        "content": f"Initializing Live Gemini Agent. Loaded {len(tool_registry.tools)} tools and {len(skill_registry.skills)} composite skills."
    }
    
    history = [
        {"role": "user", "parts": [{"text": prompt}]}
    ]
    
    headers = {"Content-Type": "application/json"}
    max_steps = 6
    step_counter = 2
    
    for iteration in range(max_steps):
        payload = {
            "contents": history,
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            }
        }
        if tools_payload:
            payload["tools"] = tools_payload
            
        yield {
            "step": step_counter,
            "type": "api_request",
            "content": json.dumps(payload, indent=2)
        }
        step_counter += 1
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            if response.status_code != 200:
                raise Exception(f"Gemini API returned status {response.status_code}: {response.text}")
                
            resp_json = response.json()
            yield {
                "step": step_counter,
                "type": "api_response",
                "content": json.dumps(resp_json, indent=2)
            }
            step_counter += 1
            
            candidates = resp_json.get("candidates", [])
            if not candidates:
                raise Exception("Gemini API returned no candidates.")
                
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            history.append({
                "role": "model",
                "parts": parts
            })
            
            text_part = next((p.get("text") for p in parts if "text" in p), None)
            if text_part:
                has_tool_call = any("functionCall" in p for p in parts)
                yield {
                    "step": step_counter,
                    "type": "thought" if has_tool_call else "final_answer",
                    "content": text_part
                }
                step_counter += 1
                
                if not has_tool_call:
                    break
                    
            function_call_part = next((p.get("functionCall") for p in parts if "functionCall" in p), None)
            if function_call_part:
                func_name = function_call_part.get("name")
                func_args = function_call_part.get("args", {})
                
                yield {
                    "step": step_counter,
                    "type": "tool_call",
                    "name": func_name,
                    "args": func_args
                }
                step_counter += 1
                
                # Dynamic Routing: Search in Tool Registry first, then Skill Registry
                if func_name in tool_registry.tools:
                    try:
                        func = tool_registry.tools[func_name]["func"]
                        output = func(**func_args)
                        output_msg = str(output)
                    except Exception as e:
                        output_msg = f"Error executing tool '{func_name}': {str(e)}"
                elif func_name in skill_registry.skills:
                    try:
                        func = skill_registry.skills[func_name]["func"]
                        output = func(**func_args)
                        output_msg = str(output)
                    except Exception as e:
                        output_msg = f"Error executing skill '{func_name}': {str(e)}"
                else:
                    output_msg = f"Error: Tool/Skill '{func_name}' is not registered."
                        
                yield {
                    "step": step_counter,
                    "type": "tool_execute",
                    "name": func_name,
                    "output": output_msg
                }
                step_counter += 1
                
                history.append({
                    "role": "tool",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": func_name,
                                "response": {
                                    "output": output_msg
                                }
                            }
                        }
                    ]
                })
            else:
                if not text_part:
                    yield {
                        "step": step_counter,
                        "type": "final_answer",
                        "content": "Agent completed without returning text."
                    }
                break
                
        except Exception as e:
            yield {
                "step": step_counter,
                "type": "error",
                "content": f"Exception in agent loop: {str(e)}"
            }
            break
            
    else:
        yield {
            "step": step_counter,
            "type": "error",
            "content": "Agent stopped due to reaching maximum iteration cap (6 turns)."
        }
