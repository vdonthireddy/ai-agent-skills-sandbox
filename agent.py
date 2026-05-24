import json
import time
import requests
import re
from typing import Generator, Dict, Any, List
from skills import registry

SYSTEM_PROMPT = """You are a helpful AI Agent equipped with local Python skills (tools). 
You must solve the user's request step-by-step.
Before calling any tool, explain your reasoning in a clear "Thought:" block.
Always use the tools available to gather information or perform calculations. Do not guess values that can be queried.
Format your thought and tool calls clearly.
"""

def extract_city(text: str) -> str:
    """Helper to extract a city name from text."""
    cities = ["tokyo", "london", "san francisco", "new york", "paris", "sydney"]
    text_lower = text.lower()
    for city in cities:
        if city in text_lower:
            return city.title()
    # Simple regex fallback
    match = re.search(r'in\s+([a-zA-Z\s]+?)(?:\s+and|\s+is|\s+to|\s*\.|\s*$)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return "Tokyo"

def run_agent_simulated(prompt: str) -> Generator[Dict[str, Any], None, None]:
    """
    Simulates the agent loop dynamically using heuristics.
    Executes actual Python skills under the hood to show real outcomes.
    """
    yield {
        "step": 1,
        "type": "thought",
        "content": f"Initializing simulated agent. User prompt: '{prompt}'. Scanning available skills..."
    }
    time.sleep(1.0)
    
    prompt_lower = prompt.lower()
    
    # Scenario A: Weather + Calculation
    if "weather" in prompt_lower and ("square" in prompt_lower or "calculate" in prompt_lower or "math" in prompt_lower or "multiply" in prompt_lower or "*" in prompt_lower):
        city = extract_city(prompt)
        yield {
            "step": 2,
            "type": "thought",
            "content": f"The user wants the weather in {city} and a calculation on the temperature. I will first query the weather using the 'get_weather' tool."
        }
        time.sleep(1.2)
        
        yield {
            "step": 3,
            "type": "tool_call",
            "name": "get_weather",
            "args": {"city": city}
        }
        time.sleep(1.0)
        
        # Execute tool
        try:
            weather_res = registry.skills["get_weather"]["func"](city=city)
            # Extract temperature number from: "Weather in Tokyo: 18°C, Rainy..."
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
            
            calc_res = registry.skills["calculator"]["func"](expression=expression)
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
                "content": f"I have successfully queried the weather ({weather_res}) and calculated the squared temperature ({calc_res}). I will now formulate the final response."
            }
            time.sleep(1.0)
            
            yield {
                "step": 9,
                "type": "final_answer",
                "content": f"The weather in {city} is currently {temp}°C. Squaring this temperature value gives {calc_res}. (Executed live Python skills in Simulated Mode)"
            }
            
        except Exception as e:
            yield {
                "step": 4,
                "type": "error",
                "content": f"Error running simulator pipeline: {str(e)}"
            }
            
    # Scenario B: Weather + Database Storage
    elif "weather" in prompt_lower and ("store" in prompt_lower or "save" in prompt_lower or "storage" in prompt_lower or "db" in prompt_lower):
        city = extract_city(prompt)
        yield {
            "step": 2,
            "type": "thought",
            "content": f"The request requires fetching the weather in {city} and saving it. Let's first retrieve the weather."
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
            weather_res = registry.skills["get_weather"]["func"](city=city)
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
                "content": f"Weather reports: '{weather_res}'. I need to save this to the storage tool under the key '{storage_key}'."
            }
            time.sleep(1.2)
            
            yield {
                "step": 6,
                "type": "tool_call",
                "name": "browser_storage",
                "args": {"action": "SET", "key": storage_key, "value": weather_res}
            }
            time.sleep(1.0)
            
            store_res = registry.skills["browser_storage"]["func"](action="SET", key=storage_key, value=weather_res)
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
                "content": f"I queried the weather in {city} ('{weather_res}') and saved it to browser storage under key '{storage_key}'. You can read it back using browser_storage GET."
            }
        except Exception as e:
            yield {
                "step": 4,
                "type": "error",
                "content": f"Error running storage simulation: {str(e)}"
            }

    # Scenario C: Basic Math
    elif any(op in prompt_lower for op in ["+", "-", "*", "/", "divided", "times", "minus", "plus", "squared", "eval"]):
        # Find math-like expression
        match = re.search(r'([0-9+\-*/().\s]{3,})', prompt)
        expr = match.group(1).strip() if match else "2 + 2"
        # strip punctuation at end
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
            res = registry.skills["calculator"]["func"](expression=expr)
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
                "content": f"Evaluating '{expr}' yields: {res}. (Simulated execution)"
            }
        except Exception as e:
            yield {
                "step": 4,
                "type": "error",
                "content": f"Calculation failed: {str(e)}"
            }
            
    # Default Scenario: Custom prompt / Direct answer
    else:
        yield {
            "step": 2,
            "type": "thought",
            "content": "No local tools match this query. I will provide a direct simulated response."
        }
        time.sleep(1.5)
        
        yield {
            "step": 3,
            "type": "final_answer",
            "content": f"This is a simulated agent response to: '{prompt}'. To run arbitrary prompts, write custom python skills, or do multi-step tool reasoning, enter your Gemini API Key in the settings panel to enable Live Mode!"
        }

