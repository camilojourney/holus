"""Trajectory database — SQLite migration path for trajectory.jsonl.

Provides a SQLite-backed trajectory store alongside the JSONL file.
The JSONL remains the source of truth; SQLite enables fast queries
for the Observatory API and learning loop.

Migration path: JSONL → SQLite → PostgreSQL (Sprint 10.3).

Usage::

    db = TrajectoryDB()
    db.migrate_from_jsonl(Path(".self-improvement/memory/trajectory.jsonl"))
    entries = db.query(agent_id="idea-runner", min_score=0.8, limit=50)
    stats = db.aggregate_by_platform(days=30)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(".self-improvement/trajectory.db")


class TrajectoryDB:
    """SQLite-backed trajectory store for fast queries."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS trajectory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                task_type TEXT,
                task_summary TEXT,
                status TEXT,
                duration_seconds REAL DEFAULT 0,
                judge_verdict TEXT,
                judge_score REAL,
                judge_feedback TEXT,
                model_used TEXT,
                cost_usd REAL DEFAULT 0,
                platform TEXT,
                content_type TEXT,
                engagement_signal REAL,
                blended_reward REAL,
                prompt_variant_id TEXT,
                metadata_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_trajectory_agent ON trajectory(agent_id);
            CREATE INDEX IF NOT EXISTS idx_trajectory_platform ON trajectory(platform);
            CREATE INDEX IF NOT EXISTS idx_trajectory_timestamp ON trajectory(timestamp);
            CREATE INDEX IF NOT EXISTS idx_trajectory_score ON trajectory(judge_score);
        """)
        self._conn.commit()

    def insert(self, entry: dict[str, Any]) -> int:
        """Insert a trajectory entry. Returns the row ID."""
        meta = entry.get("metadata", {})
        cursor = self._conn.execute(
            """INSERT INTO trajectory
               (timestamp, agent_id, task_type, task_summary, status,
                duration_seconds, judge_verdict, judge_score, judge_feedback,
                model_used, cost_usd, platform, content_type,
                engagement_signal, blended_reward, prompt_variant_id, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.get("timestamp", datetime.now(UTC).isoformat()),
                entry.get("agent_id", ""),
                entry.get("task_type", ""),
                entry.get("task_summary", ""),
                entry.get("status", ""),
                entry.get("duration_seconds", 0),
                entry.get("judge_verdict"),
                entry.get("judge_score"),
                entry.get("judge_feedback"),
                entry.get("model_used", ""),
                entry.get("cost_usd", 0),
                meta.get("platform", ""),
                meta.get("content_type", entry.get("task_type", "")),
                meta.get("engagement_signal"),
                meta.get("blended_reward"),
                meta.get("prompt_variant_id", ""),
                json.dumps(meta),
            ),
        )
        self._conn.commit()
        return cursor.lastrowid or 0

    def migrate_from_jsonl(self, jsonl_path: Path) -> int:
        """Import all entries from a JSONL file. Returns count imported."""
        if not jsonl_path.exists():
            return 0

        count = 0
        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    entry = json.loads(line.strip())
                    self.insert(entry)
                    count += 1
                except (json.JSONDecodeError, sqlite3.Error):
                    continue

        logger.info("Migrated %d entries from %s to SQLite", count, jsonl_path)
        return count

    def query(
        self,
        *,
        agent_id: str | None = None,
        platform: str | None = None,
        min_score: float | None = None,
        days: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query trajectory entries with filters."""
        conditions = []
        params: list[Any] = []

        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        if min_score is not None:
            conditions.append("judge_score >= ?")
            params.append(min_score)
        if days:
            cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
            conditions.append("timestamp >= ?")
            params.append(cutoff)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM trajectory WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def aggregate_by_platform(self, days: int = 30) -> list[dict[str, Any]]:
        """Aggregate scores by platform."""
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        rows = self._conn.execute(
            """SELECT platform,
                      COUNT(*) as n,
                      AVG(judge_score) as avg_judge,
                      AVG(engagement_signal) as avg_engagement,
                      AVG(blended_reward) as avg_reward
               FROM trajectory
               WHERE timestamp >= ? AND platform != ''
               GROUP BY platform
               ORDER BY avg_reward DESC""",
            (cutoff,),
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        """Total entry count."""
        row = self._conn.execute("SELECT COUNT(*) FROM trajectory").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()
