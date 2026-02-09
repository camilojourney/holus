"""
Holus — Personal AI Agent Workforce
Main entry point.

Usage:
    python -m holus.main                    # Start all agents
    python -m holus.main --agent job_hunter  # Run a single agent once
    python -m holus.main --status           # Show agent status
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path

from loguru import logger

# Configure logging
log_dir = os.path.expanduser("~/.holus/logs")
os.makedirs(log_dir, exist_ok=True)
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}")
logger.add(os.path.join(log_dir, "holus.log"), rotation="10 MB", retention="7 days", level="DEBUG")


def main():
    parser = argparse.ArgumentParser(description="Holus — Personal AI Agent Workforce")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument("--agent", help="Run a specific agent once (e.g., 'job_hunter')")
    parser.add_argument("--status", action="store_true", help="Show agent status and exit")
    args = parser.parse_args()

    from core.orchestrator import Orchestrator

    try:
        orchestrator = Orchestrator(config_path=args.config)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    if args.status:
        orchestrator.discover_agents()
        status = orchestrator.get_status()
        print("\n🔮 HOLUS STATUS")
        print("=" * 40)
        for name, info in status["agents"].items():
            enabled = "✅" if info["enabled"] else "❌"
            print(f"  {enabled} {name: <20} | schedule: {info['schedule']: <20} | runs: {info['run_count']}")
        print(f"\nTotal agents: {status['total_agents']}")
        return

    if args.agent:
        # Run a single agent once
        orchestrator.discover_agents()
        result = asyncio.run(orchestrator.run_agent(args.agent))
        print(f"\nResult: {result}")
        return

    # Start the full orchestrator
    asyncio.run(orchestrator.start())


if __name__ == "__main__":
    main()
