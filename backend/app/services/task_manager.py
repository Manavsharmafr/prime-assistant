import asyncio
from datetime import datetime
import time
from typing import Dict, Any, List, Set, Optional
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.models.automation import ApprovalRequest, TaskRecord, AuditLog
from app.services.permission import permission_service
from app.services.command_executor import command_executor


# --- WebSocket Manager for Tasks & Logs ---
class TaskWebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self.disconnect(conn)


tasks_ws_manager = TaskWebSocketManager()


# --- Task Manager Service ---
class TaskManagerService:
    def __init__(self):
        # Maps active task_id -> {"process": Process, "start_time": float, "command": str}
        self._active_tasks: Dict[str, Dict[str, Any]] = {}

    def _broadcast_safe(self, message: Dict[str, Any]):
        """Safely broadcast WebSocket task message, ignoring loop issues if not running."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(tasks_ws_manager.broadcast(message))
        except RuntimeError:
            pass

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Return a list of currently running tasks."""
        active = []
        for tid, info in self._active_tasks.items():
            active.append({
                "task_id": tid,
                "command": info["command"],
                "start_time": info["start_time"]
            })
        return active

    async def run_task(self, db: Session, command: str, user_request: str = "CLI Input", affected_files: Optional[str] = None, estimated_impact: Optional[str] = None) -> Dict[str, Any]:
        """Verify safety permissions and execute the command or add to approval queue."""
        analysis = permission_service.analyze_command(command)
        risk = analysis["risk_level"]
        justification = analysis["justification"]
        
        final_affected_files = affected_files or analysis["affected_files"]
        final_estimated_impact = estimated_impact or analysis["estimated_impact"]

        if risk == "blocked":
            # Instantly log blocked command to audit
            audit = AuditLog(
                user_request=user_request,
                generated_command=command,
                approval_result="blocked_automatically",
                error_message=justification,
                timestamp=datetime.utcnow()
            )
            db.add(audit)
            db.commit()
            return {"status": "blocked", "message": justification, "task_id": None}

        if risk == "confirmation_required":
            # Put task in ApprovalRequest queue
            req = ApprovalRequest(
                command=command,
                description=user_request,
                risk_level=risk,
                status="pending",
                affected_files=final_affected_files,
                estimated_impact=final_estimated_impact,
                created_at=datetime.utcnow()
            )
            db.add(req)
            db.commit()
            db.refresh(req)
            
            # Broadcast approval queue update
            self._broadcast_safe({
                "type": "approval_queued",
                "request_id": req.id,
                "command": command,
                "description": user_request,
                "affected_files": req.affected_files,
                "estimated_impact": req.estimated_impact
            })

            return {
                "status": "pending_approval",
                "message": "This command requires approval. Request added to queue.",
                "request_id": req.id,
                "affected_files": req.affected_files,
                "estimated_impact": req.estimated_impact
            }

        # Safe - auto-execute task
        return await self.execute_approved_task(db, command, user_request, approval_method="safe_auto_exec")

    async def process_approval_action(self, db: Session, approval_id: str, action: str) -> Dict[str, Any]:
        """Approve or reject a pending command request using the shared execution pipeline."""
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
        if not approval:
            return {"status": "not_found", "message": "Approval request not found"}
        if approval.status != "pending":
            return {"status": "already_processed", "message": "Request has already been processed"}

        normalized_action = action.lower()
        if normalized_action == "reject":
            approval.status = "rejected"
            approval.processed_at = datetime.utcnow()
            db.commit()

            audit = AuditLog(
                user_request=approval.description or "Manual Approved Task",
                generated_command=approval.command,
                approval_result="rejected",
                timestamp=datetime.utcnow()
            )
            db.add(audit)
            db.commit()
            return {"status": "rejected", "id": approval_id}

        if normalized_action == "approve":
            approval.status = "approved"
            approval.processed_at = datetime.utcnow()
            db.commit()

            result = await self.execute_approved_task(
                db=db,
                command=approval.command,
                user_request=approval.description or "Manual Approved Task",
                approval_method="approved"
            )
            return {"status": "approved", "id": approval_id, "task_execution": result}

        return {"status": "invalid_action", "message": "Invalid action. Must be 'approve' or 'reject'"}

    async def execute_approved_task(self, db: Session, command: str, user_request: str, approval_method: str) -> Dict[str, Any]:
        """Starts subprocess execution for an approved or safe command."""
        # 1. Create SQL record
        task_rec = TaskRecord(
            command=command,
            status="running",
            start_time=datetime.utcnow()
        )
        db.add(task_rec)
        db.commit()
        db.refresh(task_rec)

        task_id = task_rec.id
        start_perf = time.perf_counter()

        # 2. Callback definitions for log and finish stream events
        def handle_log(log_line: str):
            # Stream real-time logs to WebSockets
            self._broadcast_safe({
                "type": "log",
                "task_id": task_id,
                "data": log_line
            })

        def handle_finish(exit_code: int, full_logs: str):
            # Lifecycle execution completed
            duration = time.perf_counter() - start_perf
            self._active_tasks.pop(task_id, None)

            # Update database transaction using thread-safe context
            # (Use a new session to avoid sharing session cross-threads on callback execution)
            from app.core.database import SessionLocal
            callback_db = SessionLocal()
            try:
                rec = callback_db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
                if rec:
                    rec.status = "completed" if exit_code == 0 else "failed"
                    # Append cancellation details if task is flagged as cancelled
                    if rec.status == "failed" and "Task execution cancelled" in rec.log_content:
                        rec.status = "cancelled"
                    rec.exit_code = exit_code
                    rec.log_content = full_logs
                    rec.finish_time = datetime.utcnow()
                
                # Add to AuditLog
                audit = AuditLog(
                    user_request=user_request,
                    generated_command=command,
                    approval_result=approval_method,
                    execution_duration=round(duration, 3),
                    exit_code=exit_code,
                    error_message=None if exit_code == 0 else "Execution failed",
                    timestamp=datetime.utcnow()
                )
                callback_db.add(audit)
                callback_db.commit()
            except Exception as e:
                print(f"Task finish DB update error: {str(e)}")
            finally:
                callback_db.close()

            # Broadcast final status update
            status_str = "completed" if exit_code == 0 else "failed"
            self._broadcast_safe({
                "type": "status",
                "task_id": task_id,
                "status": status_str,
                "exit_code": exit_code
            })

        # 3. Spawn asynchronous command
        try:
            proc = await command_executor.run_command_async(
                command=command,
                task_id=task_id,
                on_log=handle_log,
                on_finished=handle_finish
            )
            self._active_tasks[task_id] = {
                "process": proc,
                "start_time": time.time(),
                "command": command
            }
            
            # Broadcast task started
            self._broadcast_safe({
                "type": "started",
                "task_id": task_id,
                "command": command
            })

            return {"status": "running", "task_id": task_id}

        except Exception as e:
            # Fallback handling to prevent uvicorn crashes
            duration = time.perf_counter() - start_perf
            task_rec.status = "failed"
            task_rec.log_content = f"Failed to start task: {str(e)}"
            task_rec.finish_time = datetime.utcnow()
            
            audit = AuditLog(
                user_request=user_request,
                generated_command=command,
                approval_result=approval_method,
                execution_duration=round(duration, 3),
                exit_code=-1,
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
            db.add(audit)
            db.commit()
            
            return {"status": "failed", "message": str(e), "task_id": task_id}

    def cancel_task(self, db: Session, task_id: str) -> bool:
        """Cancel a running command process group."""
        task_info = self._active_tasks.get(task_id)
        if not task_info:
            return False

        proc = task_info["process"]
        
        # Write cancellation state to database record ahead of callback wait return
        rec = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
        if rec:
            rec.status = "cancelled"
            rec.log_content += "\n[Task execution cancelled by user]\n"
            db.commit()

        # Terminate process group
        success = command_executor.cancel_process(proc.pid)
        if success:
            self._active_tasks.pop(task_id, None)
            self._broadcast_safe({
                "type": "status",
                "task_id": task_id,
                "status": "cancelled"
            })
        return success


task_manager = TaskManagerService()
