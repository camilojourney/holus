#!/usr/bin/env python3
"""Extract top-performing golden examples per visual type from classification data.

Reads visual_classifications.jsonl, groups by ideal_visual_type, ranks by
engagement × teaching_potential, and copies top 5 screenshots + metadata
into golden_examples/{type}/ directories.

These golden examples become few-shot prompts for visual generation.

Usage:
    cd holus && uv run python scripts/extract_golden_examples.py
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

CLASSIFICATIONS_PATH = Path("/Volumes/SSD/holus/training-data/linkedin/visual_classifications.jsonl")
GOLDEN_DIR = Path("/Volumes/SSD/holus/training-data/linkedin/golden_examples")
REF_DIR = Path("/Volumes/SSD/holus/reference-library")
TOP_N = 5


def main() -> None:
    if not CLASSIFICATIONS_PATH.exists():
        log.error("No classifications found at %s. Run classify_reference_screenshots.py first.", CLASSIFICATIONS_PATH)
        return

    # Load all classifications
    entries: list[dict] = []
    for line in CLASSIFICATIONS_PATH.read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    log.info("Loaded %d classified posts", len(entries))

    # Group by visual type
    by_type: dict[str, list[dict]] = {}
    for entry in entries:
        vt = entry.get("ideal_visual_type", "unknown")
        by_type.setdefault(vt, []).append(entry)

    log.info("Visual types found: %s", sorted(by_type.keys()))

    # For each type, rank by engagement × teaching_potential and take top N
    summary: list[dict] = []
    for vt, posts in sorted(by_type.items()):
        type_dir = GOLDEN_DIR / vt
        type_dir.mkdir(parents=True, exist_ok=True)

        # Score: engagement_total × teaching_potential (favor high engagement + high teaching)
        for p in posts:
            p["_score"] = p.get("engagement_total", 0) * p.get("teaching_potential", 5)

        ranked = sorted(posts, key=lambda x: x["_score"], reverse=True)
        top = ranked[:TOP_N]

        # Write metadata for this type
        type_meta = {
            "visual_type": vt,
            "total_posts": len(posts),
            "avg_engagement": sum(p["engagement_total"] for p in posts) / len(posts) if posts else 0,
            "avg_teaching_potential": sum(p.get("teaching_potential", 5) for p in posts) / len(posts) if posts else 0,
            "top_creators": _top_creators(posts),
            "golden_examples": [],
        }

        for i, ex in enumerate(top):
            # Copy screenshot if it exists
            screenshot_src = REF_DIR / ex["creator"] / ex.get("screenshot", "")
            screenshot_dst = type_dir / f"{i+1:02d}-{_slug(ex['creator'])}.png"
            if screenshot_src.exists():
                shutil.copy2(screenshot_src, screenshot_dst)
                log.info("  Copied: %s → %s", screenshot_src.name, screenshot_dst.name)

            golden_entry = {
                "rank": i + 1,
                "creator": ex["creator"],
                "engagement_total": ex["engagement_total"],
                "teaching_potential": ex.get("teaching_potential", 5),
                "score": ex["_score"],
                "suggested_headline": ex.get("suggested_headline", ""),
                "visual_type_reason": ex.get("visual_type_reason", ""),
                "key_visual_elements": ex.get("key_visual_elements", []),
                "text_preview": ex.get("text_preview", "")[:300],
                "screenshot_file": screenshot_dst.name if screenshot_src.exists() else None,
            }
            type_meta["golden_examples"].append(golden_entry)

        # Write type metadata
        meta_path = type_dir / "metadata.json"
        meta_path.write_text(json.dumps(type_meta, indent=2))

        summary.append({
            "type": vt,
            "count": len(posts),
            "avg_eng": round(type_meta["avg_engagement"]),
            "top_creator": top[0]["creator"] if top else "?",
            "top_score": top[0]["_score"] if top else 0,
        })
        log.info("%-25s %3d posts, avg engagement %5d, top: %s (%d)",
                 vt, len(posts), type_meta["avg_engagement"],
                 top[0]["creator"] if top else "?", top[0]["_score"] if top else 0)

    # Write overall summary
    summary_path = GOLDEN_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    log.info("\nSummary written to %s", summary_path)
    log.info("Golden examples in %s", GOLDEN_DIR)


def _top_creators(posts: list[dict], n: int = 3) -> list[str]:
    counts: dict[str, int] = {}
    for p in posts:
        counts[p["creator"]] = counts.get(p["creator"], 0) + 1
    return [c for c, _ in sorted(counts.items(), key=lambda x: -x[1])[:n]]


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "")[:30]


if __name__ == "__main__":
    main()
