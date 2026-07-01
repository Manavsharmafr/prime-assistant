from sqlalchemy import Column, String, DateTime, Float, Integer, Text
from datetime import datetime
import uuid
from app.core.database import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    command = Column(Text, nullable=False)
    description = Column(String, nullable=True)
    risk_level = Column(String, default="confirmation_required")  # 'safe', 'confirmation_required', 'blocked'
    status = Column(String, default="pending")  # 'pending', 'approved', 'rejected', 'cancelled'
    affected_files = Column(Text, nullable=True)
    estimated_impact = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class TaskRecord(Base):
    __tablename__ = "task_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    command = Column(Text, nullable=False)
    status = Column(String, default="running")  # 'running', 'completed', 'failed', 'cancelled'
    log_content = Column(Text, default="")
    exit_code = Column(Integer, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    finish_time = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_request = Column(Text, nullable=False)
    generated_command = Column(Text, nullable=False)
    approval_result = Column(String, nullable=False)  # 'approved', 'rejected', 'blocked_automatically', 'safe_auto_exec'
    execution_duration = Column(Float, nullable=True)  # duration in seconds
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
