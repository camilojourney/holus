"""SQLite corpus index for scraped LinkedIn posts.

Indexes all scraped reference posts for fast querying: full-text search,
engagement sorting, filtering by visual type or content type.

Usage::

    db = CorpusDB()
    db.ingest_all()  # Index all creators from reference library
    results = db.top_by_engagement(limit=10)
    results = db.search("ComfyUI workflow", limit=5)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REFERENCE_LIB = Path("data/reference-library")
DB_PATH = REFERENCE_LIB / "_index" / "posts.db"

# Engagement weights -- comments and reposts are worth more than reactions.
_WEIGHT_REACTION = 1
_WEIGHT_COMMENT = 3
_WEIGHT_REPOST = 5

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS posts (
    id           TEXT PRIMARY KEY,   -- urn (unique per post)
    creator      TEXT NOT NULL,
    text         TEXT NOT NULL DEFAULT '',
    reactions    INTEGER NOT NULL DEFAULT 0,
    comments     INTEGER NOT NULL DEFAULT 0,
    reposts      INTEGER NOT NULL DEFAULT 0,
    engagement_total INTEGER NOT NULL DEFAULT 0,
    visual_type  TEXT NOT NULL DEFAULT '',   -- postType: text, image+text, video, ...
    content_type TEXT NOT NULL DEFAULT '',   -- category: Technical Tutorial, ...
    image_urls   TEXT NOT NULL DEFAULT '[]', -- JSON array of image URLs
    hashtags     TEXT NOT NULL DEFAULT '[]', -- JSON array of hashtags
    scraped_at   TEXT NOT NULL DEFAULT ''    -- dateAbsolute
);

CREATE INDEX IF NOT EXISTS idx_engagement ON posts (engagement_total DESC);
CREATE INDEX IF NOT EXISTS idx_creator ON posts (creator);
CREATE INDEX IF NOT EXISTS idx_content_type ON posts (content_type);
CREATE INDEX IF NOT EXISTS idx_visual_type ON posts (visual_type);
"""

_FTS_SQL = """\
CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
    id,
    creator,
    text
);
"""


