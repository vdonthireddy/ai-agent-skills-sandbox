import inspect
import re
import math
from typing import Callable, Dict, Any, List

class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, Dict[str, Any]] = {}

    def register(self, func: Callable) -> Callable:
        """Decorator to register a function as an agent skill."""
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
            # Skip self/cls if any (though these should be module-level functions)
            if param_name in ('self', 'cls'):
                continue
                
            # Get parameter type
            annotation = param.annotation
            schema_type = "STRING" # Default fallback
            if annotation != inspect.Parameter.empty:
                schema_type = type_mapping.get(annotation, "STRING")
            
            param_desc = param_descriptions.get(param_name, f"The {param_name} parameter.")
            
            properties[param_name] = {
                "type": schema_type,
                "description": param_desc
            }
            
            # If no default value, it's required
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        # 3. Create the Gemini-compliant Tool definition
        schema = {
            "name": name,
            "description": description or f"Execute {name}",
            "parameters": {
                "type": "OBJECT",
                "properties": properties
            }
        }
        if required:
            schema["parameters"]["required"] = required
            
        # Store in registry
        self.skills[name] = {
            "name": name,
            "func": func,
            "schema": schema,
            "source": inspect.getsource(func),
            "doc": doc
        }
        return func

    def _parse_docstring(self, docstring: str) -> tuple[str, dict[str, str]]:
        """Parses description and parameters from a Google or standard docstring."""
        if not docstring:
            return "", {}
            
        lines = [line.strip() for line in docstring.split('\n')]
        
        # Extract main description (everything before Args: or Parameters:)
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
            
            # Simple parser for:
            # param_name (type): description
            # or param_name: description
            for line in lines[args_start + 1:]:
                if not line:
                    continue
                # Check if it looks like a new parameter start
                match = re.match(r'^([\w_]+)\s*(?:\([^)]+\))?\s*:\s*(.*)', line)
                if match:
                    if current_param:
                        param_descriptions[current_param] = " ".join(current_desc).strip()
                    current_param = match.group(1)
                    current_desc = [match.group(2)]
                elif current_param:
                    # Append to current parameter description
                    current_desc.append(line)
            
            if current_param:
                param_descriptions[current_param] = " ".join(current_desc).strip()
                
        return description, param_descriptions

# Initialize the global skill registry
registry = SkillRegistry()

# Decorator shortcut
def skill(func: Callable) -> Callable:
    return registry.register(func)

# --- Default Skills ---

@skill
def calculator(expression: str) -> float:
    """
    Evaluates a mathematical expression safely. Supports basic arithmetic.
    
    Args:
        expression: The mathematical expression to evaluate (e.g. "2 * 3 + 5" or "10 / (2 + 3)").
    """
    # Safe evaluation environment
    allowed_names = {
        'abs': abs,
        'round': round,
        'math': math,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'sqrt': math.sqrt,
        'pow': pow,
        'pi': math.pi,
        'e': math.e
    }
    
    # Simple sanitization
    sanitized = expression.replace('^', '**')
    if not re.match(r'^[0-9+\-*/().\s,e]|sin|cos|tan|sqrt|pow|pi|abs|round|math$', sanitized, re.IGNORECASE):
        raise ValueError("Invalid characters in expression. Only basic math operations allowed.")
        
    try:
        # Use eval in restricted environment
        result = eval(sanitized, {"__builtins__": None}, allowed_names)
        return float(result)
    except Exception as e:
        raise ValueError(f"Math evaluation error: {str(e)}")

