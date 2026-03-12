"""Knowledge routes — GET /api/v1/knowledge."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from holus.api.models import KnowledgeFile, KnowledgeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
KNOWLEDGE_DIR = REPO_ROOT / ".self-improvement" / "knowledge" / "current"


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
