import os
import json
from typing import Dict, Any, Callable, Optional, List
from sqlalchemy.orm import Session

from app.services.task_manager import task_manager
from app.services.research_service import research_service
from app.services.system_monitor import system_monitor
from app.services.playwright_client import playwright_browser
from app.memory.semantic_memory import memory_service, retrieval_service
from app.models.memory import Note, Tag
from app.core.config import settings

class ToolRegistryService:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register_tool(self, name: str, description: str, handler: Callable[..., Any], parameters: Dict[str, Any]):
        """Register a pluggable tool capability."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "parameters": parameters
        }

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())

    async def execute_tool(self, name: str, db: Session, arguments: Dict[str, Any]) -> Any:
        """Locate and invoke the handler matching the registered tool."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' is not registered in the tool registry.")
        
        # Inject DB session to execution handler if needed
        handler = tool["handler"]
        try:
            # If the handler is a coroutine, await it
            import inspect
            if inspect.iscoroutinefunction(handler):
                return await handler(db=db, **arguments)
            return handler(db=db, **arguments)
        except TypeError:
            # Fallback if handler doesn't accept db session argument
            if inspect.iscoroutinefunction(handler):
                return await handler(**arguments)
            return handler(**arguments)

    def _register_default_tools(self):
        # 1. Terminal Tool
        async def run_terminal(db: Session, command: str) -> Dict[str, Any]:
            # Always routes through task_manager/PermissionService/AuditLog
            return await task_manager.run_task(db, command, "Agent Orchestrator CLI Task")

        self.register_tool(
            name="terminal",
            description="Execute operating system CLI commands. Automatically validated for safety policies.",
            handler=run_terminal,
            parameters={"command": "Command string to execute"}
        )

        # 2. File Tool
        async def file_operation(db: Session, action: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
            # Ensure path is absolute and within workspace path to prevent directory traversal
            clean_path = os.path.normpath(path)
            if not os.path.isabs(clean_path):
                clean_path = os.path.join(settings.PRIME_WORKSPACE_PATH, clean_path)
            
            # Restrict access to prime-workspace folder
            if not clean_path.startswith(settings.PRIME_WORKSPACE_PATH):
                raise PermissionError("Access denied: File tool operations are restricted to the active workspace path.")

            if action == "read":
                if not os.path.exists(clean_path):
                    return {"status": "error", "message": "File not found"}
                with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                    return {"status": "success", "content": f.read()}
            elif action == "write":
                os.makedirs(os.path.dirname(clean_path), exist_ok=True)
                with open(clean_path, "w", encoding="utf-8") as f:
                    f.write(content or "")
                return {"status": "success", "message": f"Successfully wrote content to {path}"}
            elif action == "list":
                if not os.path.exists(clean_path):
                    return {"status": "error", "message": "Directory not found"}
                files = os.listdir(clean_path)
                return {"status": "success", "files": files}
            else:
                return {"status": "error", "message": f"Unknown file action: {action}"}

        self.register_tool(
            name="file",
            description="Read, write, or list files and directories inside the active workspace.",
            handler=file_operation,
            parameters={"action": "read/write/list", "path": "Relative or absolute target path", "content": "Text content for writing"}
        )

        # 3. Browser Tool
        async def fetch_page(db: Session, url: str) -> Dict[str, Any]:
            data = await playwright_browser.fetch_page_content(url)
            return {"status": "success", "title": data["title"], "content": data["content"][:2000] + "..."}

        self.register_tool(
            name="browser",
            description="Retrieve raw markdown text content from public web urls using Playwright headless browser.",
            handler=fetch_page,
            parameters={"url": "Target URL link"}
        )

        # 4. Research Tool
        async def research_topic(db: Session, query: str) -> Dict[str, Any]:
            report = await research_service.compile_research_report(query)
            return report

        self.register_tool(
            name="research",
            description="Perform a web query using DuckDuckGo scraping, parse results, and compile a research report.",
            handler=research_topic,
            parameters={"query": "Search query string"}
        )

        # 5. System Tool
        def fetch_system_metrics(db: Session, action: str = "stats") -> Dict[str, Any]:
            return system_monitor.get_system_status_payload()

        self.register_tool(
            name="system",
            description="Query live operating system telemetry, process statistics, battery status, and uptime metrics.",
            handler=fetch_system_metrics,
            parameters={"action": "stats"}
        )

        # 6. Notes Tool
        def notes_operation(db: Session, title: str, content: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
            note = Note(title=title, content=content)
            if tags:
                for tag_name in tags:
                    tag = db.query(Tag).filter(Tag.name == tag_name.lower()).first()
                    if not tag:
                        tag = Tag(name=tag_name.lower())
                        db.add(tag)
                    note.tags.append(tag)
            db.add(note)
            db.commit()
            db.refresh(note)
            
            # Re-index to vector memory
            memory_service.create_memory(
                db=db,
                content=f"Note: {note.title}\nContent: {note.content}",
                category="note",
                metadata={"note_id": note.id}
            )
            return {"status": "success", "note_id": note.id, "title": note.title}

        self.register_tool(
            name="notes",
            description="Create persistent text notes and tag records in the database, automatically indexing them in vector memory.",
            handler=notes_operation,
            parameters={"title": "Note title", "content": "Markdown text note content", "tags": "Optional list of tag names"}
        )

        # 7. Memory Tool
        def memory_operation(db: Session, action: str, query: Optional[str] = None, content: Optional[str] = None, category: str = "general") -> Dict[str, Any]:
            if action == "save":
                if not content:
                    return {"status": "error", "message": "Content parameter required to save semantic memory."}
                entry = memory_service.create_memory(db, content, category)
                return {"status": "success", "memory_id": entry.id}
            elif action == "search":
                if not query:
                    return {"status": "error", "message": "Query parameter required to search memory."}
                entries = retrieval_service.retrieve_similar_memories(db, query, limit=5)
                return {
                    "status": "success",
                    "results": [{"id": m.id, "content": m.content, "category": m.category} for m in entries]
                }
            else:
                return {"status": "error", "message": f"Unknown memory action: {action}"}

        self.register_tool(
            name="memory",
            description="Persist semantic facts or perform hybrid search across vectors and historical entries.",
            handler=memory_operation,
            parameters={"action": "save/search", "query": "Search query text", "content": "Text to index", "category": "Memory type category"}
        )

tool_registry = ToolRegistryService()
