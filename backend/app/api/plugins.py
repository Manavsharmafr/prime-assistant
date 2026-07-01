from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.core.database import get_db
from app.services.plugin_manager import plugin_manager
from app.services.mcp_client import mcp_client

router = APIRouter(prefix="/plugins", tags=["Plugins & MCP Core"])

class ConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]

class MCPServerRegisterRequest(BaseModel):
    name: str
    url: str

@router.get("")
def list_plugins(db: Session = Depends(get_db)):
    """Retrieve all available system plugins and their state."""
    return plugin_manager.get_plugins_list(db)

@router.post("/{pid}/enable")
def enable_plugin(pid: str, db: Session = Depends(get_db)):
    """Activate a tool plugin dynamically."""
    success = plugin_manager.enable_plugin(db, pid)
    if not success:
        raise HTTPException(status_code=404, detail=f"Plugin '{pid}' not found.")
    return {"status": "success", "message": f"Plugin '{pid}' enabled."}

@router.post("/{pid}/disable")
def disable_plugin(pid: str, db: Session = Depends(get_db)):
    """Deactivate a tool plugin dynamically."""
    success = plugin_manager.disable_plugin(db, pid)
    if not success:
        raise HTTPException(status_code=404, detail=f"Plugin '{pid}' not found.")
    return {"status": "success", "message": f"Plugin '{pid}' disabled."}

@router.post("/{pid}/config")
def update_plugin_config(pid: str, request: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """Update configurations and API keys securely."""
    success = plugin_manager.update_plugin_config(db, pid, request.config)
    if not success:
        raise HTTPException(status_code=404, detail=f"Plugin '{pid}' not found.")
    return {"status": "success", "message": f"Configuration updated for plugin '{pid}'."}

@router.get("/mcp")
def list_mcp_servers():
    """List connected Model Context Protocol servers and discovered capabilities."""
    return mcp_client.get_configured_servers()

@router.post("/mcp")
def register_mcp_server(request: MCPServerRegisterRequest):
    """Dynamically register a new MCP server connection."""
    server = mcp_client.add_mcp_server(request.name, request.url)
    return {"status": "success", "message": f"MCP server '{request.name}' registered successfully.", "server": server}