def run_agent_live(prompt: str, api_key: str) -> Generator[Dict[str, Any], None, None]:
    """
    Runs the agent loop live against the Gemini API using function calling.
    Streams execution details step-by-step.
    """
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    # 1. Convert registered Python skills to Gemini API schema format
    function_declarations = []
    for skill_name, skill_info in registry.skills.items():
        # Gemini expects properties and types in a specific JSON schema format.
        # We need to map standard JSON Schema to Gemini's schema requirements.
        decl = {
            "name": skill_info["schema"]["name"],
            "description": skill_info["schema"]["description"],
            "parameters": skill_info["schema"]["parameters"]
        }
        function_declarations.append(decl)
        
    tools_payload = [{"functionDeclarations": function_declarations}] if function_declarations else []
    
    yield {
        "step": 1,
        "type": "thought",
        "content": f"Initializing Live Gemini Agent. Tools registered: {', '.join(registry.skills.keys())}."
    }
    
    # Initialize history
    history = [
        {"role": "user", "parts": [{"text": prompt}]}
    ]
    
    headers = {"Content-Type": "application/json"}
    max_steps = 6
    step_counter = 2
    
    for iteration in range(max_steps):
        # Build prompt payload
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
            
            # Save response to history
            history.append({
                "role": "model",
                "parts": parts
            })
            
            # Check for text (thoughts or answers)
            text_part = next((p.get("text") for p in parts if "text" in p), None)
            if text_part:
                # If there's a tool call, we treat text as "thought", else it's the final answer
                has_tool_call = any("functionCall" in p for p in parts)
                yield {
                    "step": step_counter,
                    "type": "thought" if has_tool_call else "final_answer",
                    "content": text_part
                }
                step_counter += 1
                
                if not has_tool_call:
                    # No tool call, we are done!
                    break
                    
            # Check for function calls
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
                
                # Execute the skill
                if func_name not in registry.skills:
                    output_msg = f"Error: Tool '{func_name}' is not registered."
                else:
                    try:
                        func = registry.skills[func_name]["func"]
                        output = func(**func_args)
                        output_msg = str(output)
                    except Exception as e:
                        output_msg = f"Error executing tool '{func_name}': {str(e)}"
                        
                yield {
                    "step": step_counter,
                    "type": "tool_execute",
                    "name": func_name,
                    "output": output_msg
                }
                step_counter += 1
                
                # Append function response to history
                # Standard format for Gemini tool response role is "tool"
                # Response must be a JSON object inside functionResponse.response
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
                # If there's neither text nor function call (unlikely), stop
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
