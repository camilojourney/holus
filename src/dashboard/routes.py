from fastapi import APIRouter
from pathlib import Path
import subprocess
import re

router = APIRouter(prefix="/api")

HOLUS_ROOT = Path("/Users/mini/.openclaw/workspace/github/holus")
MEMORY_DIR = Path("/Users/mini/.openclaw/workspace/memory")

@router.get("/agents")
async def get_agents():
    """List running cron jobs from openclaw."""
    try:
        result = subprocess.run(["openclaw", "cron", "list"], capture_output=True, text=True)
        return {"status": "ok", "output": result.stdout}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.get("/logs")
async def get_logs():
    """Get recent build logs from memory/."""
    logs = []
    if MEMORY_DIR.exists():
        for f in sorted(MEMORY_DIR.glob("*.md"), reverse=True)[:5]:
            logs.append({"name": f.name, "size": f.stat().st_size})
    return {"logs": logs}

@router.get("/backlog")
async def get_backlog():
    """Parse BACKLOG.md and return tasks."""
    backlog_path = HOLUS_ROOT / "BACKLOG.md"
    if not backlog_path.exists():
        return {"tasks": []}
    
    content = backlog_path.read_text()
    tasks = []
    # Simple table row parsing
    for line in content.split("\n"):
        if line.startswith("|") and "Task" not in line and "---" not in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 4:
                tasks.append({
                    "task": parts[0],
                    "product": parts[1],
                    "est": parts[2],
                    "status": parts[3]
                })
    return {"tasks": tasks}
