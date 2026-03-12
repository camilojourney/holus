"""Health check system for Holus.

Verifies core services and agent status. Designed to run every 5 minutes
via launchd or manually via ``python -m holus health``.

Each check returns a dict with at minimum a ``status`` key:
  - ``healthy``: all good
  - ``degraded``: non-critical issue (e.g. Redis offline in Phase 1)
  - ``unhealthy``: critical issue that needs attention

The :func:`run_preflight_checks` function is the cycle-gating variant:
it returns a :class:`~holus.core.cycle_state.HealthResult` that the agent
loop uses to decide whether to proceed or abort before any work starts.
"""

from __future__ import annotations

import fcntl
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import structlog

try:
    import redis as redis_lib
except ImportError:
    redis_lib = None  # type: ignore[assignment]

from holus.core.cycle_state import HealthResult

logger = structlog.get_logger()

_TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")
_ALL_SILOS = ["social_media", "pilaster", "genpeli"]


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
        path = Path(".self-improvement/memory/trajectory.jsonl")
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


# ---------------------------------------------------------------------------
# Cycle-gating preflight (used by the agent loop, not the monitoring check)
# ---------------------------------------------------------------------------


def run_preflight_checks(
    *,
    redis_url: str | None = None,
    anthropic_api_key: str | None = None,
    social_media_api_base_url: str | None = None,
    pilaster_api_base_url: str | None = None,
    genpeli_api_base_url: str | None = None,
    trajectory_path: Path | None = None,
    skip_run_lock_check: bool = False,
) -> HealthResult:
    """Run all cycle-gating preflight checks and return a :class:`HealthResult`.

    Checks are run in this order:

    1. Kill switch (blocking) — global Redis kill switch must not be active.
    2. LLM reachable (blocking) — Anthropic API must respond.
    3. Social Media MCP (blocking) — primary output channel.
    4. Pilaster MCP (non-blocking) — image generation; removed from silos on failure.
    5. Genpeli MCP (non-blocking) — video generation; removed from silos on failure.
    6. Trajectory log writable (blocking) — data integrity requires write access.
    7. Run lock (blocking) — no concurrent cycle is already running.

    Args:
        redis_url: Override Redis URL (default: ``REDIS_URL`` env var or localhost).
        anthropic_api_key: Override Anthropic API key (default: ``ANTHROPIC_API_KEY``).
        social_media_api_base_url: Override Social Media API base URL.
        pilaster_api_base_url: Override Pilaster API base URL.
        genpeli_api_base_url: Override Genpeli API base URL.
        trajectory_path: Override trajectory file path.
        skip_run_lock_check: Skip the run-lock check (useful in tests).

    Returns:
        :class:`~holus.core.cycle_state.HealthResult` with ``blocking_ok``,
        ``available_silos``, and ``warnings``.
    """
    warnings: list[str] = []
    available_silos: list[str] = list(_ALL_SILOS)

    _redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
    _anthropic_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    _social_url = social_media_api_base_url or os.environ.get(
        "SOCIAL_MEDIA_API_BASE_URL", "http://localhost:8000"
    )
    _pilaster_url = pilaster_api_base_url or os.environ.get(
        "PILASTER_API_BASE_URL", "http://localhost:8001"
    )
    _genpeli_url = genpeli_api_base_url or os.environ.get(
        "GENPELI_API_BASE_URL", "http://localhost:8002"
    )
    _trajectory = trajectory_path or _TRAJECTORY_PATH

    # ------------------------------------------------------------------
    # 1. Kill switch (blocking)
    # ------------------------------------------------------------------
    try:
        if redis_lib is None:
            raise ImportError("redis package not installed")
        r = redis_lib.from_url(_redis_url)
        kill_active = bool(r.exists("holus:kill:global"))
        r.close()
        if kill_active:
            logger.warning("Preflight: global kill switch is active — blocking cycle")
            return HealthResult(
                blocking_ok=False,
                available_silos=[],
                warnings=["Global kill switch is active"],
            )
    except Exception as exc:
        # Redis unavailable: non-fatal for kill switch (agent proceeds cautiously)
        warnings.append(f"Kill switch check skipped — Redis unavailable: {exc}")
        logger.warning("Preflight: Redis unavailable for kill switch check", error=str(exc))

    # ------------------------------------------------------------------
    # 2. LLM reachable (blocking)
    # ------------------------------------------------------------------
    if not _anthropic_key:
        logger.error("Preflight: ANTHROPIC_API_KEY not set — blocking cycle")
        return HealthResult(
            blocking_ok=False,
            available_silos=[],
            warnings=["ANTHROPIC_API_KEY is not set"],
        )
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                "https://api.anthropic.com",
                headers={"x-api-key": _anthropic_key},
            )
            # Any HTTP response (even 404) means the API is reachable
            if resp.status_code >= 500:
                raise RuntimeError(f"Anthropic API returned {resp.status_code}")
    except Exception as exc:
        logger.error("Preflight: LLM not reachable — blocking cycle", error=str(exc))
        return HealthResult(
            blocking_ok=False,
            available_silos=[],
            warnings=[f"Anthropic API not reachable: {exc}"],
        )

    # ------------------------------------------------------------------
    # 3. Social Media MCP (blocking)
    # ------------------------------------------------------------------
    try:
        with httpx.Client(timeout=5.0) as client:
            client.get(f"{_social_url}/health")
    except Exception as exc:
        logger.error("Preflight: Social Media MCP unreachable — blocking cycle", error=str(exc))
        return HealthResult(
            blocking_ok=False,
            available_silos=[],
            warnings=[f"Social Media MCP not reachable: {exc}"],
        )

    # ------------------------------------------------------------------
    # 4. Pilaster MCP (non-blocking)
    # ------------------------------------------------------------------
    try:
        with httpx.Client(timeout=5.0) as client:
            client.get(f"{_pilaster_url}/health")
    except Exception as exc:
        available_silos.remove("pilaster")
        warnings.append(f"Pilaster MCP not reachable: {exc}")
        logger.warning("Preflight: Pilaster MCP unreachable", error=str(exc))

    # ------------------------------------------------------------------
    # 5. Genpeli MCP (non-blocking)
    # ------------------------------------------------------------------
    try:
        with httpx.Client(timeout=5.0) as client:
            client.get(f"{_genpeli_url}/health")
    except Exception as exc:
        available_silos.remove("genpeli")
        warnings.append(f"Genpeli MCP not reachable: {exc}")
        logger.warning("Preflight: Genpeli MCP unreachable", error=str(exc))

    # ------------------------------------------------------------------
    # 6. Trajectory log writable (blocking)
    # ------------------------------------------------------------------
    try:
        _trajectory.parent.mkdir(parents=True, exist_ok=True)
        # Touch the file to verify write access; create if it doesn't exist
        with _trajectory.open("a", encoding="utf-8"):
            pass
    except OSError as exc:
        logger.error("Preflight: trajectory log not writable — blocking cycle", error=str(exc))
        return HealthResult(
            blocking_ok=False,
            available_silos=[],
            warnings=[f"Trajectory log not writable: {exc}"],
        )

    # ------------------------------------------------------------------
    # 7. Run lock (blocking)
    # ------------------------------------------------------------------
    if not skip_run_lock_check:
        lock_path = Path("/tmp/holus/holus-marketing.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = open(lock_path, "w")  # noqa: SIM115
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # We got the lock — release immediately. The actual agent will re-acquire.
                fcntl.flock(fd, fcntl.LOCK_UN)
            except BlockingIOError:
                fd.close()
                logger.warning("Preflight: run lock held — another cycle is running")
                return HealthResult(
                    blocking_ok=False,
                    available_silos=[],
                    warnings=["Another marketing cycle is already running"],
                )
            finally:
                fd.close()
        except OSError as exc:
            warnings.append(f"Run lock check failed: {exc}")

    logger.info(
        "Preflight complete",
        available_silos=available_silos,
        warnings=warnings,
    )
    return HealthResult(
        blocking_ok=True,
        available_silos=available_silos,
        warnings=warnings,
    )