@skill
def get_weather(city: str) -> str:
    """
    Fetches the current weather report for a given city.
    
    Args:
        city: The name of the city (e.g. "Tokyo", "London", "San Francisco").
    """
    city_lower = city.lower().strip()
    
    # Hardcoded database for demo purposes
    weather_db = {
        "tokyo": {"temp": 18, "condition": "Rainy", "humidity": "85%"},
        "london": {"temp": 12, "condition": "Cloudy", "humidity": "78%"},
        "san francisco": {"temp": 15, "condition": "Foggy", "humidity": "90%"},
        "new york": {"temp": 22, "condition": "Sunny", "humidity": "50%"},
        "paris": {"temp": 16, "condition": "Windy", "humidity": "65%"},
        "sydney": {"temp": 25, "condition": "Clear", "humidity": "45%"}
    }
    
    for k, v in weather_db.items():
        if k in city_lower:
            return f"Weather in {city}: {v['temp']}°C, {v['condition']}, Humidity: {v['humidity']}."
            
    # Default fallback using simple deterministic random based on city name length
    hash_val = sum(ord(c) for c in city)
    temp = 10 + (hash_val % 25) # temp between 10 and 35
    conditions = ["Sunny", "Partly Cloudy", "Rainy", "Clear", "Showers", "Overcast"]
    cond = conditions[hash_val % len(conditions)]
    humidity = f"{50 + (hash_val % 45)}%"
    
    return f"Weather in {city}: {temp}°C, {cond}, Humidity: {humidity} (Simulated Data)."

# Simulating simple backend store
_in_memory_db = {}

@skill
def browser_storage(action: str, key: str, value: str = None) -> str:
    """
    Reads, writes, or deletes items in the agent's key-value database. Useful for persistent state.
    
    Args:
        action: The database action to perform: "GET", "SET", or "DELETE".
        key: The storage key to look up or write to.
        value: The string value to write (required only for "SET").
    """
    global _in_memory_db
    act = action.upper().strip()
    
    if act == "GET":
        if key in _in_memory_db:
            return f"Key '{key}' found with value: '{_in_memory_db[key]}'"
        return f"Key '{key}' not found in database."
        
    elif act == "SET":
        if value is None:
            return "Error: Action SET requires a value."
        _in_memory_db[key] = value
        return f"Successfully saved key '{key}' = '{value}'"
        
    elif act == "DELETE":
        if key in _in_memory_db:
            del _in_memory_db[key]
            return f"Successfully deleted key '{key}'"
        return f"Key '{key}' not found, nothing to delete."
        
    else:
        return f"Error: Unknown storage action '{action}'. Use GET, SET, or DELETE."

@skill
def fetch_webpage(url: str) -> str:
    """
    Fetches the content of a webpage and returns a clean, text-only summary.
    
    Args:
        url: The web URL to fetch (e.g. "https://example.com" or "https://en.wikipedia.org/wiki/Artificial_intelligence").
    """
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urllib.parse.urlparse(url)
        
    domain = parsed.netloc.lower()
    
    # We will simulate page fetches for common sites to be fast, stable, and offline-friendly,
    # but we can also use real requests as a fallback if the user wants.
    mock_pages = {
        "example.com": "Example Domain. This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.",
        "wikipedia.org": "Artificial Intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans. AI applications include advanced web search engines, recommendation systems, understanding human speech, self-driving cars, generative tools, and competing at the highest level in strategic game systems.",
        "github.com": "GitHub, Inc. is a developer platform that allows developers to create, store, manage and share their code. It uses Git, providing the distributed version control and source code management functionality of Git, plus its own features."
    }
    
    for key, text in mock_pages.items():
        if key in domain:
            return f"Content of {url} (Simulated):\n\n{text}"
            
    # Try actual fetch (non-blocking fallback)
    try:
        import requests
        # Setup small timeout
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0 (AI Agent Sandbox)"})
        if resp.status_code == 200:
            # Strip HTML tags using simple regex to avoid requiring BeautifulSoup
            html = resp.text
            # Simple body extractor
            body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
            text_content = body_match.group(1) if body_match else html
            # Remove scripts & styles
            text_content = re.sub(r'<script[^>]*>.*?</script>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
            text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
            # Remove all other HTML tags
            text_content = re.sub(r'<[^>]+>', ' ', text_content)
            # Normalize whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            # Truncate
            return f"Content of {url} (Live Fetch - Truncated):\n\n{text_content[:600]}..."
        else:
            return f"Failed to fetch {url}. Status code: {resp.status_code}. Falling back to mock summary: Webpage contents for {domain} contains development docs and general landing page text."
    except Exception as e:
        return f"Could not fetch {url} due to error: {str(e)}. Fallback: This is a placeholder summary for {domain} showing basic site info."
