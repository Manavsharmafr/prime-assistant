from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.automation import ApprovalRequest, TaskRecord, AuditLog
from app.services.task_manager import task_manager

router = APIRouter(prefix="/automation", tags=["automation"])


# --- Request/Response schemas ---
class CommandExecutionRequest(BaseModel):
    command: str
    user_request: Optional[str] = "CLI Input"
    affected_files: Optional[str] = None
    estimated_impact: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    action: str  # 'approve', 'reject'


# --- Endpoints ---

@router.post("/tasks")
async def run_command_task(req: CommandExecutionRequest, db: Session = Depends(get_db)):
    """Execute command or append to safety approval queue."""
    result = await task_manager.run_task(
        db, 
        req.command, 
        req.user_request, 
        affected_files=req.affected_files, 
        estimated_impact=req.estimated_impact
    )
    return result


@router.post("/tasks/{id}/cancel")
def cancel_running_task(id: str, db: Session = Depends(get_db)):
    """Cancel active running task process."""
    success = task_manager.cancel_task(db, id)
    if not success:
        raise HTTPException(status_code=400, detail="Task not active or could not be cancelled")
    return {"status": "cancelled", "task_id": id}


@router.get("/tasks")
def list_tasks(status: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    """List historical and active tasks."""
    query = db.query(TaskRecord)
    if status:
        query = query.filter(TaskRecord.status == status)
    records = query.order_by(TaskRecord.start_time.desc()).limit(limit).all()
    return records


@router.get("/tasks/{id}")
def get_task_details(id: str, db: Session = Depends(get_db)):
    """Fetch task details and execution logs."""
    record = db.query(TaskRecord).filter(TaskRecord.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Task record not found")
    return record


@router.get("/approvals")
def list_approval_queue(status: Optional[str] = "pending", db: Session = Depends(get_db)):
    """List approval queue entries."""
    query = db.query(ApprovalRequest)
    if status:
        query = query.filter(ApprovalRequest.status == status)
    return query.order_by(ApprovalRequest.created_at.desc()).all()


@router.post("/approvals/{id}/action")
async def action_approval_request(id: str, req: ApprovalActionRequest, db: Session = Depends(get_db)):
    """Approve or reject a pending security command request."""
    result = await task_manager.process_approval_action(db, id, req.action)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Approval request not found")
    if result["status"] == "already_processed":
        raise HTTPException(status_code=400, detail="Request has already been processed")
    if result["status"] == "invalid_action":
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'approve' or 'reject'")
    return result


@router.get("/audit")
def list_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve execution safety audit logs."""
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
