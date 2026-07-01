from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict
import uuid
import re
from app.core.database import get_db
from app.services.research_service import research_service
from app.services.task_manager import task_manager
from app.services.task_orchestrator import task_orchestrator

router = APIRouter(prefix="/agents", tags=["Agents Core"])


class CommandRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None
    provider: Optional[str] = None


class ChallengeResponse(BaseModel):
    status: str
    challenge_id: Optional[str] = None
    command: Optional[str] = None
    description: Optional[str] = None
    result: Optional[str] = None
    speech_response: Optional[str] = None
    report: Optional[Dict] = None
    request_id: Optional[str] = None
    task_id: Optional[str] = None
    message: Optional[str] = None
    affected_files: Optional[str] = None
    estimated_impact: Optional[str] = None


@router.post("/command", response_model=ChallengeResponse)
async def process_agent_command(request: CommandRequest, db: Session = Depends(get_db)):
    """Process user prompt using the planning and task orchestrator system."""
    convo_id = request.conversation_id or "default_conversation_id"
    
    result = await task_orchestrator.execute_user_prompt(
        db=db,
        prompt=request.prompt,
        conversation_id=convo_id,
        provider_override=request.provider
    )
    
    # Map dictionary response fields to ChallengeResponse schema
    return ChallengeResponse(
        status=result.get("status", "success"),
        challenge_id=result.get("challenge_id"),
        command=result.get("command"),
        description=result.get("description"),
        result=result.get("result"),
        speech_response=result.get("speech_response"),
        report=result.get("report"),
        request_id=result.get("request_id"),
        task_id=result.get("task_id"),
        message=result.get("message"),
        affected_files=result.get("affected_files"),
        estimated_impact=result.get("estimated_impact")
    )


@router.post("/challenges/{challenge_id}/approve")
async def approve_challenge(challenge_id: str, db: Session = Depends(get_db)):
    """Authorize a queued command through the shared automation pipeline."""
    result = await task_manager.process_approval_action(db, challenge_id, "approve")
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Approval request not found")
    if result["status"] == "already_processed":
        raise HTTPException(status_code=400, detail="Request has already been processed")
    return result


@router.post("/challenges/{challenge_id}/deny")
async def deny_challenge(challenge_id: str, db: Session = Depends(get_db)):
    """Reject a queued command through the shared automation pipeline."""
    result = await task_manager.process_approval_action(db, challenge_id, "reject")
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Approval request not found")
    if result["status"] == "already_processed":
        raise HTTPException(status_code=400, detail="Request has already been processed")
    return {"status": "aborted", "message": "Command aborted by user.", "approval": result}
