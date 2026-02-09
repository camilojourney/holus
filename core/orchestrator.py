"""
Orchestrator — The central hub of Holus.
Manages agent lifecycle, scheduling, and inter-agent communication.
This is the "brain" that AI Jason calls the "workforce manager."
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from core.base_agent import BaseAgent
from core.llm import LLMProvider
from core.memory import MemoryStore
from core.notifier import Notifier


def parse_schedule(schedule_str: str) -> Optional[IntervalTrigger | CronTrigger]:
    """Parse human-readable schedule strings into APScheduler triggers."""
    s = schedule_str.lower().strip()

    if s == "manual":
        return None

    # "every X minutes/hours"
    if s.startswith("every "):
        parts = s.replace("every ", "").strip().split()
        if len(parts) == 2:
            value, unit = int(parts[0]), parts[1]
            if "minute" in unit:
                return IntervalTrigger(minutes=value)
            elif "hour" in unit:
                return IntervalTrigger(hours=value)
            elif "day" in unit:
                return IntervalTrigger(days=value)

    # "daily at Xam/pm"
    if s.startswith("daily at "):
        time_str = s.replace("daily at ", "").strip()
        hour = int(time_str.replace("am", "").replace("pm", ""))
        if "pm" in time_str and hour != 12:
            hour += 12
        return CronTrigger(hour=hour, minute=0)

    # "3x daily" — roughly every 8 hours
    if "3x daily" in s:
        return IntervalTrigger(hours=8)

    logger.warning(f"Could not parse schedule '{schedule_str}', defaulting to every 6 hours")
    return IntervalTrigger(hours=6)


class Orchestrator:
    """
    Central orchestrator for all Holus agents.
    
    Responsibilities:
    - Load config and initialize shared resources
    - Discover and register agents and domain orchestrators
    - Schedule agent runs
    - Handle graceful shutdown
    - Provide status/health endpoints
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

        # Shared resources
        self.llm_provider = LLMProvider(self.config["llm"])
        self.memory = MemoryStore(
            persist_dir=self.config.get("memory", {}).get(
                "persist_directory", "~/.holus/memory"
            )
        )
        self.notifier = Notifier(self.config.get("notifications", {}))

        # Agent registry
        self.agents: dict[str, BaseAgent] = {}
        # Domain orchestrator registry (content-strategy, job-tracker, trading)
        self.domain_orchestrators: dict[str, object] = {}
        self._domain_tasks: list[asyncio.Task] = []
        self.scheduler = AsyncIOScheduler()

        logger.info("Holus Orchestrator initialized")

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        config_path = Path(self.config_path)
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            logger.info("Run: cp config/config.example.yaml config/config.yaml")
            sys.exit(1)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        logger.info(f"Config loaded from {config_path}")
        return config

    def register_agent(self, agent_class: type[BaseAgent]):
        """Register an agent class. The orchestrator will instantiate and schedule it."""
        agent_config = self.config.get("agents", {}).get(agent_class.name, {})

        if not agent_config.get("enabled", True):
            logger.info(f"Agent '{agent_class.name}' is disabled in config, skipping")
            return

        agent = agent_class(
            llm_provider=self.llm_provider,
            memory=self.memory,
            notifier=self.notifier,
            config=agent_config,
        )

        self.agents[agent.name] = agent

        # Schedule the agent
        schedule = agent_config.get("schedule", agent.schedule)
        trigger = parse_schedule(schedule)
        if trigger:
            self.scheduler.add_job(
                agent.scheduled_run,
                trigger=trigger,
                id=f"agent_{agent.name}",
                name=f"Agent: {agent.name}",
                replace_existing=True,
            )
            logger.info(f"Agent '{agent.name}' scheduled: {schedule}")
        else:
            logger.info(f"Agent '{agent.name}' registered (manual only)")

    def discover_agents(self):
        """Auto-discover and register all available agents."""
        # Import agent classes
        from agents.job_hunter.agent import JobHunterAgent
        from agents.trading_monitor.agent import TradingMonitorAgent
        from agents.social_media.agent import SocialMediaAgent
        from agents.research_scout.agent import ResearchScoutAgent
        from agents.inbox_manager.agent import InboxManagerAgent

        agent_classes = [
            JobHunterAgent,
            TradingMonitorAgent,
            SocialMediaAgent,
            ResearchScoutAgent,
            InboxManagerAgent,
        ]

        for agent_class in agent_classes:
            try:
                self.register_agent(agent_class)
            except Exception as e:
                logger.error(f"Failed to register agent '{agent_class.name}': {e}")

    def discover_domain_orchestrators(self):
        """Auto-discover and register domain orchestrators.

        Domain orchestrators manage cross-cutting concerns within a domain
        (e.g., content-strategy automation routing). They run as long-lived
        asyncio tasks alongside the scheduler.
        """
        import importlib.util

        project_root = Path(__file__).parent.parent

        domain_configs = {
            "content-strategy": {
                "file": project_root / "agents" / "content-strategy" / "orchestrator.py",
                "class": "ContentOrchestrator",
            },
            "job-tracker": {
                "file": project_root / "agents" / "job-tracker" / "orchestrator.py",
                "class": "JobTrackerOrchestrator",
            },
            "trading": {
                "file": project_root / "agents" / "trading" / "orchestrator.py",
                "class": "TradingOrchestrator",
            },
        }

        for domain_name, info in domain_configs.items():
            domain_cfg = self.config.get("domains", {}).get(domain_name, {})
            if not domain_cfg.get("enabled", False):
                logger.debug(f"Domain '{domain_name}' not enabled, skipping")
                continue

            filepath = info["file"]
            if not filepath.exists():
                logger.warning(
                    f"Domain orchestrator file not found: {filepath}"
                )
                continue

            try:
                mod_name = f"agents_domain_{domain_name.replace('-', '_')}"
                spec = importlib.util.spec_from_file_location(mod_name, filepath)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)

                cls = getattr(mod, info["class"])
                orchestrator = cls()
                self.domain_orchestrators[domain_name] = orchestrator
                logger.info(f"Domain orchestrator '{domain_name}' registered")

                # Schedule domain-specific jobs
                self._schedule_domain_jobs(domain_name, orchestrator, domain_cfg)
            except Exception as e:
                logger.error(
                    f"Failed to register domain '{domain_name}': {e}"
                )

    def _schedule_domain_jobs(self, name: str, orchestrator: object, cfg: dict):
        """Schedule recurring jobs defined by a domain orchestrator."""
        schedule_str = cfg.get("schedule")
        if not schedule_str:
            return

        # Content-strategy has a daily routine
        if name == "content-strategy" and hasattr(orchestrator, "run_daily_routine"):
            trigger = parse_schedule(schedule_str)
            if trigger:
                self.scheduler.add_job(
                    orchestrator.run_daily_routine,
                    trigger=trigger,
                    id=f"domain_{name}_daily",
                    name=f"Domain: {name} daily routine",
                    replace_existing=True,
                )
                logger.info(
                    f"Domain '{name}' daily routine scheduled: {schedule_str}"
                )

    async def run_agent(self, agent_name: str) -> dict:
        """Manually trigger a specific agent."""
        if agent_name not in self.agents:
            return {"error": f"Agent '{agent_name}' not found"}
        return await self.agents[agent_name].scheduled_run()

    def get_status(self) -> dict:
        """Get status of all agents and domain orchestrators."""
        domain_status = {}
        for name, orch in self.domain_orchestrators.items():
            domain_status[name] = {
                "domain": name,
                "agents": len(getattr(orch, "agents", {})),
                "status": "running",
            }

        return {
            "agents": {
                name: agent.get_status()
                for name, agent in self.agents.items()
            },
            "domains": domain_status,
            "scheduler_running": self.scheduler.running,
            "total_agents": len(self.agents),
            "total_domains": len(self.domain_orchestrators),
        }

    def _start_dashboard(self):
        """Start the FastAPI dashboard in a background thread (SPEC-008)."""
        dash_cfg = self.config.get("dashboard", {})
        if not dash_cfg.get("enabled", True):
            logger.info("Dashboard disabled in config")
            return

        host = dash_cfg.get("host", "0.0.0.0")
        port = dash_cfg.get("port", 8080)

        try:
            import uvicorn
            from dashboard.app import create_app

            app = create_app(self)

            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="warning",
            )
            server = uvicorn.Server(config)

            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            logger.info(f"Dashboard running at http://{host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")

    async def start(self):
        """Start the orchestrator and all scheduled agents."""
        logger.info("=" * 60)
        logger.info("🔮 HOLUS — Starting Agent Workforce")
        logger.info("=" * 60)

        # Discover and register agents
        self.discover_agents()

        # Discover and register domain orchestrators
        self.discover_domain_orchestrators()

        # Start scheduler
        self.scheduler.start()

        # Launch domain orchestrators as background tasks
        for name, orch in self.domain_orchestrators.items():
            if hasattr(orch, "run") and asyncio.iscoroutinefunction(orch.run):
                task = asyncio.create_task(orch.run())
                task.set_name(f"domain_{name}")
                self._domain_tasks.append(task)
                logger.info(f"Domain '{name}' running as background task")

        # Start dashboard (SPEC-008)
        self._start_dashboard()

        # Send startup notification
        agent_list = ", ".join(self.agents.keys()) or "none"
        domain_list = ", ".join(self.domain_orchestrators.keys()) or "none"
        await self.notifier.notify(
            f"🔮 *Holus started!*\n\n"
            f"Active agents: {agent_list}\n"
            f"Active domains: {domain_list}\n"
            f"Total: {len(self.agents)} agents, {len(self.domain_orchestrators)} domains"
        )

        # Setup graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        # Keep running
        logger.info(f"Holus running with {len(self.agents)} agents. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("🛑 Holus shutting down...")
        self.scheduler.shutdown(wait=False)

        # Cancel domain orchestrator tasks
        for task in self._domain_tasks:
            task.cancel()
        if self._domain_tasks:
            await asyncio.gather(*self._domain_tasks, return_exceptions=True)

        await self.notifier.notify("🛑 *Holus shutting down*")
        logger.info("Goodbye!")

        # Cancel all tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
