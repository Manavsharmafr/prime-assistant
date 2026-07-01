from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.services.developer_workspace import developer_workspace

router = APIRouter(prefix="/developer", tags=["Developer Assistant Workspace"])

class SearchRequest(BaseModel):
    query: str
    match_case: Optional[bool] = False
    use_regex: Optional[bool] = False

class DiffRequest(BaseModel):
    file_path: str
    content: str

@router.get("/index")
def get_workspace_index():
    """Retrieve lists of functions, classes, and workspace file counts."""
    return developer_workspace.index_project()

@router.post("/search")
def search_workspace_code(request: SearchRequest):
    """Trigger structural regex or keyword grep searches across workspace modules."""
    results = developer_workspace.search_code(
        query=request.query,
        match_case=request.match_case or False,
        use_regex=request.use_regex or False
    )
    return {"status": "success", "results": results}

@router.post("/diff")
def generate_code_diff(request: DiffRequest):
    """Compute unified diff comparison between active and modified content drafts."""
    res = developer_workspace.generate_diff(request.file_path, request.content)
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@router.get("/git")
def get_workspace_git_status():
    """Query git repo uncommitted additions and branch information."""
    return developer_workspace.get_git_status()
