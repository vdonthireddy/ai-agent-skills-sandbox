import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tools import tool_registry, tool
from skills import skill_registry, skill
from agent import run_agent_simulated, run_agent_live

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Interactive Python AI Agent Sandbox")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    prompt: str
    mode: str = "simulated"  # "simulated" or "live"
    api_key: Optional[str] = None

class CodeUpload(BaseModel):
    code: str

@app.get("/api/tools")
async def get_tools():
    """Retrieve list of all registered low-level tools, their schemas and source code."""
    tools_data = []
    for name, tool_info in tool_registry.tools.items():
        tools_data.append({
            "name": name,
            "description": tool_info["schema"]["description"],
            "parameters": tool_info["schema"]["parameters"],
            "source": tool_info["source"],
            "doc": tool_info["doc"]
        })
    return tools_data

@app.get("/api/skills")
async def get_skills():
    """Retrieve list of all registered high-level skills, their schemas and source code."""
    skills_data = []
    for name, skill_info in skill_registry.skills.items():
        skills_data.append({
            "name": name,
            "description": skill_info["schema"]["description"],
            "parameters": skill_info["schema"]["parameters"],
            "source": skill_info["source"],
            "doc": skill_info["doc"]
        })
    return skills_data

@app.post("/api/tools")
async def add_tool(payload: CodeUpload):
    """
    Dynamically compiles and registers a new low-level Python tool.
    The code must use the @tool decorator.
    """
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    if "@tool" not in code:
        raise HTTPException(status_code=400, detail="The code must contain the '@tool' decorator to register with the registry.")
        
    try:
        import math
        import re
        import json
        import requests
        import tools
        
        exec_globals = globals().copy()
        for name in dir(tools):
            if not name.startswith("__"):
                exec_globals[name] = getattr(tools, name)
                
        exec_globals.update({
            "tool": tool,
            "tool_registry": tool_registry,
            "math": math,
            "re": re,
            "json": json,
            "requests": requests
        })
        
        exec(code, exec_globals)
        logger.info(f"Dynamically loaded tool. Current tools: {list(tool_registry.tools.keys())}")
        
        return {
            "success": True,
            "message": f"Successfully registered tool! Current tools: {list(tool_registry.tools.keys())}"
        }
    except Exception as e:
        logger.error(f"Error compiling custom tool: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Compilation Error: {str(e)}")

@app.post("/api/skills")
async def add_skill(payload: CodeUpload):
    """
    Dynamically compiles and registers a new high-level Python skill.
    The code must use the @skill decorator.
    """
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    if "@skill" not in code:
        raise HTTPException(status_code=400, detail="The code must contain the '@skill' decorator to register with the registry.")
        
    try:
        import math
        import re
        import json
        import requests
        import tools
        import skills
        
        exec_globals = globals().copy()
        
        # Populate with low-level tools so the skill workflow code can call them
        for name in dir(tools):
            if not name.startswith("__"):
                exec_globals[name] = getattr(tools, name)
                
        # Populate with existing skills
        for name in dir(skills):
            if not name.startswith("__"):
                exec_globals[name] = getattr(skills, name)
                
        exec_globals.update({
            "skill": skill,
            "skill_registry": skill_registry,
            "tool_registry": tool_registry,
            "math": math,
            "re": re,
            "json": json,
            "requests": requests
        })
        
        exec(code, exec_globals)
        logger.info(f"Dynamically loaded skill. Current skills: {list(skill_registry.skills.keys())}")
        
        return {
            "success": True,
            "message": f"Successfully registered skill! Current skills: {list(skill_registry.skills.keys())}"
        }
    except Exception as e:
        logger.error(f"Error compiling custom skill: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Compilation Error: {str(e)}")

@app.post("/api/agent/run")
async def run_agent(payload: RunRequest):
    """
    Runs the agent loop step-by-step and streams logs as Server-Sent Events (SSE).
    """
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
        
    if payload.mode == "live" and not payload.api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required for Live Mode.")
        
    def sse_generator():
        if payload.mode == "live":
            logger.info(f"Running agent in LIVE mode for prompt: '{prompt}'")
            generator = run_agent_live(prompt, payload.api_key)
        else:
            logger.info(f"Running agent in SIMULATED mode for prompt: '{prompt}'")
            generator = run_agent_simulated(prompt)
            
        try:
            for step in generator:
                yield f"data: {json.dumps(step)}\n\n"
        except Exception as e:
            logger.error(f"Generator error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Internal Runner Error: {str(e)}'})}\n\n"
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

# Serve the static frontend assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
