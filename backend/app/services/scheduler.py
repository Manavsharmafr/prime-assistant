import datetime
from sqlalchemy.orm import Session
from app.models.automation import WorkflowRecord

class SchedulerService:
    def evaluate_scheduled_jobs(self, db: Session) -> int:
        """Scan scheduled workflows, trigger execution, and compute next run datetimes."""
        now = datetime.datetime.utcnow()
        scheduled_records = db.query(WorkflowRecord).filter(
            WorkflowRecord.schedule_cron.isnot(None)
        ).all()

        triggered_count = 0
        for record in scheduled_records:
            # If next_run_at is empty, initialize it to now
            if not record.next_run_at:
                record.next_run_at = now
                db.commit()

            if now >= record.next_run_at:
                # Trigger workflow execution reset
                record.status = "pending"
                record.current_step_idx = 0
                
                # Compute next run (mock next execution after +60 seconds for testing or +1 day)
                interval_seconds = 60
                if record.schedule_cron == "@daily":
                    interval_seconds = 86400
                elif record.schedule_cron == "@hourly":
                    interval_seconds = 3600

                record.next_run_at = now + datetime.timedelta(seconds=interval_seconds)
                db.commit()
                triggered_count += 1

        return triggered_count

scheduler = SchedulerService()
