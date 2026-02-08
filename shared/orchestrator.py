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
    - Discover and register agents
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

    async def run_agent(self, agent_name: str) -> dict:
        """Manually trigger a specific agent."""
        if agent_name not in self.agents:
            return {"error": f"Agent '{agent_name}' not found"}
        return await self.agents[agent_name].scheduled_run()

    def get_status(self) -> dict:
        """Get status of all agents."""
        return {
            "agents": {
                name: agent.get_status()
                for name, agent in self.agents.items()
            },
            "scheduler_running": self.scheduler.running,
            "total_agents": len(self.agents),
        }

    async def start(self):
        """Start the orchestrator and all scheduled agents."""
        logger.info("=" * 60)
        logger.info("🔮 HOLUS — Starting Agent Workforce")
        logger.info("=" * 60)

        # Discover and register agents
        self.discover_agents()

        # Start scheduler
        self.scheduler.start()

        # Send startup notification
        agent_list = ", ".join(self.agents.keys()) or "none"
        await self.notifier.notify(
            f"🔮 *Holus started!*\n\n"
            f"Active agents: {agent_list}\n"
            f"Total: {len(self.agents)}"
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
        await self.notifier.notify("🛑 *Holus shutting down*")
        logger.info("Goodbye!")

        # Cancel all tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
