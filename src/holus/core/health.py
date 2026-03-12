"""Health check system for Holus.

Verifies core services and agent status. Designed to run every 5 minutes
via launchd or manually via ``python -m holus health``.

Each check returns a dict with at minimum a ``status`` key:
  - ``healthy``: all good
  - ``degraded``: non-critical issue (e.g. Redis offline in Phase 1)
  - ``unhealthy``: critical issue that needs attention
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog

from holus.core.config import HolusConfig
from holus.core.kill_switch import KillSwitch
from holus.core.run_lock import is_run_lock_available
from holus.integrations.claude_api.client import CachedPrompt, HolusClaudeClient

logger = structlog.get_logger()

_TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")
_PILASTER_BASE_URL = "http://localhost:3000"
_GENPELI_BASE_URL = "http://localhost:8100"


@dataclass(slots=True)
class HealthResult:
    """Preflight result for a single marketing cycle."""

    blocking_ok: bool
    available_silos: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocking_reason: str | None = None
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocking_ok": self.blocking_ok,
            "available_silos": self.available_silos,
            "warnings": self.warnings,
            "blocking_reason": self.blocking_reason,
            "checks": self.checks,
        }


class HealthCheck:
    """Run health checks and aggregate results."""

    def run(self) -> dict[str, Any]:
        """Run all health checks and return a summary."""
        results: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": {},
            "overall": "healthy",
        }

        results["checks"]["kill_switch"] = self.check_kill_switch()
        results["checks"]["trajectory"] = self.check_trajectory()
        results["checks"]["knowledge"] = self.check_knowledge()
        results["checks"]["content_queue"] = self.check_content_queue()
        results["checks"]["logs"] = self.check_logs()

        # Overall: unhealthy if any check is unhealthy
        if any(c.get("status") == "unhealthy" for c in results["checks"].values()):
            results["overall"] = "unhealthy"
        elif any(c.get("status") == "degraded" for c in results["checks"].values()):
            results["overall"] = "degraded"

        logger.info(
            "Health check complete",
            overall=results["overall"],
            checks={k: v["status"] for k, v in results["checks"].items()},
        )
        return results

    def check_kill_switch(self) -> dict[str, Any]:
        """Check Redis connectivity and kill switch state."""
        try:
            import redis

            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
            r = redis.from_url(redis_url)
            r.ping()
            global_kill = r.exists("holus:kill:global")
            r.close()
            return {
                "status": "healthy",
                "redis": "connected",
                "global_kill_active": bool(global_kill),
            }
        except Exception as e:
            return {
                "status": "degraded",
                "error": str(e),
                "note": "Redis not required for Phase 1",
            }

    def check_trajectory(self) -> dict[str, Any]:
        """Check trajectory file exists and is writable."""
        path = _TRAJECTORY_PATH
        return {
            "status": "healthy",
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }

    def check_knowledge(self) -> dict[str, Any]:
        """Check knowledge base has files."""
        knowledge_dir = Path(".self-improvement/knowledge/current")
        files = list(knowledge_dir.glob("*.md")) if knowledge_dir.exists() else []
        return {
            "status": "healthy" if files else "degraded",
            "files_count": len(files),
            "files": [f.name for f in files],
        }

    def check_content_queue(self) -> dict[str, Any]:
        """Check content queue directory."""
        queue_dir = Path("data/content-queue")
        if not queue_dir.exists():
            return {"status": "healthy", "pending": 0, "note": "Queue not created yet"}
        pending = list(queue_dir.glob("*.yaml")) + list(queue_dir.glob("*.json"))
        return {"status": "healthy", "pending": len(pending)}

    def check_logs(self) -> dict[str, Any]:
        """Check logs directory exists."""
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return {"status": "degraded", "note": "logs/ directory missing — run mkdir -p logs"}
        return {"status": "healthy", "directory": str(logs_dir)}


def run_preflight_checks(
    *,
    config: HolusConfig | None = None,
    agent_name: str = "marketing-agent",
    kill_switch: KillSwitch | None = None,
    trajectory_path: Path = _TRAJECTORY_PATH,
    lock_name: str | None = None,
    check_run_lock: bool = True,
    llm_probe: Any | None = None,
    social_media_probe: Any | None = None,
    pilaster_probe: Any | None = None,
    genpeli_probe: Any | None = None,
) -> HealthResult:
    """Run Phase 0 preflight checks in spec-defined order."""
    resolved_config = config or HolusConfig.load(agent_name="marketing")
    silos: list[str] = []
    warnings: list[str] = []
    checks: dict[str, dict[str, Any]] = {}

    def fail(check_name: str, reason: str) -> HealthResult:
        checks[check_name] = {"status": "failed", "reason": reason}
        return HealthResult(
            blocking_ok=False,
            available_silos=silos,
            warnings=warnings,
            blocking_reason=reason,
            checks=checks,
        )

    resolved_kill_switch = kill_switch or _load_kill_switch(resolved_config)

    try:
        if resolved_kill_switch.is_active(agent_name):
            state = (
                resolved_kill_switch.get_state(agent_name)
                or resolved_kill_switch.get_state("marketing")
                or resolved_kill_switch.get_state("global")
            )
            reason = state.reason if state and state.reason else "kill switch active"
            return fail("kill_switch", reason)
        checks["kill_switch"] = {"status": "ok"}
    except Exception as exc:
        return fail("kill_switch", f"Kill switch check failed: {exc}")

    probe_llm = llm_probe or _probe_llm
    try:
        probe_llm(resolved_config)
        checks["llm"] = {"status": "ok"}
    except Exception as exc:
        return fail("llm", f"LLM unreachable: {exc}")

    probe_social = social_media_probe or _probe_social_media
    try:
        probe_social(resolved_config)
        silos.append("social-media")
        checks["social_media"] = {"status": "ok"}
    except Exception as exc:
        return fail("social_media", f"Social media MCP unreachable: {exc}")

    probe_pilaster = pilaster_probe or _probe_pilaster
    try:
        probe_pilaster()
        silos.append("pilaster")
        checks["pilaster"] = {"status": "ok"}
    except Exception as exc:
        warning = f"Pilaster MCP unavailable: {exc}"
        warnings.append(warning)
        checks["pilaster"] = {"status": "warning", "reason": warning}

    probe_genpeli = genpeli_probe or _probe_genpeli
    try:
        probe_genpeli()
        silos.append("genpeli")
        checks["genpeli"] = {"status": "ok"}
    except Exception as exc:
        warning = f"Genpeli MCP unavailable: {exc}"
        warnings.append(warning)
        checks["genpeli"] = {"status": "warning", "reason": warning}

    try:
        _ensure_trajectory_writable(trajectory_path)
        checks["trajectory"] = {"status": "ok", "path": str(trajectory_path)}
    except Exception as exc:
        return fail("trajectory", f"Trajectory log unavailable: {exc}")

    if check_run_lock:
        resolved_lock = lock_name or agent_name
        if not is_run_lock_available(resolved_lock):
            return fail("run_lock", f"Another {resolved_lock} cycle is already running")
        checks["run_lock"] = {"status": "ok", "lock_name": resolved_lock}
    else:
        checks["run_lock"] = {"status": "skipped"}

    return HealthResult(
        blocking_ok=True,
        available_silos=silos,
        warnings=warnings,
        checks=checks,
    )


def _load_kill_switch(config: HolusConfig) -> KillSwitch:
    import redis

    redis_client = redis.Redis.from_url(config.redis_url, decode_responses=True)
    return KillSwitch(redis_client)


def _probe_llm(config: HolusConfig) -> None:
    if not config.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = HolusClaudeClient(api_key=config.anthropic_api_key)
    response = client.call(
        cached_prompt=CachedPrompt(system_prompt="Reply with OK."),
        messages=[{"role": "user", "content": "Ping"}],
        tier="classification",
        max_tokens=8,
        temperature=0.0,
        agent_id="health-check",
    )
    text = " ".join(
        str(getattr(block, "text", "")).strip() for block in getattr(response, "content", [])
    ).strip()
    if not text:
        raise RuntimeError("empty response")


def _probe_social_media(config: HolusConfig) -> None:
    if not config.posting_api_key:
        raise RuntimeError("POSTING_API_KEY not configured")

    with httpx.Client(
        base_url=config.social_media_api_base_url.rstrip("/"),
        headers={"X-API-Key": config.posting_api_key},
        timeout=10.0,
    ) as client:
        response = client.get("/health")
        response.raise_for_status()


def _probe_pilaster() -> None:
    _probe_http_service(os.environ.get("PILASTER_BASE_URL", _PILASTER_BASE_URL))


def _probe_genpeli() -> None:
    _probe_http_service(os.environ.get("GENPELI_BASE_URL", _GENPELI_BASE_URL))


def _probe_http_service(base_url: str) -> None:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(urljoin(base_url.rstrip("/") + "/", "health"))
        response.raise_for_status()


def _ensure_trajectory_writable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8"):
        pass
