import logging
from sqlalchemy.orm import Session
from app.models.automation import WorkflowRecord
from app.services.workflow_engine import workflow_engine

logger = logging.getLogger("autonomous_agent")

class AutonomousAgentService:
    async def execute_pending_workflows(self, db: Session) -> int:
        """Scan the database and execute one step of all pending workflows."""
        pending_records = db.query(WorkflowRecord).filter(
            WorkflowRecord.status == "pending"
        ).all()

        executed_count = 0
        for record in pending_records:
            try:
                logger.info(f"Agent executing workflow '{record.name}' step {record.current_step_idx}")
                await workflow_engine.run_workflow_step(db, record.id)
                executed_count += 1
            except Exception as e:
                logger.error(f"Failed to execute workflow step: {str(e)}")

        return executed_count

autonomous_agent = AutonomousAgentService()
