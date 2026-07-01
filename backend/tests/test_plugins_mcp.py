import pytest
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from main import app
from app.core.database import Base, get_db
from app.services.plugin_manager import plugin_manager
from app.services.mcp_client import mcp_client
from app.services.tool_registry import tool_registry

TEST_DB_URL = "sqlite:///./test_prime_plugins.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        db.execute(text("PRAGMA foreign_keys = ON"))
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        plugin_manager.initialize_plugins(db)
    finally:
        db.close()
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_prime_plugins.db"):
        try:
            os.remove("./test_prime_plugins.db")
        except PermissionError:
            pass


# ─── Plugin Manager Lifecycle Tests ──────────────────────────────────────────

def test_plugin_list_and_initialization():
    """Verify that default plugins are pre-populated in database and retrieved correctly."""
    db = TestingSessionLocal()
    try:
        plugins = plugin_manager.get_plugins_list(db)
        assert len(plugins) >= 6
        pids = [p["id"] for p in plugins]
        assert "github" in pids
        assert "notion" in pids
        assert "file_system" in pids
    finally:
        db.close()


def test_plugin_activation_and_deactivation():
    """Verify that enabling/disabling plugins dynamically binds/unbinds tools in registry."""
    db = TestingSessionLocal()
    try:
        # Disable GitHub plugin
        success = plugin_manager.disable_plugin(db, "github")
        assert success is True
        assert tool_registry.get_tool("github") is None

        # Re-enable GitHub plugin
        success = plugin_manager.enable_plugin(db, "github")
        assert success is True
        assert tool_registry.get_tool("github") is not None
    finally:
        db.close()


def test_plugin_config_update():
    """Verify updating plugin credentials updates JSON config field."""
    db = TestingSessionLocal()
    try:
        new_config = {"api_key": "test_token_abc_123", "mock_mode": False}
        success = plugin_manager.update_plugin_config(db, "notion", new_config)
        assert success is True

        plugins = plugin_manager.get_plugins_list(db)
        notion_plugin = next(p for p in plugins if p["id"] == "notion")
        assert notion_plugin["config"]["api_key"] == "test_token_abc_123"
        assert notion_plugin["config"]["mock_mode"] is False
    finally:
        db.close()


# ─── MCP Tool Integration Tests ──────────────────────────────────────────────

def test_mcp_server_discovery():
    """Verify that client queries configured MCP servers and lists their tools."""
    servers = mcp_client.get_configured_servers()
    assert len(servers) >= 2
    
    server_ids = [s["id"] for s in servers]
    assert "postgres-db-mcp" in server_ids
    assert "vector-mem-mcp" in server_ids

    # Confirms tool metadata is present
    postgres_server = next(s for s in servers if s["id"] == "postgres-db-mcp")
    tool_names = [t["name"] for t in postgres_server["tools"]]
    assert "sql_query" in tool_names


@pytest.mark.asyncio
async def test_mcp_custom_server_registration():
    """Verify registering a new MCP server registers its custom tools in ToolRegistry."""
    res = client.post("/api/plugins/mcp", json={
        "name": "Jira Workspace MCP",
        "url": "http://127.0.0.1:9095"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "jira-workspace-mcp" in data["server"]["id"]

    # Verify custom tool is dynamically registered in ToolRegistry
    custom_tool = tool_registry.get_tool("jira-workspace-mcp_custom_tool")
    assert custom_tool is not None
    assert "[MCP Tool]" in custom_tool["description"]

    # Execute custom MCP tool and verify fallback mock execution path
    db = TestingSessionLocal()
    try:
        exec_res = await tool_registry.execute_tool("jira-workspace-mcp_custom_tool", db, {"payload": "issue_key: PR-100"})
        assert exec_res["status"] == "success"
        assert "jira-workspace-mcp_custom_tool" in exec_res["tool"]
    finally:
        db.close()
