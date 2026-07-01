import json
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.automation import WorkflowRecord, TaskRecord
from app.services.task_manager import task_manager
from app.services.permission import permission_service

class WorkflowEngineService:
    def create_workflow(
        self,
        db: Session,
        name: str,
        steps: List[str],
        schedule_cron: Optional[str] = None,
        retry_policy: Optional[Dict[str, Any]] = None
    ) -> WorkflowRecord:
        """Create and persist a new workflow in the database."""
        default_policy = retry_policy or {"max_retries": 3, "current_retries": 0}
        record = WorkflowRecord(
            name=name,
            status="pending",
            steps=json.dumps(steps),
            current_step_idx=0,
            retry_policy=json.dumps(default_policy),
            schedule_cron=schedule_cron
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    async def run_workflow_step(self, db: Session, workflow_id: str) -> Dict[str, Any]:
        """Execute the current step of the workflow."""
        record = db.query(WorkflowRecord).filter(WorkflowRecord.id == workflow_id).first()
        if not record:
            return {"status": "error", "message": "Workflow not found"}

        if record.status in ["completed", "failed", "paused", "cancelled"]:
            return {"status": record.status, "message": f"Workflow is in '{record.status}' state."}

        steps = json.loads(record.steps)
        if record.current_step_idx >= len(steps):
            record.status = "completed"
            db.commit()
            return {"status": "completed", "message": "Workflow already finished"}

        record.status = "running"
        db.commit()

        current_cmd = steps[record.current_step_idx]

        # 1. Pre-check permission
        risk, justification = permission_service.check_permission(current_cmd)
        if risk == "blocked":
            record.status = "failed"
            db.commit()
            return {"status": "failed", "message": f"Step blocked by safety gate: {justification}"}
        
        if risk == "confirmation_required":
            record.status = "paused"
            db.commit()
            # Request approval via task_manager
            await task_manager.run_task(db, current_cmd)
            return {
                "status": "paused",
                "message": "Step requires explicit confirmation. Workflow paused.",
                "approval_required": True
            }

        # 2. Execute command
        try:
            result = await task_manager.run_task(db, current_cmd)
            if result.get("status") == "failed":
                return self._handle_step_failure(db, record, "Command exited with error code")
            
            # Step succeeded
            record.current_step_idx += 1
            policy = json.loads(record.retry_policy)
            policy["current_retries"] = 0  # Reset retries on success
            record.retry_policy = json.dumps(policy)

            if record.current_step_idx >= len(steps):
                record.status = "completed"
            else:
                record.status = "pending"  # Ready for next step
                
            db.commit()
            return {
                "status": record.status,
                "current_step": record.current_step_idx,
                "total_steps": len(steps)
            }
        except Exception as e:
            return self._handle_step_failure(db, record, str(e))

    def _handle_step_failure(self, db: Session, record: WorkflowRecord, error_msg: str) -> Dict[str, Any]:
        """Apply retry policies or mark workflow failed."""
        policy = json.loads(record.retry_policy)
        max_retries = policy.get("max_retries", 3)
        current_retries = policy.get("current_retries", 0)

        if current_retries < max_retries:
            current_retries += 1
            policy["current_retries"] = current_retries
            record.retry_policy = json.dumps(policy)
            record.status = "pending"  # retry in next loop
            db.commit()
            return {
                "status": "retrying",
                "attempt": current_retries,
                "max": max_retries,
                "error": error_msg
            }
        else:
            record.status = "failed"
            db.commit()
            return {
                "status": "failed",
                "error": f"Max retries exceeded: {error_msg}"
            }

    def pause_workflow(self, db: Session, workflow_id: str) -> Dict[str, Any]:
        record = db.query(WorkflowRecord).filter(WorkflowRecord.id == workflow_id).first()
        if record:
            record.status = "paused"
            db.commit()
            return {"status": "paused"}
        return {"status": "error", "message": "Workflow not found"}

    async def resume_workflow(self, db: Session, workflow_id: str) -> Dict[str, Any]:
        record = db.query(WorkflowRecord).filter(WorkflowRecord.id == workflow_id).first()
        if record:
            record.status = "pending"
            db.commit()
            # Try running the step
            return await self.run_workflow_step(db, workflow_id)
        return {"status": "error", "message": "Workflow not found"}

    def cancel_workflow(self, db: Session, workflow_id: str) -> Dict[str, Any]:
        record = db.query(WorkflowRecord).filter(WorkflowRecord.id == workflow_id).first()
        if record:
            record.status = "cancelled"
            db.commit()
            return {"status": "cancelled"}
        return {"status": "error", "message": "Workflow not found"}

workflow_engine = WorkflowEngineService()
