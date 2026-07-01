import psutil
import platform
import os
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health")
async def health_check():
    """Verify backend health."""
    return {"status": "ok", "app": "Prime API Assistant", "version": "1.0.0"}


@router.get("/stats")
async def get_system_stats():
    """Fetch live system telemetry."""
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(logical=True),
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0
            },
            "memory": {
                "percent": memory.percent,
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "total_gb": round(memory.total / (1024 ** 3), 2)
            },
            "disk": {
                "percent": disk.percent,
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "total_gb": round(disk.total / (1024 ** 3), 2)
            },
            "os": {
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine()
            }
        }
    except Exception as e:
        return {"error": f"Failed to retrieve system statistics: {str(e)}"}


@router.get("/config")
async def get_safe_config():
    """Get non-sensitive active configurations."""
    return {
        "host": settings.HOST,
        "port": settings.PORT,
        "database_type": "sqlite",
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "has_anthropic_key": bool(settings.ANTHROPIC_API_KEY),
        "ollama_host": settings.OLLAMA_HOST,
        "ollama_model": settings.OLLAMA_MODEL,
        "workspace_path": settings.PRIME_WORKSPACE_PATH
    }
