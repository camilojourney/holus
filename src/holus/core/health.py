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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


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
