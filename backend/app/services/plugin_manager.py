import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.automation import PluginRecord
from app.services.tool_registry import tool_registry

class PluginManagerService:
    def __init__(self):
        self.default_plugins = {
            "github": {
                "name": "GitHub Integration",
                "description": "Exposes actions to search repositories, analyze files, list issues, pull requests, and commit logs.",
                "version": "1.0.0",
                "health_status": "healthy",
                "required_permissions": ["network_access", "read_files"],
                "actions": ["repo_search", "analyze_repo", "issues_list", "pr_list", "commit_info"]
            },
            "linkedin": {
                "name": "LinkedIn Assistant",
                "description": "Analyze professional profiles, career suggestions, and tailor resume details.",
                "version": "1.0.0",
                "health_status": "healthy",
                "required_permissions": ["network_access"],
                "actions": ["analyze_profile", "career_tips", "resume_opt"]
            },
            "notion": {
                "name": "Notion Sync",
                "description": "Enables reading, writing, searching, and managing Notion workspace workspaces and pages.",
                "version": "1.0.0",
                "health_status": "healthy",
                "required_permissions": ["network_access"],
                "actions": ["read_page", "write_page", "search_workspace"]
            },
            "google_workspace": {
                "name": "Google Workspace Integration",
                "description": "Provides sync pipelines with Gmail messages, Google Calendar schedules, Drive directories, and Docs.",
                "version": "1.0.0",
                "health_status": "healthy",
                "required_permissions": ["network_access"],
                "actions": ["gmail_list", "calendar_list", "drive_search", "doc_read"]
            },
            "browser": {
                "name": "Local Web Browsers",
                "description": "Manage active browser profiles and automate scraping routes across Chrome, Edge, and Firefox.",
                "version": "1.0.0",
                "health_status": "healthy",
                "required_permissions": ["process_execution", "network_access"],
                "actions": ["browser_scrape", "browser_cookies"]
            },
            "file_system": {
                "name": "Workspace File System Indexer",
                "description": "High performance file system search, indexing, metadata caching, and batch file editing tools.",
                "version": "1.0.0",
                "health_status": "healthy",
                "required_permissions": ["read_files", "write_files"],
                "actions": ["batch_file_edit", "workspace_index"]
            }
        }

    def initialize_plugins(self, db: Session):
        """Pre-populate the plugin configuration table with defaults if empty."""
        for pid, meta in self.default_plugins.items():
            record = db.query(PluginRecord).filter(PluginRecord.id == pid).first()
            if not record:
                record = PluginRecord(
                    id=pid,
                    enabled=True,
                    config=json.dumps({"api_key": "", "token": "", "mock_mode": True}),
                    health_status=meta["health_status"]
                )
                db.add(record)
        db.commit()
        self.register_plugin_tools(db)

    def register_plugin_tools(self, db: Session):
        """Dynamically register tool interfaces of enabled plugins into the central ToolRegistry."""
        records = db.query(PluginRecord).all()
        active_pids = {r.id: r for r in records if r.enabled}

        # 1. Register GitHub Actions
        if "github" in active_pids:
            async def github_tool(db: Session, action: str, query: Optional[str] = None, repo: Optional[str] = None) -> Dict[str, Any]:
                # Verify token or run in mock mode
                return {"status": "success", "plugin": "github", "action": action, "output": f"Mock GitHub output for action '{action}' on repo '{repo}' using query '{query}'"}
            
            tool_registry.register_tool(
                name="github",
                description=self.default_plugins["github"]["description"],
                handler=github_tool,
                parameters={"action": "repo_search/issues_list/pr_list/commit_info", "query": "Filter criteria", "repo": "Target repo path"}
            )

        # 2. Register LinkedIn Actions
        if "linkedin" in active_pids:
            async def linkedin_tool(db: Session, action: str, profile_url: Optional[str] = None, resume_text: Optional[str] = None) -> Dict[str, Any]:
                return {"status": "success", "plugin": "linkedin", "action": action, "output": f"Mock LinkedIn output for '{action}'"}
            
            tool_registry.register_tool(
                name="linkedin",
                description=self.default_plugins["linkedin"]["description"],
                handler=linkedin_tool,
                parameters={"action": "analyze_profile/career_tips/resume_opt", "profile_url": "LinkedIn url", "resume_text": "Resume markdown"}
            )

        # 3. Register Notion Actions
        if "notion" in active_pids:
            async def notion_tool(db: Session, action: str, page_id: Optional[str] = None, title: Optional[str] = None, content: Optional[str] = None) -> Dict[str, Any]:
                return {"status": "success", "plugin": "notion", "action": action, "output": f"Mock Notion output for '{action}'"}
            
            tool_registry.register_tool(
                name="notion",
                description=self.default_plugins["notion"]["description"],
                handler=notion_tool,
                parameters={"action": "read_page/write_page/search_workspace", "page_id": "Page UUID", "title": "New page title"}
            )

        # 4. Register Google Workspace Actions
        if "google_workspace" in active_pids:
            async def google_tool(db: Session, action: str, query: Optional[str] = None) -> Dict[str, Any]:
                return {"status": "success", "plugin": "google_workspace", "action": action, "output": f"Mock Google Workspace output for '{action}'"}
            
            tool_registry.register_tool(
                name="google_workspace",
                description=self.default_plugins["google_workspace"]["description"],
                handler=google_tool,
                parameters={"action": "gmail_list/calendar_list/drive_search/doc_read", "query": "Search search query"}
            )

        # 5. Register Browser Actions
        if "browser" in active_pids:
            async def browser_plugin_tool(db: Session, action: str, url: str) -> Dict[str, Any]:
                return {"status": "success", "plugin": "browser", "action": action, "output": f"Mock browser scrape from target '{url}'"}
            
            tool_registry.register_tool(
                name="browser_plugin",
                description=self.default_plugins["browser"]["description"],
                handler=browser_plugin_tool,
                parameters={"action": "browser_scrape", "url": "Scrape target url"}
            )

        # 6. Register File System Actions
        if "file_system" in active_pids:
            async def fs_plugin_tool(db: Session, action: str, dir_path: str) -> Dict[str, Any]:
                return {"status": "success", "plugin": "file_system", "action": action, "output": f"Mock FS output for '{action}' inside '{dir_path}'"}
            
            tool_registry.register_tool(
                name="file_system_plugin",
                description=self.default_plugins["file_system"]["description"],
                handler=fs_plugin_tool,
                parameters={"action": "batch_file_edit/workspace_index", "dir_path": "Directory path target"}
            )

    def enable_plugin(self, db: Session, pid: str) -> bool:
        record = db.query(PluginRecord).filter(PluginRecord.id == pid).first()
        if record:
            record.enabled = True
            db.commit()
            self.register_plugin_tools(db)
            return True
        return False

    def disable_plugin(self, db: Session, pid: str) -> bool:
        record = db.query(PluginRecord).filter(PluginRecord.id == pid).first()
        if record:
            record.enabled = False
            db.commit()
            # Remove dynamically registered tool from list
            tool_registry._tools.pop(pid, None)
            tool_registry._tools.pop(f"{pid}_plugin", None)
            return True
        return False

    def get_plugins_list(self, db: Session) -> List[Dict[str, Any]]:
        records = {r.id: r for r in db.query(PluginRecord).all()}
        out = []
        for pid, meta in self.default_plugins.items():
            record = records.get(pid)
            out.append({
                "id": pid,
                "name": meta["name"],
                "description": meta["description"],
                "version": meta["version"],
                "enabled": record.enabled if record else False,
                "health_status": record.health_status if record else "offline",
                "required_permissions": meta["required_permissions"],
                "actions": meta["actions"],
                "config": json.loads(record.config) if record and record.config else {}
            })
        return out

    def update_plugin_config(self, db: Session, pid: str, config: Dict[str, Any]) -> bool:
        record = db.query(PluginRecord).filter(PluginRecord.id == pid).first()
        if record:
            record.config = json.dumps(config)
            db.commit()
            return True
        return False

plugin_manager = PluginManagerService()
