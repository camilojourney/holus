from .base import BaseAgent
import re

class ManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__("ManagerAgent")
    
    async def spawn_agent(self, label: str, model: str, task_prompt: str) -> str:
        """Spawn a sub-agent via OpenClaw. Returns session key."""
        # Escape the prompt for shell
        escaped_prompt = task_prompt.replace("'", "'\\''")
        cmd = f"openclaw sessions spawn --model {model} --label '{label}' --prompt '{escaped_prompt}'"
        returncode, stdout, stderr = await self.run_command(cmd)
        self.log(f"Spawned agent: {label}, model={model}, rc={returncode}")
        # Parse session key from output
        return stdout.strip()
    
    async def check_status(self, session_key: str) -> dict:
        """Check sub-agent session status."""
        cmd = f"openclaw sessions status {session_key}"
        returncode, stdout, stderr = await self.run_command(cmd)
        return {"status": "completed" if returncode == 0 else "unknown", "output": stdout}
    
    async def update_backlog(self, task_name: str, new_status: str) -> None:
        """Update BACKLOG.md — find task row, change status column."""
        backlog = self.backlog_path.read_text()
        # Find the task row and update status
        pattern = rf"(\| {re.escape(task_name)} \|.*?\|.*?\|)\s*\w+\s*\|"
        replacement = rf"\1 {new_status} |"
        updated = re.sub(pattern, replacement, backlog)
        self.backlog_path.write_text(updated)
        self.log(f"Updated backlog: {task_name} -> {new_status}")
    
    async def health_check(self) -> dict:
        """Run health check on Holus system."""
        checks = {}
        # Check if key files exist
        checks["backlog_exists"] = self.backlog_path.exists()
        checks["strategy_exists"] = (self.holus_root / "STRATEGY.md").exists()
        # Check git status
        rc, stdout, _ = await self.run_command(f"cd {self.holus_root} && git status --short")
        checks["git_clean"] = len(stdout.strip()) == 0
        self.log(f"Health check: {checks}")
        return checks
