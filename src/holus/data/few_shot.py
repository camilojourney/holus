"""Few-shot example materializer.

Extracts top-performing posts from the corpus and saves them as
pre-computed JSON files that the content generator reads at generation time.

Usage::

    materializer = FewShotMaterializer()
    materializer.materialize_all()  # Creates data/few-shot-examples/
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from holus.data.corpus import CorpusDB

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("data/few-shot-examples")


def _slugify(text: str) -> str:
    """Convert a content-type label to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "uncategorized"


def _analyze_why_it_works(post: dict[str, Any]) -> str:
    """Heuristic explanation of why a post performed well.

    Based on engagement metrics and text characteristics -- no LLM call.
    """
    reasons: list[str] = []
    text: str = post.get("text", "")
    reactions: int = post.get("reactions", 0)
    engagement: int = post.get("engagement_total", 0)

    # Engagement magnitude.
    if reactions >= 500:
        reasons.append(f"Very high engagement ({reactions:,} reactions)")
    elif reactions >= 100:
        reasons.append(f"High engagement ({reactions:,} reactions)")
    else:
        reasons.append(f"Solid engagement ({reactions:,} reactions)")

    # Hook analysis: first sentence characteristics.
    first_line = text.split("\n")[0].strip() if text else ""

    if re.search(r"\d+", first_line):
        reasons.append("Hook uses specific number")

    if first_line.endswith("?"):
        reasons.append("Opens with a question")

    if any(word in first_line.lower() for word in ("i ", "my ", "i've ", "i'm ")):
        reasons.append("Personal/first-person hook")

    # Content pattern analysis.
    if re.search(r"(?:step|tip|lesson|rule|mistake)\s*\d", text, re.IGNORECASE):
        reasons.append("Numbered list structure")

    if any(word in text.lower() for word in ("built", "shipped", "launched", "created", "made")):
        reasons.append("Builder story with real details")

    if re.search(r"https?://", text):
        reasons.append("Includes external link/resource")

    visual_type = post.get("visual_type", "")
    if visual_type == "carousel/document":
        reasons.append("Carousel format drives saves and shares")
    elif visual_type == "image+text":
        reasons.append("Image increases feed visibility")
    elif visual_type == "video":
        reasons.append("Video format boosts dwell time")

    # Comments-to-reactions ratio indicates discussion quality.
    comments: int = post.get("comments", 0)
    if reactions > 0 and comments / reactions > 0.15:
        reasons.append("High comment ratio — sparks discussion")

    if engagement >= 2000:
        reasons.append("Top-tier virality")

    return ". ".join(reasons) + "."


class FewShotMaterializer:
    """Materializes top-N examples per content type for prompt injection."""

    def __init__(
        self,
        corpus: CorpusDB | None = None,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
    ) -> None:
        self._owns_corpus = corpus is None
        self._corpus = corpus if corpus is not None else CorpusDB()
        self._output_dir = Path(output_dir)

    # ------------------------------------------------------------------
    # Materialize
    # ------------------------------------------------------------------

    def materialize_all(self, top_n: int = 5) -> dict[str, int]:
        """Materialize top-N examples for each content type.

        Creates ``data/few-shot-examples/{slug}/top-5.json``.
        Returns ``{content_type: count}``.
        """
        stats = self._corpus.stats()
        content_types: list[str] = [
            row["content_type"] for row in stats.get("by_content_type", []) if row["content_type"]
        ]

        result: dict[str, int] = {}

        for ct in content_types:
            posts = self._corpus.top_by_engagement(content_type=ct, limit=top_n)
            if not posts:
                continue

            examples = [
                {
                    "creator": p["creator"],
                    "text": p["text"],
                    "engagement_total": p["engagement_total"],
                    "why_it_works": _analyze_why_it_works(p),
                }
                for p in posts
            ]

            slug = _slugify(ct)
            out_dir = self._output_dir / slug
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"top-{top_n}.json"
            out_file.write_text(
                json.dumps(examples, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            result[ct] = len(examples)
            logger.info("Materialized %d examples for %s → %s", len(examples), ct, out_file)

        # Also materialize an "all" bucket with top-N across all types.
        all_posts = self._corpus.top_by_engagement(limit=top_n)
        if all_posts:
            examples = [
                {
                    "creator": p["creator"],
                    "text": p["text"],
                    "engagement_total": p["engagement_total"],
                    "why_it_works": _analyze_why_it_works(p),
                }
                for p in all_posts
            ]
            out_dir = self._output_dir / "all"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"top-{top_n}.json"
            out_file.write_text(
                json.dumps(examples, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            result["all"] = len(examples)

        logger.info("Materialization complete: %s", result)
        return result

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_examples(self, content_type: str, limit: int = 3) -> list[dict[str, Any]]:
        """Load pre-materialized examples for a content type.

        Falls back to the ``all`` bucket if the specific type has no examples.
        """
        slug = _slugify(content_type)
        candidates = [
            self._output_dir / slug,
            self._output_dir / "all",
        ]

        for candidate_dir in candidates:
            # Find any top-N file in the directory.
            if not candidate_dir.is_dir():
                continue
            files = sorted(candidate_dir.glob("top-*.json"), reverse=True)
            if not files:
                continue
            data: list[dict[str, Any]] = json.loads(files[0].read_text(encoding="utf-8"))
            return data[:limit]

        logger.warning("No materialized examples found for %r", content_type)
        return []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying corpus if we own it."""
        if self._owns_corpus:
            self._corpus.close()

    def __enter__(self) -> FewShotMaterializer:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
