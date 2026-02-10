from pathlib import Path
import asyncio
import subprocess
from datetime import datetime

class BaseAgent:
    def __init__(self, name: str, workspace: str = "/Users/mini/.openclaw/workspace"):
        self.name = name
        self.workspace = Path(workspace)
    
    @property
    def holus_root(self) -> Path:
        return self.workspace / "github" / "holus"
    
    @property
    def backlog_path(self) -> Path:
        return self.holus_root / "BACKLOG.md"
    
    async def run_command(self, cmd: str) -> tuple[int, str, str]:
        """Run shell command, return (returncode, stdout, stderr)."""
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(), stderr.decode()
    
    def log(self, msg: str) -> None:
        """Append to daily build log."""
        log_dir = self.workspace / "memory"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"holus-build-{datetime.now().strftime('%Y-%m-%d')}.log"
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] [{self.name}] {msg}\n")