def _safe_int(value: Any) -> int:
    """Parse a value to int, tolerating stringified numbers and commas."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
    return 0


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row to a plain dict, deserializing JSON fields."""
    d: dict[str, Any] = dict(row)
    for key in ("image_urls", "hashtags"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except json.JSONDecodeError:
                d[key] = []
    return d


class CorpusDB:
    """SQLite-backed corpus store for scraped LinkedIn posts."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        """Create tables and FTS index if they don't exist."""
        cur = self._conn.cursor()
        cur.executescript(_SCHEMA_SQL)
        cur.executescript(_FTS_SQL)
        self._conn.commit()

    def _rebuild_fts(self) -> None:
        """Rebuild the FTS index from the posts table.

        Called after bulk ingestion. Clears and repopulates the FTS table
        from the canonical ``posts`` table.
        """
        self._conn.execute("DELETE FROM posts_fts")
        self._conn.execute(
            "INSERT INTO posts_fts(id, creator, text) "
            "SELECT id, creator, text FROM posts"
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest_creator(self, creator_dir: Path, *, rebuild_fts: bool = True) -> int:
        """Import posts from a single creator's ``posts-raw.json``.

        Args:
            creator_dir: Directory containing ``posts-raw.json``.
            rebuild_fts: Whether to rebuild the FTS index after ingestion.
                Set to ``False`` when calling from :meth:`ingest_all` which
                does a single rebuild at the end.

        Returns the number of posts ingested (new or updated).
        """
        posts_file = creator_dir / "posts-raw.json"
        if not posts_file.exists():
            logger.warning("No posts-raw.json in %s", creator_dir)
            return 0

        raw: list[dict[str, Any]] = json.loads(posts_file.read_text(encoding="utf-8"))
        creator_name = creator_dir.name
        count = 0

        for entry in raw:
            raw_urn = entry.get("urn", "")
            if not raw_urn:
                # Synthesise a stable ID when urn is missing.
                idx = entry.get("index", 0)
                raw_urn = f"synthetic:{idx}"

            # Prefix with creator to guarantee uniqueness across creators.
            # Some scrapers emit generic IDs like "post-5" that collide.
            urn = f"{creator_name}::{raw_urn}"

            reactions = _safe_int(entry.get("reactions", 0))
            comments = _safe_int(entry.get("comments", 0))
            reposts = _safe_int(entry.get("reposts", 0))
            engagement_total = (
                reactions * _WEIGHT_REACTION
                + comments * _WEIGHT_COMMENT
                + reposts * _WEIGHT_REPOST
            )

            self._conn.execute(
                """\
                INSERT OR REPLACE INTO posts
                    (id, creator, text, reactions, comments, reposts,
                     engagement_total, visual_type, content_type,
                     image_urls, hashtags, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    urn,
                    creator_name,
                    entry.get("text", ""),
                    reactions,
                    comments,
                    reposts,
                    engagement_total,
                    entry.get("postType", ""),
                    entry.get("category", ""),
                    json.dumps(entry.get("images", []), ensure_ascii=False),
                    json.dumps(entry.get("hashtags", []), ensure_ascii=False),
                    entry.get("dateAbsolute", ""),
                ),
            )
            count += 1

        self._conn.commit()
        if rebuild_fts:
            self._rebuild_fts()
        logger.info("Ingested %d posts from %s", count, creator_name)
        return count

    def ingest_all(self, reference_lib: Path = REFERENCE_LIB) -> int:
        """Import all creators from the reference library.

        Returns the total number of posts ingested.
        """
        total = 0
        for creator_dir in sorted(reference_lib.iterdir()):
            if not creator_dir.is_dir():
                continue
            if creator_dir.name.startswith("_"):
                continue
            total += self.ingest_creator(creator_dir, rebuild_fts=False)
        self._rebuild_fts()
        logger.info("Total ingested: %d posts", total)
        return total

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Full-text search across post text.

        Returns posts ranked by FTS relevance.
        """
        rows = self._conn.execute(
            """\
            SELECT p.*
            FROM posts_fts AS f
            JOIN posts AS p ON p.id = f.id
            WHERE posts_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def top_by_engagement(
        self,
        visual_type: str | None = None,
        content_type: str | None = None,
        creator: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Top posts sorted by ``engagement_total``.

        Optionally filter by ``visual_type``, ``content_type``, or ``creator``.
        """
        clauses: list[str] = []
        params: list[Any] = []

        if visual_type is not None:
            clauses.append("visual_type = ?")
            params.append(visual_type)
        if content_type is not None:
            clauses.append("content_type = ?")
            params.append(content_type)
        if creator is not None:
            clauses.append("creator = ?")
            params.append(creator)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        params.append(limit)
        rows = self._conn.execute(
            f"SELECT * FROM posts {where} ORDER BY engagement_total DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        """Corpus statistics: total posts, creators, avg engagement, etc."""
        row = self._conn.execute(
            """\
            SELECT
                COUNT(*)                            AS total_posts,
                COUNT(DISTINCT creator)             AS total_creators,
                COALESCE(AVG(engagement_total), 0)  AS avg_engagement,
                COALESCE(MAX(engagement_total), 0)  AS max_engagement,
                COALESCE(MIN(engagement_total), 0)  AS min_engagement
            FROM posts
            """
        ).fetchone()

        assert row is not None
        base: dict[str, Any] = dict(row)

        # Per-content-type breakdown.
        type_rows = self._conn.execute(
            """\
            SELECT content_type, COUNT(*) AS count,
                   COALESCE(AVG(engagement_total), 0) AS avg_engagement
            FROM posts
            GROUP BY content_type
            ORDER BY count DESC
            """
        ).fetchall()
        base["by_content_type"] = [dict(r) for r in type_rows]

        # Per-creator breakdown.
        creator_rows = self._conn.execute(
            """\
            SELECT creator, COUNT(*) AS count,
                   COALESCE(AVG(engagement_total), 0) AS avg_engagement
            FROM posts
            GROUP BY creator
            ORDER BY avg_engagement DESC
            """
        ).fetchall()
        base["by_creator"] = [dict(r) for r in creator_rows]

        return base

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> CorpusDB:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
