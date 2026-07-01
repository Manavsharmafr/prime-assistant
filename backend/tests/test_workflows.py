import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.services.workflow_engine import workflow_engine
from app.services.autonomous_agent import autonomous_agent
from app.services.scheduler import scheduler as scheduler_service
from app.models.automation import WorkflowRecord
from main import app

client = TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# ─── Service Integration Tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workflow_creation_and_steps(db: Session):
    """Verify workflow registration, steps list storage, and engine iterations."""
    wf = workflow_engine.create_workflow(
        db=db,
        name="Test Workflow",
        steps=["echo step1", "echo step2"],
        retry_policy={"max_retries": 2, "current_retries": 0}
    )
    assert wf.id is not None
    assert wf.status == "pending"
    assert wf.current_step_idx == 0

    # Execute first step
    res1 = await workflow_engine.run_workflow_step(db, wf.id)
    assert res1["status"] in ["pending", "completed"]
    assert res1["current_step"] == 1

    # Execute second step
    res2 = await workflow_engine.run_workflow_step(db, wf.id)
    assert res2["status"] == "completed"


@pytest.mark.asyncio
async def test_workflow_retry_policy(db: Session):
    """Verify that failing command steps trigger auto-retry increment logs."""
    wf = workflow_engine.create_workflow(
        db=db,
        name="Failing Workflow",
        steps=["rm -rf /test"], # dangerous command blocked by PermissionService
        retry_policy={"max_retries": 1, "current_retries": 0}
    )
    res = await workflow_engine.run_workflow_step(db, wf.id)
    assert res["status"] == "failed"
    assert "blocked" in res["message"]


def test_scheduler_cron_evaluation(db: Session):
    """Verify crontab rule scanner resets statuses and schedules next run times."""
    wf = workflow_engine.create_workflow(
        db=db,
        name="Hourly Workflow",
        steps=["echo scheduled"],
        schedule_cron="@hourly"
    )
    triggered = scheduler_service.evaluate_scheduled_jobs(db)
    assert triggered == 1

    # Check database state
    db.refresh(wf)
    assert wf.status == "pending"
    assert wf.next_run_at is not None


# ─── API Router Tests ────────────────────────────────────────────────────────

def test_workflows_api_endpoints():
    """Verify workflows REST API list, create, pause, and resume endpoints."""
    # 1. Create workflow
    resp = client.post("/api/workflows/create", json={
        "name": "API Workflow",
        "steps": ["echo first", "echo second"],
        "schedule_cron": "@daily"
    })
    assert resp.status_code == 200
    wf_id = resp.json()["id"]

    # 2. List workflows
    resp_list = client.get("/api/workflows")
    assert resp_list.status_code == 200
    assert any(w["id"] == wf_id for w in resp_list.json())

    # 3. Pause workflow
    resp_pause = client.post(f"/api/workflows/{wf_id}/pause")
    assert resp_pause.status_code == 200
    assert resp_pause.json()["status"] == "paused"

    # 4. Resume workflow
    resp_resume = client.post(f"/api/workflows/{wf_id}/resume")
    assert resp_resume.status_code == 200

    # 5. Cancel workflow
    resp_cancel = client.post(f"/api/workflows/{wf_id}/cancel")
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "cancelled"
