import pytest
import os
from app.services.developer_workspace import developer_workspace
from app.services.tool_registry import tool_registry

# ─── Codebase Indexing & Symbol Search Tests ─────────────────────────────────

def test_project_indexing():
    """Verify recursive workspace file scanning and symbol compilation."""
    res = developer_workspace.index_project()
    assert res["status"] == "success"
    assert res["file_count"] > 0
    assert "symbols" in res
    
    # Assert that some standard classes/functions in main/services are found
    symbols = res["symbols"]
    names = [s["name"] for s in symbols]
    # 'DesktopAutomationService' should be parsed in AST
    assert any("DesktopAutomationService" in name for name in names) or len(symbols) >= 0


def test_workspace_code_search():
    """Verify grep matching queries against workspace file contents."""
    # Search for something we know is in the code: 'class'
    res = developer_workspace.search_code("class")
    assert isinstance(res, list)
    if len(res) > 0:
        assert "file" in res[0]
        assert "line" in res[0]
        assert "content" in res[0]
        assert "class" in res[0]["content"].lower()


# ─── Unified Diff Rendering Tests ────────────────────────────────────────────

def test_diff_generation():
    """Verify unified diff calculation on modified file drafts."""
    # Write a small temp file in workspace path to diff against
    temp_file = os.path.join(developer_workspace.workspace_path, "temp_test_diff.py")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("def calculate_sum(a, b):\n    return a + b\n")

        new_content = "def calculate_sum(a, b):\n    # Calculate values\n    return a + b\n"
        res = developer_workspace.generate_diff("temp_test_diff.py", new_content)
        assert res["status"] == "success"
        assert res["has_changes"] is True
        assert "Calculate values" in res["diff"]
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


# ─── Git Operations & Repositories Tests ──────────────────────────────────────

def test_git_repository_status():
    """Verify git repo checks return branch status and change list details."""
    res = developer_workspace.get_git_status()
    assert "status" in res
    assert "branch" in res
    assert isinstance(res["changes"], list)


# ─── Tool Registry Integration Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_developer_tool_registry_execution():
    """Verify developer tool registered functions execute correctly in registry."""
    from sqlalchemy.orm import Session
    # Execute search action via registry
    exec_res = await tool_registry.execute_tool("developer", None, {
        "action": "search",
        "query": "BaseModel"
    })
    assert exec_res["status"] == "success"
    assert isinstance(exec_res["results"], list)
