"""
FastAPI web interface for the CTF solver
"""
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from src.models.challenge import Challenge, CTFSubmission, ChallengeType
from src.models.state import CTFState, WorkflowStatus
from src.graph.workflow import CTFSolverGraph
from src.utils.logging import get_logger, setup_logging
from src.utils.config import get_config

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Web CTF Solver", 
    description="LangGraph-powered multi-agent system for solving web CTF challenges",
    version="0.1.0"
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
templates = Jinja2Templates(directory="src/web/templates")

# Global state management
active_sessions: Dict[str, CTFState] = {}
solver_graph = CTFSolverGraph()

# Pydantic models for API
class ChallengeSubmission(BaseModel):
    url: str
    title: str = ""
    description: str = ""
    source_code: str = None
    flag_format: str = ""
    hint: str = None

class ExploitStatus(BaseModel):
    challenge_id: str
    status: str
    progress: float
    current_agent: Optional[str] = None
    messages: List[str] = []
    flags_found: List[str] = []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with challenge submission form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse) 
async def dashboard(request: Request):
    """Dashboard showing active challenges"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_sessions": len(active_sessions),
        "sessions": [
            {
                "id": session_id,
                "challenge": state.challenge.title or state.challenge.url,
                "status": state.workflow_status.value,
                "progress": _calculate_progress(state),
                "flags_found": len(state.flags_found)
            }
            for session_id, state in active_sessions.items()
        ]
    })

@app.post("/api/challenges/submit")
async def submit_challenge(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    title: str = Form(""),
    description: str = Form(""),
    source_code: str = Form(""),
    flag_format: str = Form(""),
    hint: str = Form("")
):
    """Submit a new CTF challenge for solving"""
    try:
        # Create challenge object
        challenge = Challenge(
            id=str(uuid.uuid4()),
            url=url,
            title=title,
            description=description,
            source_code=source_code,
            flag_format=flag_format,
            hint=hint,
            created_at=datetime.now()
        )
        
        # Create initial state
        state = CTFState(
            challenge=challenge,
            submission=CTFSubmission(challenge=challenge)
        )
        
        # Store in active sessions
        session_id = challenge.id
        active_sessions[session_id] = state
        
        # Start solving process in background
        background_tasks.add_task(solve_challenge_background, session_id, state)
        
        logger.info(f"Submitted new challenge: {challenge.title} ({session_id})")
        
        return {
            "success": True,
            "challenge_id": session_id,
            "message": "Challenge submitted successfully. Solving in progress...",
            "redirect_url": f"/challenges/{session_id}"
        }
        
    except Exception as e:
        logger.error(f"Challenge submission failed: {e}")
        raise HTTPException(status_code=500, detail=f"Challenge submission failed: {str(e)}")

@app.get("/api/challenges/{challenge_id}/status")
async def get_challenge_status(challenge_id: str):
    """Get the current status of a challenge"""
    if challenge_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    state = active_sessions[challenge_id]
    
    # Get current agent status
    current_agent = None
    current_agent_messages = []
    
    if state.current_agent:
        agent_state = state.agent_states.get(state.current_agent)
        if agent_state:
            current_agent = state.current_agent.value
            current_agent_messages = agent_state.messages[-5:]  # Last 5 messages
    
    return ExploitStatus(
        challenge_id=challenge_id,
        status=state.workflow_status.value,
        progress=_calculate_progress(state),
        current_agent=current_agent,
        messages=current_agent_messages,
        flags_found=state.flags_found
    )

@app.get("/api/challenges/{challenge_id}/details")
async def get_challenge_details(challenge_id: str):
    """Get detailed information about a challenge"""
    if challenge_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    state = active_sessions[challenge_id]
    
    return {
        "challenge": state.challenge.to_dict(),
        "status": state.workflow_status.value,
        "summary": state.get_summary(),
        "crawled_pages": len(state.crawled_pages),
        "vulnerabilities": [
            {
                "type": vuln.vulnerability_type,
                "location": vuln.location,
                "confidence": vuln.confidence,
                "description": vuln.description
            }
            for vuln in state.vulnerabilities
        ],
        "exploit_attempts": len(state.submission.exploit_attempts),
        "successful_exploits": len(state.successful_exploits),
        "flags_found": state.flags_found,
        "agent_states": {
            agent_type.value: {
                "status": agent_state.status,
                "progress": agent_state.progress,
                "messages": agent_state.messages[-3:],  # Last 3 messages
                "errors": agent_state.errors
            }
            for agent_type, agent_state in state.agent_states.items()
        }
    }

@app.get("/challenges/{challenge_id}", response_class=HTMLResponse)
async def challenge_detail(request: Request, challenge_id: str):
    """Challenge detail page"""
    if challenge_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    state = active_sessions[challenge_id]
    
    return templates.TemplateResponse("challenge_detail.html", {
        "request": request,
        "challenge_id": challenge_id,
        "challenge": state.challenge,
        "status": state.workflow_status.value
    })

@app.post("/api/challenges/{challenge_id}/stop")
async def stop_challenge(challenge_id: str):
    """Stop a running challenge"""
    if challenge_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    state = active_sessions[challenge_id]
    state.workflow_status = WorkflowStatus.FAILED
    
    return {"success": True, "message": "Challenge stopped"}

@app.delete("/api/challenges/{challenge_id}")
async def delete_challenge(challenge_id: str):
    """Delete a challenge from active sessions"""
    if challenge_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    del active_sessions[challenge_id]
    return {"success": True, "message": "Challenge deleted"}

@app.get("/api/challenges")
async def list_challenges():
    """List all active challenges"""
    return {
        "challenges": [
            {
                "id": session_id,
                "title": state.challenge.title,
                "url": state.challenge.url,
                "status": state.workflow_status.value,
                "progress": _calculate_progress(state),
                "flags_found": len(state.flags_found),
                "created_at": state.start_time.isoformat()
            }
            for session_id, state in active_sessions.items()
        ]
    }

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    total_challenges = len(active_sessions)
    completed_challenges = sum(1 for state in active_sessions.values() 
                              if state.workflow_status == WorkflowStatus.COMPLETED)
    flags_found = sum(len(state.flags_found) for state in active_sessions.values())
    
    return {
        "total_challenges": total_challenges,
        "completed_challenges": completed_challenges, 
        "success_rate": completed_challenges / total_challenges if total_challenges > 0 else 0,
        "total_flags_found": flags_found,
        "active_sessions": total_challenges
    }

async def solve_challenge_background(session_id: str, state: CTFState):
    """Background task to solve a challenge using LangGraph"""
    try:
        logger.info(f"Starting background solving for challenge {session_id}")
        
        # Execute the LangGraph workflow
        final_state = await solver_graph.solve_ctf(state, thread_id=session_id)
        
        # Update the session
        active_sessions[session_id] = final_state
        
        if final_state.flags_found:
            logger.info(f"Successfully solved challenge {session_id}: {final_state.flags_found}")
        else:
            logger.info(f"Challenge {session_id} completed without finding flags")
            
    except Exception as e:
        logger.error(f"Background solving failed for challenge {session_id}: {e}")
        if session_id in active_sessions:
            active_sessions[session_id].workflow_status = WorkflowStatus.FAILED

def _calculate_progress(state: CTFState) -> float:
    """Calculate overall progress for a challenge"""
    total_agents = 4  # crawler, summarizer, threat_model, fuzzer
    completed_agents = len(state.completed_agents)
    
    # Base progress from completed agents
    base_progress = completed_agents / total_agents
    
    # Add current agent progress if active
    if state.current_agent and state.current_agent not in state.completed_agents:
        current_agent_progress = state.agent_states[state.current_agent].progress
        base_progress += current_agent_progress / total_agents
    
    # Cap at 100%
    return min(base_progress, 1.0)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def run_server():
    """Run the web server"""
    config = get_config()
    
    uvicorn.run(
        "src.web.app:app",
        host=config.get("HOST", "0.0.0.0"),
        port=config.get("PORT", 8000),
        reload=config.get("DEBUG", True),
        log_level="info"
    )

if __name__ == "__main__":
    run_server()