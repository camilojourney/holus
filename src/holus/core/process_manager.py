"""Agent process management and supervision.

Each Holus agent runs as an independent OS process.  The ``ProcessManager``
handles lifecycle operations (start/stop/restart) and health monitoring
with exponential backoff on crashes.

This is the supervisor pattern:  a crash in the trading agent does NOT
affect the content agent.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import IO

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class AgentStatus(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    CRASHED = "crashed"
    RATE_LIMITED = "rate_limited"
    RESTARTING = "restarting"


@dataclass
class AgentProcess:
    """Runtime state for a managed agent process."""

    name: str
    entrypoint: str                     # e.g. "holus.agents.trading.agent"
    pid: int | None = None
    status: AgentStatus = AgentStatus.STOPPED
    restart_count: int = 0
    max_restarts: int = 3
    cooldown_seconds: int = 60          # Base cooldown; doubles per restart
    last_started: float | None = None
    last_stopped: float | None = None
    process: subprocess.Popen | None = field(default=None, repr=False)

    @property
    def is_alive(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None


# ---------------------------------------------------------------------------
# Process Manager
# ---------------------------------------------------------------------------

class ProcessManager:
    """Supervisor for Holus agent processes.

    Usage::

        pm = ProcessManager(log_dir=Path("logs"))
        pm.start_agent("trading-agent", "holus.agents.trading.agent")
        pm.start_agent("content-agent", "holus.agents.content.agent")

        # Monitor loop
        pm.check_health()

        # Graceful shutdown
        pm.shutdown_all()
    """

    def __init__(self, log_dir: Path = Path("logs")) -> None:
        self._agents: dict[str, AgentProcess] = {}
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)

    # -- Lifecycle -----------------------------------------------------------

    def start_agent(self, name: str, entrypoint: str) -> AgentProcess:
        """Launch an agent as a subprocess.

        The subprocess inherits the current environment plus
        ``HOLUS_AGENT_NAME`` set to *name*.
        """
        if name in self._agents and self._agents[name].is_alive:
            logger.warning("Agent %s is already running (pid %s)", name, self._agents[name].pid)
            return self._agents[name]

        stdout_path = self._log_dir / f"{name}.stdout.log"
        stderr_path = self._log_dir / f"{name}.stderr.log"

        stdout_fh: IO = open(stdout_path, "a")
        stderr_fh: IO = open(stderr_path, "a")

        env = {**os.environ, "HOLUS_AGENT_NAME": name}

        proc = subprocess.Popen(
            ["python", "-m", entrypoint],
            env=env,
            stdout=stdout_fh,
            stderr=stderr_fh,
        )

        agent = AgentProcess(
            name=name,
            entrypoint=entrypoint,
            pid=proc.pid,
            status=AgentStatus.RUNNING,
            process=proc,
            last_started=time.time(),
        )
        self._agents[name] = agent
        logger.info("Started agent %s (pid %d)", name, proc.pid)
        return agent

    def stop_agent(self, name: str, timeout: float = 10.0) -> None:
        """Gracefully stop an agent, falling back to SIGKILL."""
        agent = self._agents.get(name)
        if agent is None or agent.process is None:
            return

        if not agent.is_alive:
            agent.status = AgentStatus.STOPPED
            return

        logger.info("Stopping agent %s (pid %s)...", name, agent.pid)

        # Graceful SIGTERM
        agent.process.send_signal(signal.SIGTERM)
        try:
            agent.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning("Agent %s did not stop gracefully; sending SIGKILL", name)
            agent.process.kill()
            agent.process.wait(timeout=5)

        agent.status = AgentStatus.STOPPED
        agent.last_stopped = time.time()
        logger.info("Agent %s stopped", name)

    def restart_agent(self, name: str) -> AgentProcess | None:
        """Stop then start an agent."""
        agent = self._agents.get(name)
        if agent is None:
            logger.error("Cannot restart unknown agent: %s", name)
            return None

        self.stop_agent(name)
        return self.start_agent(name, agent.entrypoint)

    def shutdown_all(self, timeout: float = 15.0) -> None:
        """Gracefully shut down every managed agent."""
        logger.info("Shutting down all agents...")
        for name in list(self._agents):
            self.stop_agent(name, timeout=timeout)
        logger.info("All agents stopped.")

    # -- Health check --------------------------------------------------------

    def check_health(self) -> dict[str, AgentStatus]:
        """Check every agent's health and handle crashes.

        Returns a mapping of agent names to their current status.
        """
        statuses: dict[str, AgentStatus] = {}

        for name, agent in self._agents.items():
            if agent.status == AgentStatus.STOPPED:
                statuses[name] = AgentStatus.STOPPED
                continue

            if not agent.is_alive:
                exit_code = agent.process.returncode if agent.process else -1
                logger.error(
                    "Agent %s has exited unexpectedly (exit code %s)",
                    name,
                    exit_code,
                )
                self._handle_crash(agent)

            statuses[name] = agent.status

        return statuses

    # -- Crash handling with exponential backoff -----------------------------

    def _handle_crash(self, agent: AgentProcess) -> None:
        """Restart a crashed agent with exponential backoff."""
        agent.restart_count += 1
        agent.last_stopped = time.time()

        if agent.restart_count > agent.max_restarts:
            agent.status = AgentStatus.CRASHED
            logger.critical(
                "Agent %s has crashed %d times (limit %d). NOT restarting. "
                "Manual intervention required.",
                agent.name,
                agent.restart_count,
                agent.max_restarts,
            )
            return

        cooldown = agent.cooldown_seconds * (2 ** (agent.restart_count - 1))
        logger.warning(
            "Agent %s crashed (attempt %d/%d). Restarting in %ds...",
            agent.name,
            agent.restart_count,
            agent.max_restarts,
            cooldown,
        )
        agent.status = AgentStatus.RESTARTING

        # Schedule restart after cooldown (non-blocking)
        import threading

        def _delayed_restart() -> None:
            time.sleep(cooldown)
            if agent.status == AgentStatus.RESTARTING:
                self.start_agent(agent.name, agent.entrypoint)

        t = threading.Thread(target=_delayed_restart, daemon=True)
        t.start()

    # -- Introspection -------------------------------------------------------

    def list_agents(self) -> list[AgentProcess]:
        """Return all registered agents."""
        return list(self._agents.values())

    def get_agent(self, name: str) -> AgentProcess | None:
        return self._agents.get(name)

    def reset_crash_counter(self, name: str) -> None:
        """Manually reset the crash counter after investigation."""
        agent = self._agents.get(name)
        if agent:
            agent.restart_count = 0
            logger.info("Reset crash counter for %s", name)
