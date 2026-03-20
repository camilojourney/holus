"""Knowledge routes — GET /api/v1/knowledge."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from holus.api.models import (
    KnowledgeFile,
    KnowledgeResponse,
    LessonEntry,
    LessonsResponse,
    MemoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
KNOWLEDGE_DIR = REPO_ROOT / ".self-improvement" / "knowledge" / "current"
MEMORY_PATH = REPO_ROOT / ".self-improvement" / "MEMORY.md"
LESSONS_PATH = REPO_ROOT / ".self-improvement" / "memory" / "lessons.json"


def _list_knowledge_files(include_content: bool = False) -> list[KnowledgeFile]:
    """List all .md files in the knowledge/current directory."""
    if not KNOWLEDGE_DIR.exists():
        return []

    files: list[KnowledgeFile] = []
    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md")):
        try:
            stat = md_file.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            content = md_file.read_text(encoding="utf-8") if include_content else None
            files.append(
                KnowledgeFile(
                    filename=md_file.name,
                    last_modified=last_modified,
                    size_bytes=stat.st_size,
                    content=content,
                )
            )
        except Exception as exc:
            logger.warning("Failed to stat knowledge file %s: %s", md_file.name, exc)

    return files


@router.get("", response_model=KnowledgeResponse)
async def list_knowledge() -> KnowledgeResponse:
    """Return metadata for all knowledge files."""
    files = _list_knowledge_files(include_content=False)
    return KnowledgeResponse(files=files)


# --- Static paths MUST come before the /{filename} catch-all ---


@router.get("/memory/content", response_model=MemoryResponse)
async def get_memory() -> MemoryResponse:
    """Return MEMORY.md content for inline rendering on the knowledge page."""
    if not MEMORY_PATH.exists():
        raise HTTPException(status_code=404, detail="MEMORY.md not found")
    try:
        stat = MEMORY_PATH.stat()
        content = MEMORY_PATH.read_text(encoding="utf-8")
        return MemoryResponse(
            content=content,
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            size_bytes=stat.st_size,
        )
    except Exception as exc:
        logger.error("Failed to read MEMORY.md: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read MEMORY.md") from exc


@router.get("/lessons/recent", response_model=LessonsResponse)
async def get_recent_lessons(
    limit: int = Query(default=20, ge=1, le=100),
) -> LessonsResponse:
    """Return the most recent lessons from lessons.json."""
    if not LESSONS_PATH.exists():
        return LessonsResponse(lessons=[], total=0)

    try:
        raw = json.loads(LESSONS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read lessons.json: %s", exc)
        return LessonsResponse(lessons=[], total=0)

    # lessons.json may be a list or a dict with a "lessons" key
    entries: list[dict[str, Any]] = []
    if isinstance(raw, list):
        entries = raw
    elif isinstance(raw, dict) and "lessons" in raw:
        entries = raw["lessons"]

    total = len(entries)
    # Take last N entries (most recent at end)
    recent = entries[-limit:] if len(entries) > limit else entries
    recent.reverse()  # newest first

    lessons = []
    for i, entry in enumerate(recent):
        lessons.append(
            LessonEntry(
                id=entry.get("id", str(i)),
                date=entry.get("date"),
                lesson=entry.get("lesson") or entry.get("text") or entry.get("description", ""),
                source=entry.get("source"),
                agent_id=entry.get("agent_id"),
                category=entry.get("category"),
                context=entry.get("context"),
            )
        )

    return LessonsResponse(lessons=lessons, total=total)


# --- Catch-all for individual knowledge files ---


@router.get("/{filename}", response_model=KnowledgeFile)
async def get_knowledge_file(filename: str) -> KnowledgeFile:
    """Return a single knowledge file with content."""
    # Sanitize filename — no path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    target = KNOWLEDGE_DIR / filename
    if not target.exists() or target.suffix != ".md":
        raise HTTPException(status_code=404, detail=f"Knowledge file '{filename}' not found")

    try:
        stat = target.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        content = target.read_text(encoding="utf-8")
        return KnowledgeFile(
            filename=target.name,
            last_modified=last_modified,
            size_bytes=stat.st_size,
            content=content,
        )
    except Exception as exc:
        logger.error("Failed to read knowledge file %s: %s", filename, exc)
        raise HTTPException(status_code=500, detail="Failed to read knowledge file") from exc
