#!/usr/bin/env python3
"""Download actual images from LinkedIn posts (not screenshots).

Reads posts-raw.json from each creator, downloads images from the `images` URLs,
and saves them organized by creator in data/reference-library/{creator}/images/.

These are the REAL visuals (infographics, flowcharts, charts) that creators used,
not the Playwright screenshots of the full post.

Usage:
    cd holus && uv run python scripts/download_creator_images.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

REF_DIR = Path("data/reference-library")
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max images to download (0=all)")
    args = parser.parse_args()

    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    total_video = 0

    for creator_dir in sorted(REF_DIR.iterdir()):
        if not creator_dir.is_dir():
            continue
        posts_file = creator_dir / "posts-raw.json"
        if not posts_file.exists():
            continue

        creator = creator_dir.name
        images_dir = creator_dir / "images"
        images_dir.mkdir(exist_ok=True)

        posts = json.loads(posts_file.read_text())

        for post in posts:
            if args.limit and total_downloaded >= args.limit:
                break

            post_type = post.get("postType", "unknown")
            images = post.get("images", [])
            index = post.get("index", 0)

            # Skip video-only posts
            if "video" in post_type.lower() and not images:
                total_video += 1
                continue

            if not images:
                continue

            for img_idx, url in enumerate(images):
                if args.limit and total_downloaded >= args.limit:
                    break

                # Build filename from post index and image index
                slug = (post.get("text", "") or "")[:50].lower()
                slug = "".join(c if c.isalnum() or c in "-_ " else "" for c in slug)
                slug = slug.strip().replace(" ", "-")[:40]
                filename = f"{index:03d}-{img_idx}-{slug}.jpg"
                filepath = images_dir / filename

                if filepath.exists():
                    total_skipped += 1
                    continue

                try:
                    resp = SESSION.get(url, timeout=15)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        # Detect actual format from content-type
                        ct = resp.headers.get("content-type", "")
                        if "png" in ct:
                            filepath = filepath.with_suffix(".png")
                        elif "gif" in ct:
                            filepath = filepath.with_suffix(".gif")
                        elif "webp" in ct:
                            filepath = filepath.with_suffix(".webp")

                        filepath.write_bytes(resp.content)
                        total_downloaded += 1
                        log.info("[%d] %s/%s (%s bytes)", total_downloaded, creator, filepath.name, f"{len(resp.content):,}")
                    else:
                        total_failed += 1
                        log.warning("Failed: %s (status=%d, size=%d)", url[:80], resp.status_code, len(resp.content))
                except Exception as exc:
                    total_failed += 1
                    log.warning("Error: %s — %s", url[:80], exc)

                time.sleep(0.3)  # Rate limit

    log.info("\nDone. Downloaded: %d, Skipped (exist): %d, Failed: %d, Video-only: %d",
             total_downloaded, total_skipped, total_failed, total_video)


if __name__ == "__main__":
    main()
