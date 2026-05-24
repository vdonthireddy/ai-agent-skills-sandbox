import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from skills import registry, skill
from agent import run_agent_simulated, run_agent_live

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Interactive Python AI Agent Sandbox")

# Enable CORS for development ease
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

class SkillUpload(BaseModel):
    code: str

@app.get("/api/skills")
async def get_skills():
    """Retrieve list of all registered skills, their schemas and source code."""
    skills_data = []
    for name, skill_info in registry.skills.items():
        skills_data.append({
            "name": name,
            "description": skill_info["schema"]["description"],
            "parameters": skill_info["schema"]["parameters"],
            "source": skill_info["source"],
            "doc": skill_info["doc"]
        })
    return skills_data

@app.post("/api/skills")
async def add_skill(payload: SkillUpload):
    """
    Dynamically compiles and registers a new Python skill.
    Executes the upload code, which must use the @skill decorator to register.
    """
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    
    # Validation check: must use the @skill decorator to register itself
    if "@skill" not in code:
        raise HTTPException(status_code=400, detail="The code must contain the '@skill' decorator to register with the registry.")
        
    try:
        # Create an enriched globals namespace for the compiled code.
        # Python functions defined in exec() use the globals dictionary for subsequent global scope lookups.
        # We copy all variables and functions from skills.py to ensure references to module states
        # (like _in_memory_db or other skills) resolve correctly.
        import math
        import re
        import json
        import requests
        import skills
        
        exec_globals = globals().copy()
        
        # Populate with all non-private attributes from skills.py module
        for name in dir(skills):
            if not name.startswith("__"):
                exec_globals[name] = getattr(skills, name)
                
        exec_globals.update({
            "skill": skill,
            "registry": registry,
            "math": math,
            "re": re,
            "json": json,
            "requests": requests
        })
        
        # Compile and execute the source code
        # In a local developer environment, this dynamic registration is safe and educational
        exec(code, exec_globals)
        
        # Log active skills to verify
        logger.info(f"Dynamically loaded code. Current registered skills: {list(registry.skills.keys())}")
        
        return {
            "success": True,
            "message": f"Successfully registered new skill! Current skills: {list(registry.skills.keys())}"
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
        # Choose runner
        if payload.mode == "live":
            logger.info(f"Running agent in LIVE mode for prompt: '{prompt}'")
            generator = run_agent_live(prompt, payload.api_key)
        else:
            logger.info(f"Running agent in SIMULATED mode for prompt: '{prompt}'")
            generator = run_agent_simulated(prompt)
            
        try:
            for step in generator:
                # SSE lines must start with "data: " and end with "\n\n"
                yield f"data: {json.dumps(step)}\n\n"
        except Exception as e:
            logger.error(f"Generator error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Internal Runner Error: {str(e)}'})}\n\n"
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

# Serve the static frontend assets.
# Ensure the static directory exists.
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount the static files handler at root
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
