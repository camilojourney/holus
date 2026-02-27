"""Holus CLI entrypoint.

Usage::

    python -m holus run marketing --once
    python -m holus status
    python -m holus health
    python -m holus kill --scope marketing-agent --reason "testing"
    python -m holus unkill --scope marketing-agent
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import structlog

from holus.core.run_lock import acquire_run_lock

logger = structlog.get_logger()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="holus",
        description="Holus AI Marketing Agent",
    )
    subparsers = parser.add_subparsers(dest="command")

    # -- run ------------------------------------------------------------------
    run_parser = subparsers.add_parser("run", help="Run an agent")
    run_parser.add_argument(
        "agent",
        choices=["marketing", "manager", "all"],
        help="Which agent to run",
    )
    run_parser.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle and exit",
    )

    # -- status ---------------------------------------------------------------
    subparsers.add_parser("status", help="Show system status")

    # -- health ---------------------------------------------------------------
    subparsers.add_parser("health", help="Run health check")

    # -- kill -----------------------------------------------------------------
    kill_parser = subparsers.add_parser("kill", help="Activate kill switch")
    kill_parser.add_argument("--scope", required=True, help="Kill switch scope")
    kill_parser.add_argument("--reason", required=True, help="Reason for kill")

    # -- unkill ---------------------------------------------------------------
    unkill_parser = subparsers.add_parser("unkill", help="Deactivate kill switch")
    unkill_parser.add_argument("--scope", required=True, help="Kill switch scope")

    args = parser.parse_args()

    if args.command == "run":
        _run_agent(args.agent, once=args.once)
    elif args.command == "status":
        _show_status()
    elif args.command == "health":
        _run_health_check()
    elif args.command == "kill":
        _activate_kill(args.scope, args.reason)
    elif args.command == "unkill":
        _deactivate_kill(args.scope)
    else:
        parser.print_help()
        sys.exit(1)


# -- Commands -----------------------------------------------------------------


def _run_agent(agent_name: str, *, once: bool = False) -> None:
    """Run an agent with run-lock protection."""
    with acquire_run_lock(f"holus-{agent_name}"):
        logger.info("Starting agent", agent=agent_name, once=once)
        asyncio.run(_start_agent(agent_name, once=once))


async def _start_agent(agent_name: str, *, once: bool = False) -> None:
    """Import and run the specified agent."""
    if agent_name == "marketing":
        from holus.agents.marketing.agent import MarketingAgent

        agent = MarketingAgent()
        await agent.run()
        agent.close()
    elif agent_name == "manager":
        logger.info("Manager agent not yet implemented")
    elif agent_name == "all":
        logger.info("Running all agents not yet implemented")


def _show_status() -> None:
    """Show system status: kill switch state, recent trajectory, health."""
    from holus.core.health import HealthCheck

    health = HealthCheck()
    results = health.run()

    print(json.dumps(results, indent=2))

    overall = results.get("overall", "unknown")
    if overall != "healthy":
        sys.exit(1)


def _run_health_check() -> None:
    """Run health check and output JSON."""
    from holus.core.health import HealthCheck

    health = HealthCheck()
    results = health.run()

    print(json.dumps(results, indent=2))

    overall = results.get("overall", "unknown")
    if overall != "healthy":
        sys.exit(1)


def _activate_kill(scope: str, reason: str) -> None:
    """Activate kill switch for the given scope."""
    try:
        import redis as redis_lib

        from holus.core.config import HolusConfig
        from holus.core.kill_switch import KillSwitch

        config = HolusConfig.load()
        r = redis_lib.Redis.from_url(config.redis_url, decode_responses=True)
        ks = KillSwitch(r)
        ks.activate(scope=scope, reason=reason)
        print(f"Kill switch activated: scope={scope}, reason={reason}")
    except Exception as e:
        print(f"Failed to activate kill switch: {e}", file=sys.stderr)
        sys.exit(1)


def _deactivate_kill(scope: str) -> None:
    """Deactivate kill switch for the given scope."""
    try:
        import redis as redis_lib

        from holus.core.config import HolusConfig
        from holus.core.kill_switch import KillSwitch

        config = HolusConfig.load()
        r = redis_lib.Redis.from_url(config.redis_url, decode_responses=True)
        ks = KillSwitch(r)
        ks.deactivate(scope=scope)
        print(f"Kill switch deactivated: scope={scope}")
    except Exception as e:
        print(f"Failed to deactivate kill switch: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
