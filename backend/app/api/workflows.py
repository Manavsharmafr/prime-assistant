from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.models.automation import WorkflowRecord
from app.services.workflow_engine import workflow_engine
from app.services.autonomous_agent import autonomous_agent
from app.services.scheduler import scheduler as scheduler_service

router = APIRouter(prefix="/workflows", tags=["Workflows Engine"])

class WorkflowCreateRequest(BaseModel):
    name: str
    steps: List[str]
    schedule_cron: Optional[str] = None
    retry_policy: Optional[Dict[str, Any]] = None

@router.get("")
def list_workflows(db: Session = Depends(get_db)):
    """Fetch all persisted workflows and their current execution details."""
    records = db.query(WorkflowRecord).all()
    results = []
    for r in records:
        results.append({
            "id": r.id,
            "name": r.name,
            "status": r.status,
            "current_step": r.current_step_idx,
            "steps": r.steps,
            "schedule_cron": r.schedule_cron,
            "next_run_at": r.next_run_at,
            "created_at": r.created_at
        })
    return results

@router.post("/create")
def create_new_workflow(request: WorkflowCreateRequest, db: Session = Depends(get_db)):
    """Instantiate a new multi-step workflow in the database."""
    record = workflow_engine.create_workflow(
        db=db,
        name=request.name,
        steps=request.steps,
        schedule_cron=request.schedule_cron,
        retry_policy=request.retry_policy
    )
    return {"status": "success", "id": record.id}

@router.post("/{workflow_id}/pause")
def pause_active_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """Pause workflow step execution."""
    return workflow_engine.pause_workflow(db, workflow_id)

@router.post("/{workflow_id}/resume")
async def resume_paused_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """Resume execution of a paused or pending workflow."""
    return await workflow_engine.resume_workflow(db, workflow_id)

@router.post("/{workflow_id}/cancel")
def cancel_active_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """Cancel workflow progression."""
    return workflow_engine.cancel_workflow(db, workflow_id)

@router.post("/trigger-scheduler")
def force_scheduler_trigger(db: Session = Depends(get_db)):
    """Manually invoke scheduler loop scanner for evaluating cron jobs."""
    count = scheduler_service.evaluate_scheduled_jobs(db)
    return {"status": "success", "triggered_jobs": count}

@router.post("/trigger-agent")
async def force_agent_trigger(db: Session = Depends(get_db)):
    """Manually invoke autonomous agent loop scanner for executing pending tasks."""
    count = await autonomous_agent.execute_pending_workflows(db)
    return {"status": "success", "executed_steps": count}
