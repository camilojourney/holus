#!/usr/bin/env python3
"""Build master index files from image sidecar metadata.

Reads all sidecar .json files from creator images/ directories and produces:
  1. _index/all-images.jsonl     — one line per image, full metadata
  2. _index/by-visual-type.json  — grouped summary with counts and top images
  3. _index/top-1000.json        — all images ranked by engagement * teaching_value

Usage:
    cd holus && uv run python scripts/build_master_index.py
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

REF_DIR = Path("data/reference-library")
INDEX_DIR = REF_DIR / "_index"

IMAGE_SIDECAR_PATTERN = re.compile(r"^\d{3}-\d+-.*\.json$")


def collect_sidecars() -> list[dict]:
    """Walk all creator images/ dirs and collect sidecar JSON data."""
    records: list[dict] = []

    for creator_dir in sorted(REF_DIR.iterdir()):
        if not creator_dir.is_dir():
            continue
        if creator_dir.name.startswith("_") or creator_dir.name.startswith("."):
            continue
        if creator_dir.name == "scraper":
            continue

        images_dir = creator_dir / "images"
        if not images_dir.exists() or not images_dir.is_dir():
            continue

        for sidecar_file in sorted(images_dir.iterdir()):
            if not sidecar_file.is_file():
                continue
            if sidecar_file.suffix != ".json":
                continue
            if not IMAGE_SIDECAR_PATTERN.match(sidecar_file.name):
                continue

            try:
                data = json.loads(sidecar_file.read_text())
                # Add relative path for reference
                data["_path"] = str(sidecar_file.relative_to(REF_DIR))
                # Add image path (swap .json -> original image extension)
                image_file = data.get("image_file", "")
                if image_file:
                    data["_image_path"] = str(
                        (creator_dir / "images" / image_file).relative_to(REF_DIR)
                    )
                records.append(data)
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("Skipping %s: %s", sidecar_file, exc)

    return records


def compute_score(record: dict) -> float:
    """Compute ranking score: engagement.total * classification.teaching_value."""
    engagement_total = 0
    engagement = record.get("engagement")
    if isinstance(engagement, dict):
        engagement_total = engagement.get("total", 0) or 0

    teaching_value = 0
    classification = record.get("classification")
    if isinstance(classification, dict):
        teaching_value = classification.get("teaching_value", 0) or 0

    # If no classification, use engagement alone (teaching_value defaults to 1)
    if teaching_value == 0:
        teaching_value = 1

    return engagement_total * teaching_value


def build_all_images_jsonl(records: list[dict]) -> None:
    """Write _index/all-images.jsonl — one line per image."""
    output = INDEX_DIR / "all-images.jsonl"
    with open(output, "w") as f:
        for record in records:
            # Write without the internal _path/_image_path fields
            clean = {k: v for k, v in record.items() if not k.startswith("_")}
            clean["image_path"] = record.get("_image_path", "")
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")
    log.info("Wrote %d records to %s", len(records), output)


def build_by_visual_type(records: list[dict]) -> None:
    """Write _index/by-visual-type.json — grouped summary."""
    groups: dict[str, list[dict]] = defaultdict(list)

    for record in records:
        visual_type = "unclassified"
        classification = record.get("classification")
        if isinstance(classification, dict) and classification.get("visual_type"):
            visual_type = classification["visual_type"]
        groups[visual_type].append(record)

    summary: dict[str, dict] = {}
    for vtype, group_records in sorted(groups.items()):
        engagement_totals = []
        scored: list[tuple[float, str]] = []

        for r in group_records:
            eng = r.get("engagement", {})
            total = eng.get("total", 0) if isinstance(eng, dict) else 0
            engagement_totals.append(total)

            score = compute_score(r)
            image_path = r.get("_image_path", r.get("image_file", ""))
            scored.append((score, image_path))

        avg_engagement = (
            sum(engagement_totals) / len(engagement_totals) if engagement_totals else 0
        )
        # Top images by score
        scored.sort(key=lambda x: x[0], reverse=True)
        top_paths = [path for _, path in scored[:5]]

        summary[vtype] = {
            "count": len(group_records),
            "avg_engagement": round(avg_engagement),
            "top_images": top_paths,
        }

    output = INDEX_DIR / "by-visual-type.json"
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    log.info("Wrote %d visual types to %s", len(summary), output)


def build_top_1000(records: list[dict]) -> None:
    """Write _index/top-1000.json — all images ranked by score."""
    scored: list[tuple[float, dict]] = []

    for record in records:
        score = compute_score(record)
        entry = {
            "id": record.get("id", ""),
            "creator": record.get("creator", ""),
            "image_path": record.get("_image_path", ""),
            "image_file": record.get("image_file", ""),
            "score": score,
            "engagement_total": (
                record.get("engagement", {}).get("total", 0)
                if isinstance(record.get("engagement"), dict)
                else 0
            ),
            "teaching_value": (
                record.get("classification", {}).get("teaching_value", 0)
                if isinstance(record.get("classification"), dict)
                else 0
            ),
            "visual_type": (
                record.get("classification", {}).get("visual_type", "")
                if isinstance(record.get("classification"), dict)
                else ""
            ),
            "suggested_headline": (
                record.get("classification", {}).get("suggested_headline", "")
                if isinstance(record.get("classification"), dict)
                else ""
            ),
            "urn": record.get("urn", ""),
        }
        scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [entry for _, entry in scored[:1000]]

    output = INDEX_DIR / "top-1000.json"
    output.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n")
    log.info("Wrote %d entries to %s", len(top), output)


def main() -> None:
    if not REF_DIR.exists():
        log.error("Reference library not found: %s", REF_DIR)
        return

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Collecting sidecar metadata from %s", REF_DIR)
    records = collect_sidecars()
    log.info("Found %d image sidecar records across all creators", len(records))

    if not records:
        log.warning("No sidecar files found. Run build_image_metadata.py first.")
        return

    build_all_images_jsonl(records)
    build_by_visual_type(records)
    build_top_1000(records)

    log.info("")
    log.info("Master index built in %s", INDEX_DIR)


if __name__ == "__main__":
    main()
