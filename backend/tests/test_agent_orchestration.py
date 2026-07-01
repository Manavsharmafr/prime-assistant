import pytest
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from main import app
from app.core.database import Base, get_db
from app.services.llm_provider import llm_provider
from app.services.planner import planner_service
from app.services.tool_registry import tool_registry
from app.services.task_orchestrator import task_orchestrator
from app.models.conversation import Conversation, Message

TEST_DB_URL = "sqlite:///./test_prime_orchestration.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    from sqlalchemy import text
    db = TestingSessionLocal()
    try:
        # Enable sqlite foreign keys
        db.execute(text("PRAGMA foreign_keys = ON"))
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
    if os.path.exists("./test_prime_orchestration.db"):
        try:
            os.remove("./test_prime_orchestration.db")
        except PermissionError:
            pass


# ─── LLM Provider Tests ──────────────────────────────────────────────────────

def test_llm_provider_fallback_cascades():
    """Verify that execute_prompt cascades to offline heuristic fallback when no keys are available."""
    # Temporarily force offline provider preferrence
    res = llm_provider.execute_prompt("Hello", provider_override="offline")
    assert "local offline fallback" in res.lower()


# ─── Planner Tests ──────────────────────────────────────────────────────────

def test_planner_structured_output():
    """Verify that the Planner correctly decomposes a user query into tool subtasks."""
    plan_data = planner_service.generate_plan("research react and save a note", provider_override="offline")
    assert "plan" in plan_data
    assert "reasoning" in plan_data
    assert len(plan_data["plan"]) > 0
    assert plan_data["plan"][0]["tool"] in ["research", "notes", "terminal"]


# ─── Tool Registry Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_registry_handlers():
    """Verify all default tools are registered and resolve correctly."""
    db = TestingSessionLocal()
    try:
        # 1. System tool query
        sys_res = await tool_registry.execute_tool("system", db, {"action": "stats"})
        assert "cpu" in sys_res
        assert "memory" in sys_res

        # 2. Memory tool query
        mem_save = await tool_registry.execute_tool("memory", db, {
            "action": "save",
            "content": "Simulated fact text context",
            "category": "test"
        })
        assert mem_save["status"] == "success"
        assert "memory_id" in mem_save

        mem_search = await tool_registry.execute_tool("memory", db, {
            "action": "search",
            "query": "Simulated fact"
        })
        assert mem_search["status"] == "success"
        assert len(mem_search["results"]) > 0
    finally:
        db.close()


# ─── Task Orchestrator Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_orchestrator_execution():
    """Verify end-to-end task orchestrator runs steps and compiles final response."""
    db = TestingSessionLocal()
    try:
        convo_id = "test-convo-123"
        res = await task_orchestrator.execute_user_prompt(
            db=db,
            prompt="research python and list files",
            conversation_id=convo_id,
            provider_override="offline"
        )
        assert "result" in res
        assert "steps" in res
        assert len(res["steps"]) > 0
        
        # Verify history is saved
        msgs = db.query(Message).filter(Message.conversation_id == convo_id).all()
        assert len(msgs) >= 2
        assert msgs[0].sender == "user"
        assert msgs[1].sender == "assistant"
    finally:
        db.close()


# ─── Safety Gate Integration Tests ───────────────────────────────────────────

def test_api_agents_safety_gate_integration():
    """Verify that process_agent_command routes terminal tools and triggers security challenge blocks."""
    # Submit command trigger that requires approval
    res = client.post("/api/agents/command", json={
        "prompt": "run command 'del workspace.code'",
        "conversation_id": "test-safety-convo",
        "provider": "offline"
    })
    assert res.status_code == 200
    data = res.json()
    
    # In offline fallback, a command like 'del workspace.code' will be planned as a terminal tool call.
    # The terminal tool invokes task_manager.run_task which triggers 'pending_approval' safety gate.
    assert data["status"] == "challenge_required"
    assert "request_id" in data
    assert "command" in data
