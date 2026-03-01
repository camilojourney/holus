"""Knowledge base loader: validate and load knowledge files for agent context.

Agents read knowledge files from ``.self-improvement/knowledge/current/``
at the start of every marketing cycle (observe stage).  Each file must have
a metadata header with required fields.  This module validates headers and
loads files into structured data.

Spec reference: 012-knowledge-learning.md SPEC-001
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE_DIR = Path(".self-improvement/knowledge/current")

REQUIRED_HEADERS = frozenset(
    {
        "Last updated",
        "Updated by",
        "Confidence",
        "Affects",
        "Research cadence",
    }
)

VALID_CONFIDENCE_LEVELS = frozenset(
    {
        "preliminary",
        "medium",
        "high",
        "validated",
    }
)


@dataclass(frozen=True)
class KnowledgeFile:
    """A parsed and validated knowledge file."""

    path: Path
    title: str
    last_updated: str
    updated_by: str
    confidence: str
    affects: str
    research_cadence: str
    content: str
    errors: tuple[str, ...] = field(default=())

    @property
    def is_valid(self) -> bool:
        """Whether the file passed all validation checks."""
        return len(self.errors) == 0


def validate_knowledge_file(path: Path) -> KnowledgeFile:
    """Parse and validate a single knowledge file's metadata header.

    Args:
        path: Path to the knowledge markdown file.

    Returns:
        KnowledgeFile with parsed metadata and any validation errors.
    """
    try:
        text = path.read_text()
    except OSError:
        return KnowledgeFile(
            path=path,
            title="",
            last_updated="",
            updated_by="",
            confidence="",
            affects="",
            research_cadence="",
            content="",
            errors=(f"Cannot read file: {path}",),
        )

    errors: list[str] = []

    # Extract title (first H1)
    title_match = re.match(r"^#\s+(.+)", text)
    title = title_match.group(1).strip() if title_match else ""
    if not title:
        errors.append("Missing title (expected '# Knowledge: Topic Name')")

    def _extract_header(label: str) -> str:
        match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", text)
        return match.group(1).strip() if match else ""

    last_updated = _extract_header("Last updated")
    updated_by = _extract_header("Updated by")
    confidence_raw = _extract_header("Confidence")
    affects = _extract_header("Affects")
    research_cadence = _extract_header("Research cadence")

    # Check required headers are present
    for header_name, value in [
        ("Last updated", last_updated),
        ("Updated by", updated_by),
        ("Confidence", confidence_raw),
        ("Affects", affects),
        ("Research cadence", research_cadence),
    ]:
        if not value:
            errors.append(f"Missing required header: {header_name}")

    # Validate confidence level (extract base level before parenthetical notes)
    confidence_base = confidence_raw.split("(")[0].strip().lower() if confidence_raw else ""
    if confidence_raw and confidence_base not in VALID_CONFIDENCE_LEVELS:
        errors.append(
            f"Invalid confidence level: '{confidence_base}' "
            f"(expected one of: {', '.join(sorted(VALID_CONFIDENCE_LEVELS))})"
        )

    return KnowledgeFile(
        path=path,
        title=title,
        last_updated=last_updated,
        updated_by=updated_by,
        confidence=confidence_raw,
        affects=affects,
        research_cadence=research_cadence,
        content=text,
        errors=tuple(errors),
    )


def load_knowledge_files(
    *,
    knowledge_dir: Path = DEFAULT_KNOWLEDGE_DIR,
    skip_invalid: bool = True,
) -> list[KnowledgeFile]:
    """Load and validate all knowledge files from the current/ directory.

    Args:
        knowledge_dir: Path to the knowledge directory.
        skip_invalid: If True, log warnings for invalid files but still include them.
            If False, raise ValueError on the first invalid file.

    Returns:
        List of KnowledgeFile objects sorted by title.
    """
    if not knowledge_dir.exists():
        logger.warning("Knowledge directory does not exist: %s", knowledge_dir)
        return []

    files: list[KnowledgeFile] = []

    for path in sorted(knowledge_dir.glob("*.md")):
        if path.name == "README.md":
            continue

        kf = validate_knowledge_file(path)

        if not kf.is_valid:
            if skip_invalid:
                logger.warning(
                    "Knowledge file has validation errors: %s — %s",
                    path.name,
                    "; ".join(kf.errors),
                )
            else:
                msg = f"Invalid knowledge file {path.name}: {'; '.join(kf.errors)}"
                raise ValueError(msg)

        files.append(kf)

    logger.info("Loaded %d knowledge files from %s", len(files), knowledge_dir)
    return files
