import uvicorn
import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.models import Base
from app.api.system import router as system_router
from app.api.agents import router as agents_router
from app.api.memory import router as memory_router
from app.api.automation import router as automation_router
from app.services.system_monitor import system_monitor, stats_ws_manager
from app.services.task_manager import tasks_ws_manager

# Ensure local databases/directories are setup
os.makedirs(settings.PRIME_WORKSPACE_PATH, exist_ok=True)

# Create SQLAlchemy Database tables
# Currently, models aren't imported, but Base metadata is prepared.
# When we add models, we will import them here so they register with Base.metadata.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Prime Local Assistant Backend",
    description="Local server facilitating system access, vector search, research, and command safety gates.",
    version="1.0.0"
)

# Enable CORS for local client development (e.g. React running on localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development, restrict in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.plugins import router as plugins_router
from app.api.desktop import router as desktop_router
from app.api.developer import router as developer_router
from app.api.workflows import router as workflows_router

# Attach API routers
app.include_router(system_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(automation_router, prefix="/api")
app.include_router(plugins_router, prefix="/api")
app.include_router(desktop_router, prefix="/api")
app.include_router(developer_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")

# Background stats loop task reference
stats_task = None

@app.on_event("startup")
async def startup_event():
    # Dynamic SQLite schema update to support Phase 4 requirements
    from sqlalchemy import text
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        res = db.execute(text("PRAGMA table_info(approval_requests)")).fetchall()
        columns = [row[1] for row in res]
        if "affected_files" not in columns:
            db.execute(text("ALTER TABLE approval_requests ADD COLUMN affected_files TEXT;"))
        if "estimated_impact" not in columns:
            db.execute(text("ALTER TABLE approval_requests ADD COLUMN estimated_impact TEXT;"))
        db.commit()

        # Initialize plugins and register tools
        from app.services.plugin_manager import plugin_manager
        from app.services.mcp_client import mcp_client
        plugin_manager.initialize_plugins(db)
        mcp_client.register_discovered_mcp_tools()
    except Exception as e:
        print(f"Database schema migration/plugin init error: {str(e)}")
    finally:
        db.close()

    global stats_task
    async def poll_system_stats_loop():
        while True:
            try:
                payload = system_monitor.get_system_status_payload()
                await stats_ws_manager.broadcast(payload)
            except Exception as e:
                print(f"Stats broadcast error: {str(e)}")
            await asyncio.sleep(2.0)
    stats_task = asyncio.create_task(poll_system_stats_loop())

@app.on_event("shutdown")
async def shutdown_event():
    global stats_task
    if stats_task:
        stats_task.cancel()

# --- WebSocket Endpoints ---

@app.websocket("/api/ws/stats")
async def ws_stats_endpoint(websocket: WebSocket):
    await stats_ws_manager.connect(websocket)
    try:
        # Stream initial telemetry payload immediately
        initial_stats = system_monitor.get_system_status_payload()
        await websocket.send_json(initial_stats)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        stats_ws_manager.disconnect(websocket)
    except Exception:
        stats_ws_manager.disconnect(websocket)

@app.websocket("/api/ws/tasks")
async def ws_tasks_endpoint(websocket: WebSocket):
    await tasks_ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        tasks_ws_manager.disconnect(websocket)
    except Exception:
        tasks_ws_manager.disconnect(websocket)


@app.get("/")
async def root():
    return {
        "message": "Prime Backend is active.",
        "docs": "/docs",
        "health": "/api/system/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
