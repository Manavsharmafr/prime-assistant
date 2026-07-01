import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os

from main import app
from app.core.database import Base, get_db
from app.models.automation import ApprovalRequest, TaskRecord, AuditLog
from app.services.system_monitor import system_monitor
from app.services.permission import permission_service
from app.services.task_manager import task_manager

TEST_DB_URL = "sqlite:///./test_prime_automation.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_prime_automation.db"):
        try:
            os.remove("./test_prime_automation.db")
        except PermissionError:
            pass


# ─── System Monitor Tests ────────────────────────────────────────────────────

def test_system_monitoring_service():
    """Test SystemMonitorService metrics extraction returns all required fields."""
    payload = system_monitor.get_system_status_payload()
    assert "cpu" in payload
    assert "percent" in payload["cpu"]
    assert "cores" in payload["cpu"]
    assert "temp" in payload["cpu"]
    assert "memory" in payload
    assert "percent" in payload["memory"]
    assert "used_gb" in payload["memory"]
    assert "total_gb" in payload["memory"]
    assert "disk" in payload
    assert "network" in payload
    assert "upload_kb_s" in payload["network"]
    assert "download_kb_s" in payload["network"]
    assert "uptime_seconds" in payload
    assert isinstance(payload["uptime_seconds"], float)
    assert "top_processes" in payload
    assert isinstance(payload["top_processes"], list)


def test_ws_stats_endpoint():
    """Test /api/ws/stats WebSocket streams a valid telemetry payload on connect."""
    with client.websocket_connect("/api/ws/stats") as websocket:
        data = websocket.receive_json()
        assert "cpu" in data
        assert "memory" in data
        assert "uptime_seconds" in data
        assert "top_processes" in data


# ─── Permission Service Tests ─────────────────────────────────────────────────

def test_permission_service_safe_commands():
    """Safe commands auto-execute without approval."""
    safe_cases = ["code", "calc", "ls", "dir", "echo hello", "whoami", "hostname", "ping google.com"]
    for cmd in safe_cases:
        risk, _ = permission_service.check_permission(cmd)
        assert risk == "safe", f"Expected 'safe' for: {cmd}, got {risk}"


def test_permission_service_blocked_commands():
    """Blocked commands are immediately rejected."""
    blocked_cases = [
        "format C:",
        "format D: /FS:NTFS",
        "reg delete HKLM\\Software",
        "reg add HKCU\\Test",
        "net user admin newpass",
        "rm -rf /",
        "rm -r /home",
        "diskpart",
        "secedit /configure",
        "powershell Set-ExecutionPolicy Unrestricted",
    ]
    for cmd in blocked_cases:
        risk, reason = permission_service.check_permission(cmd)
        assert risk == "blocked", f"Expected 'blocked' for: {cmd}, got {risk} ({reason})"


def test_permission_service_confirmation_required():
    """Unknown/shell commands default to confirmation_required."""
    confirm_cases = [
        "git commit -m 'Initial'",
        "npm install -g pm2",
        "pip install requests",
        "del /f important.txt",
    ]
    for cmd in confirm_cases:
        risk, _ = permission_service.check_permission(cmd)
        assert risk == "confirmation_required", f"Expected 'confirmation_required' for: {cmd}, got {risk}"


# ─── REST API Endpoints Tests ─────────────────────────────────────────────────

def test_api_run_safe_command():
    """Safe commands submitted via REST auto-execute and return running status."""
    # 'echo' is a safe command
    res = client.post("/api/automation/tasks", json={
        "command": "echo Phase4 safety test",
        "user_request": "Test safe command auto-exec"
    })
    assert res.status_code == 200
    data = res.json()
    # Should auto-execute since echo is safe
    assert data["status"] in ("running", "completed")
    assert "task_id" in data


