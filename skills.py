import inspect
import re
from typing import Callable, Dict, Any, List

# Import tools directly so composite skills can coordinate them
from tools import get_weather, calculator, browser_storage, fetch_webpage

class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, Dict[str, Any]] = {}

    def register(self, func: Callable) -> Callable:
        """Decorator to register a function as an agent composite skill."""
        name = func.__name__
        doc = func.__doc__ or ""
        
        # 1. Parse description and parameter descriptions from docstring
        description, param_descriptions = self._parse_docstring(doc)
        
        # 2. Extract schema using inspect
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        type_mapping = {
            str: "STRING",
            int: "INTEGER",
            float: "NUMBER",
            bool: "BOOLEAN",
            list: "ARRAY",
            dict: "OBJECT"
        }
        
        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'cls'):
                continue
                
            annotation = param.annotation
            schema_type = "STRING" # Default fallback
            if annotation != inspect.Parameter.empty:
                schema_type = type_mapping.get(annotation, "STRING")
            
            param_desc = param_descriptions.get(param_name, f"The {param_name} parameter.")
            
            properties[param_name] = {
                "type": schema_type,
                "description": param_desc
            }
            
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        schema = {
            "name": name,
            "description": description or f"Execute skill {name}",
            "parameters": {
                "type": "OBJECT",
                "properties": properties
            }
        }
        if required:
            schema["parameters"]["required"] = required
            
        self.skills[name] = {
            "name": name,
            "func": func,
            "schema": schema,
            "source": inspect.getsource(func),
            "doc": doc
        }
        return func

    def _parse_docstring(self, docstring: str) -> tuple[str, dict[str, str]]:
        if not docstring:
            return "", {}
            
        lines = [line.strip() for line in docstring.split('\n')]
        
        description_lines = []
        args_start = -1
        for i, line in enumerate(lines):
            if line.lower().startswith(('args:', 'parameters:', 'params:')):
                args_start = i
                break
            description_lines.append(line)
            
        description = " ".join([l for l in description_lines if l]).strip()
        
        param_descriptions = {}
        if args_start != -1:
            current_param = None
            current_desc = []
            
            for line in lines[args_start + 1:]:
                if not line:
                    continue
                match = re.match(r'^([\w_]+)\s*(?:\([^)]+\))?\s*:\s*(.*)', line)
                if match:
                    if current_param:
                        param_descriptions[current_param] = " ".join(current_desc).strip()
                    current_param = match.group(1)
                    current_desc = [match.group(2)]
                elif current_param:
                    current_desc.append(line)
            
            if current_param:
                param_descriptions[current_param] = " ".join(current_desc).strip()
                
        return description, param_descriptions

# Initialize the global skill registry
skill_registry = SkillRegistry()

# Decorator shortcut
def skill(func: Callable) -> Callable:
    return skill_registry.register(func)

# --- High-Level Composite Skills (Workflows) ---

@skill
def research_city(city: str) -> str:
    """
    Performs a full travel research report on a city, gathering weather, converting temperature,
    generating outlines, and automatically saving a summary report in the database storage.
    
    Args:
        city: The name of the city to research (e.g. "Paris", "Tokyo", "Sydney").
    """
    # 1. Invoke get_weather tool
    weather_data = get_weather(city)
    
    # 2. Extract temperature and use calculator tool to convert it to Fahrenheit
    temp_match = re.search(r'(\d+)°C', weather_data)
    temp_c = float(temp_match.group(1)) if temp_match else 20.0
    temp_f = calculator(f"({temp_c} * 9/5) + 32")
    
    # 3. Simulate page fetch for description (Wikipedia outline)
    summary_url = f"https://en.wikipedia.org/wiki/{city.replace(' ', '_')}"
    wiki_data = fetch_webpage(summary_url)
    
    # Clean up wiki outline snippet
    snippet = "No extra details found."
    if "wikipedia" in wiki_data.lower() or "simulated" in wiki_data.lower():
        parts = wiki_data.split("\n\n")
        snippet = parts[-1] if len(parts) > 1 else wiki_data
        
    # 4. Compile detailed travel report
    report = (
        f"==================================================\n"
        f"TRAVEL RESEARCH REPORT: {city.upper()}\n"
        f"==================================================\n"
        f"1. Current Weather conditions:\n"
        f"   - {weather_data}\n"
        f"   - Temp in Fahrenheit: {temp_f:.1f}°F\n\n"
        f"2. Local Summary & Insights:\n"
        f"   - {snippet}\n\n"
        f"3. Recommendation:\n"
        f"   - Weather is {temp_c}°C ({temp_f:.1f}°F). "
        f"{'A great time for outdoor sightseeing!' if temp_c > 15 else 'Best suited for indoor museums and galleries.'}\n"
        f"=================================================="
    )
    
    # 5. Save report automatically to persistent storage
    storage_key = f"{city.lower()}_travel_report"
    browser_storage("SET", storage_key, report)
    
    return f"Successfully completed full city research workflow for {city}. Saved report in browser_storage as '{storage_key}'.\n\nPreview:\n{report}"
