#!/usr/bin/env python3
"""Build sidecar JSON metadata files for every downloaded creator image.

Reads posts-raw.json from each creator, matches downloaded images by index prefix,
and writes a companion .json file next to each image with full metadata.

Optionally merges classification data from visual_classifications.jsonl.

Usage:
    cd holus && uv run python scripts/build_image_metadata.py
"""
from __future__ import annotations

import contextlib
import json
import logging
import re
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

REF_DIR = Path("data/reference-library")
CLASSIFICATIONS_PATH = Path("/Volumes/SSD/holus/training-data/linkedin/visual_classifications.jsonl")

# Pattern: {index:03d}-{img_idx}-{slug}.{ext}
IMAGE_PATTERN = re.compile(r"^(\d{3})-(\d+)-(.*)\.(jpg|jpeg|png|gif|webp)$", re.IGNORECASE)


def parse_engagement(value: str | int | float | None) -> int:
    """Parse engagement numbers from various formats: '1,944', '1.2K', '52', '', None."""
    if value is None or value == "":
        return 0
    s = str(value).strip()
    if not s:
        return 0
    # Remove commas: '1,944' -> '1944'
    s = s.replace(",", "")
    # Handle K/M suffixes: '1.2K' -> 1200
    upper = s.upper()
    if upper.endswith("K"):
        try:
            return int(float(upper[:-1]) * 1_000)
        except ValueError:
            return 0
    if upper.endswith("M"):
        try:
            return int(float(upper[:-1]) * 1_000_000)
        except ValueError:
            return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def load_classifications() -> dict[str, dict]:
    """Load visual_classifications.jsonl keyed by URN."""
    classifications: dict[str, dict] = {}
    if not CLASSIFICATIONS_PATH.exists():
        log.warning("Classifications file not found: %s", CLASSIFICATIONS_PATH)
        return classifications

    with open(CLASSIFICATIONS_PATH) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                urn = record.get("urn", "")
                if urn:
                    classifications[urn] = record
            except json.JSONDecodeError:
                log.warning("Skipping malformed JSON at line %d in classifications", line_num)
    log.info("Loaded %d classifications from %s", len(classifications), CLASSIFICATIONS_PATH)
    return classifications


def build_creator_slug(creator_name: str) -> str:
    """Turn 'Santiago Valdarrama' into 'santiago-valdarrama'."""
    return re.sub(r"[^a-z0-9]+", "-", creator_name.lower()).strip("-")


def build_sidecar(
    *,
    creator_name: str,
    creator_slug: str,
    post: dict,
    image_file: Path,
    img_index: int,
    classification: dict | None,
) -> dict:
    """Build the sidecar metadata dict for one image."""
    post_index = post.get("index", 0)
    reactions = parse_engagement(post.get("reactions"))
    comments = parse_engagement(post.get("comments"))
    reposts = parse_engagement(post.get("reposts"))

    image_bytes = 0
    with contextlib.suppress(OSError):
        image_bytes = image_file.stat().st_size

    sidecar: dict = {
        "id": f"{creator_slug}-{post_index}-{img_index}",
        "creator": creator_name,
        "platform": "linkedin",
        "post_text": post.get("text", ""),
        "post_type": post.get("postType", "unknown"),
        "image_file": image_file.name,
        "image_format": image_file.suffix.lstrip(".").lower(),
        "image_bytes": image_bytes,
        "engagement": {
            "reactions": reactions,
            "comments": comments,
            "reposts": reposts,
            "total": reactions + comments + reposts,
        },
        "classification": None,
        "scraped_at": None,
        "source_url": None,
        "urn": post.get("urn", ""),
    }

    # Extract scraped_at from timestamp if available
    timestamp = post.get("timestamp", "")
    if timestamp:
        sidecar["scraped_at"] = timestamp.split("•")[0].strip() if "•" in timestamp else timestamp

    # Extract source URL — match by img_index into post's images list
    images_list = post.get("images", [])
    if img_index < len(images_list):
        sidecar["source_url"] = images_list[img_index]

    # Merge classification data
    if classification:
        sidecar["classification"] = {
            "visual_type": classification.get("ideal_visual_type", ""),
            "teaching_value": classification.get("teaching_potential", 0),
            "scroll_stop_power": 0,  # Not in current classification data
            "key_visual_elements": classification.get("key_visual_elements", []),
            "suggested_headline": classification.get("suggested_headline", ""),
        }
        # Use engagement from classification if it looks more complete (has actual totals)
        cls_total = classification.get("engagement_total", 0)
        if cls_total and cls_total > sidecar["engagement"]["total"]:
            sidecar["engagement"] = {
                "reactions": classification.get("engagement_reactions", reactions),
                "comments": classification.get("engagement_comments", comments),
                "reposts": classification.get("engagement_reposts", reposts),
                "total": cls_total,
            }

    return sidecar


def process_creator(creator_dir: Path, classifications: dict[str, dict]) -> tuple[int, int]:
    """Process one creator directory. Returns (created, skipped) counts."""
    posts_file = creator_dir / "posts-raw.json"
    images_dir = creator_dir / "images"

    if not posts_file.exists():
        return 0, 0
    if not images_dir.exists() or not images_dir.is_dir():
        return 0, 0

    # Scan actual image files and group by post index
    image_files: dict[int, list[tuple[int, Path]]] = {}
    for entry in sorted(images_dir.iterdir()):
        if entry.is_file():
            match = IMAGE_PATTERN.match(entry.name)
            if match:
                post_idx = int(match.group(1))
                img_idx = int(match.group(2))
                image_files.setdefault(post_idx, []).append((img_idx, entry))

    if not image_files:
        return 0, 0

    # Load posts and index by post index
    posts = json.loads(posts_file.read_text())
    posts_by_index: dict[int, dict] = {}
    for post in posts:
        idx = post.get("index")
        if idx is not None:
            posts_by_index[idx] = post

    creator_name = creator_dir.name
    creator_slug = build_creator_slug(creator_name)
    created = 0
    skipped = 0

    for post_idx, imgs in sorted(image_files.items()):
        post = posts_by_index.get(post_idx)
        if not post:
            log.warning("No post found for index %d in %s", post_idx, creator_name)
            skipped += len(imgs)
            continue

        urn = post.get("urn", "")
        classification = classifications.get(urn)

        for img_idx, image_path in sorted(imgs):
            sidecar_path = image_path.with_suffix(".json")

            sidecar = build_sidecar(
                creator_name=creator_name,
                creator_slug=creator_slug,
                post=post,
                image_file=image_path,
                img_index=img_idx,
                classification=classification,
            )

            sidecar_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n")
            created += 1

    return created, skipped


def main() -> None:
    if not REF_DIR.exists():
        log.error("Reference library not found: %s", REF_DIR)
        return

    classifications = load_classifications()

    total_created = 0
    total_skipped = 0
    creators_processed = 0

    for creator_dir in sorted(REF_DIR.iterdir()):
        if not creator_dir.is_dir():
            continue
        # Skip special directories
        if creator_dir.name.startswith("_") or creator_dir.name.startswith("."):
            continue
        if creator_dir.name == "scraper":
            continue

        created, skipped = process_creator(creator_dir, classifications)
        if created > 0 or skipped > 0:
            log.info("%-30s created=%d  skipped=%d", creator_dir.name, created, skipped)
            creators_processed += 1
            total_created += created
            total_skipped += skipped

    log.info("")
    log.info("Done. Creators: %d, Sidecars created: %d, Skipped: %d",
             creators_processed, total_created, total_skipped)


if __name__ == "__main__":
    main()