def test_api_run_blocked_command():
    """Blocked commands return blocked status with no task_id."""
    res = client.post("/api/automation/tasks", json={
        "command": "format D:",
        "user_request": "Attempt to format a drive"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "blocked"
    assert data.get("task_id") is None


def test_api_run_confirmation_required_command():
    """Commands requiring confirmation land in pending_approval queue."""
    res = client.post("/api/automation/tasks", json={
        "command": "git status",
        "user_request": "Check git repository state"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending_approval"
    assert "request_id" in data


def test_api_list_approval_queue():
    """Approval queue lists pending requests correctly."""
    res = client.get("/api/automation/approvals?status=pending")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_approval_reject():
    """Rejected approval request updates status and logs result."""
    # Submit a command requiring approval
    submit = client.post("/api/automation/tasks", json={
        "command": "pip install numpy",
        "user_request": "Install numpy package"
    })
    assert submit.json()["status"] == "pending_approval"
    req_id = submit.json()["request_id"]

    # Reject it
    action = client.post(f"/api/automation/approvals/{req_id}/action", json={"action": "reject"})
    assert action.status_code == 200
    assert action.json()["status"] == "rejected"

    # Confirm DB state: audit log created, status = rejected
    audit_res = client.get("/api/automation/audit")
    assert audit_res.status_code == 200
    audit_entries = audit_res.json()
    rejected_entries = [e for e in audit_entries if e["generated_command"] == "pip install numpy"]
    assert len(rejected_entries) > 0
    assert rejected_entries[0]["approval_result"] == "rejected"


def test_api_approval_approve_and_execute():
    """Approving a queued command runs it and creates a task record."""
    # Submit command
    submit = client.post("/api/automation/tasks", json={
        "command": "echo approval_test_confirmed",
        "user_request": "Test approval workflow end-to-end"
    })
    # echo is actually safe so it might auto-exec; test with a git command instead
    submit2 = client.post("/api/automation/tasks", json={
        "command": "git log --oneline -5",
        "user_request": "Review recent git history"
    })
    assert submit2.json()["status"] == "pending_approval"
    req_id = submit2.json()["request_id"]

    # Approve it
    action = client.post(f"/api/automation/approvals/{req_id}/action", json={"action": "approve"})
    assert action.status_code == 200
    assert action.json()["status"] == "approved"
    task_exec = action.json()["task_execution"]
    assert task_exec["status"] in ("running", "completed", "failed")  # may fail if no git repo, but must not error


def test_api_task_list():
    """Task history list returns records."""
    res = client.get("/api/automation/tasks")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_audit_logs():
    """Audit log captures all execution decisions."""
    res = client.get("/api/automation/audit")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    # Each entry must have required fields
    for entry in logs[:5]:
        assert "generated_command" in entry
        assert "approval_result" in entry
        assert "timestamp" in entry


# ─── Blocked Commands Cannot Bypass Safety Gate ───────────────────────────────

def test_blocked_commands_create_audit_trail():
    """Every blocked command attempt is persisted in audit logs."""
    dangerous_commands = ["diskpart", "format C:", "reg delete HKCU\\Test"]
    for cmd in dangerous_commands:
        client.post("/api/automation/tasks", json={
            "command": cmd,
            "user_request": f"Attempted: {cmd}"
        })

    res = client.get("/api/automation/audit")
    audit_logs = res.json()
    blocked_logs = [e for e in audit_logs if e["approval_result"] == "blocked_automatically"]
    assert len(blocked_logs) >= len(dangerous_commands)


def test_approval_already_processed_returns_error():
    """Processing an already-actioned approval returns 400."""
    # Submit and immediately reject
    submit = client.post("/api/automation/tasks", json={
        "command": "mvn clean install",
        "user_request": "Build maven project"
    })
    req_id = submit.json()["request_id"]
    client.post(f"/api/automation/approvals/{req_id}/action", json={"action": "reject"})

    # Try to act on it again
    second = client.post(f"/api/automation/approvals/{req_id}/action", json={"action": "approve"})
    assert second.status_code == 400


def test_phase4_permission_analysis():
    """Verify Phase 4 PermissionService analyze_command returns all safety metadata."""
    res = permission_service.analyze_command("pip install requests")
    assert res["risk_level"] == "confirmation_required"
    assert "dependencies" in res["affected_files"].lower()
    assert "install" in res["estimated_impact"].lower()

    res_blocked = permission_service.analyze_command("format E:")
    assert res_blocked["risk_level"] == "blocked"
    assert "system" in res_blocked["affected_files"].lower()

    res_safe = permission_service.analyze_command("systeminfo")
    assert res_safe["risk_level"] == "safe"
    assert "read-only" in res_safe["affected_files"].lower()


def test_api_phase4_metadata_propagation():
    """Verify that metadata fields affected_files and estimated_impact propagate through run_task."""
    res = client.post("/api/automation/tasks", json={
        "command": "git commit -m 'Test'",
        "user_request": "Make a test commit",
        "affected_files": "TestFile.txt",
        "estimated_impact": "Record state changes in version control"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending_approval"
    assert data["affected_files"] == "TestFile.txt"
    assert data["estimated_impact"] == "Record state changes in version control"
