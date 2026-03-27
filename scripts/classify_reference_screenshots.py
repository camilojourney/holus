#!/usr/bin/env python3
"""Classify 569 reference posts by ideal visual type using LLM text analysis.

Reads posts-raw.json from each creator in reference-library/, sends the post TEXT
through the proxy to classify what visual type would best accompany it, joins with
engagement data, and outputs a JSONL training dataset.

No vision API needed — classifies based on post content, not screenshots.

Usage:
    cd holus && uv run python scripts/classify_reference_screenshots.py [--limit N] [--resume]
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

PROXY_URL = "http://localhost:8080/v1/chat/completions"
PROXY_HEADERS = {"Content-Type": "application/json"}
REF_DIR = Path("/Volumes/SSD/holus/reference-library")
OUT_PATH = Path("/Volumes/SSD/holus/training-data/linkedin/visual_classifications.jsonl")

CLASSIFICATION_PROMPT = """\
You are a LinkedIn content strategist. Given a post's text and metadata, classify what visual type would BEST accompany this post for maximum engagement.

Post text:
---
{text}
---

Post type: {post_type}
Creator: {creator}
Category: {category}

Return ONLY valid JSON with these fields:

{{
  "ideal_visual_type": one of ["flowchart", "architecture_diagram", "data_viz_chart", "comparison_table", "code_snippet", "research_card", "stat_card", "checklist", "timeline", "infographic", "screenshot", "quote_card", "photo", "none_text_only"],
  "visual_type_reason": "1 sentence why this visual type fits",
  "key_visual_elements": ["element1", "element2", "element3"],
  "suggested_headline": "max 8 words for the visual",
  "data_points_extractable": true/false,
  "has_sequential_process": true/false,
  "has_system_components": true/false,
  "has_comparison": true/false,
  "has_code": true/false,
  "has_data_or_stats": true/false,
  "content_complexity": "simple|moderate|complex",
  "teaching_potential": 1-10
}}
"""


def _parse_count(val: str | int) -> int:
    if isinstance(val, int):
        return val
    val = str(val).strip().replace(",", "")
    if not val:
        return 0
    m = re.match(r"([\d.]+)\s*[kK]", val)
    if m:
        return int(float(m.group(1)) * 1000)
    try:
        return int(val)
    except ValueError:
        return 0


def _load_all_posts() -> list[dict]:
    """Load all posts from all creators, enrich with creator name."""
    all_posts: list[dict] = []
    for creator_dir in sorted(REF_DIR.iterdir()):
        if not creator_dir.is_dir():
            continue
        posts_file = creator_dir / "posts-raw.json"
        if not posts_file.exists():
            continue
        creator = creator_dir.name
        try:
            posts = json.loads(posts_file.read_text())
        except json.JSONDecodeError:
            log.warning("Bad JSON: %s", posts_file)
            continue
        for post in posts:
            text = post.get("text", "") or ""
            if len(text) < 20:
                continue  # Skip empty/tiny posts
            all_posts.append({
                "creator": creator,
                "text": text,
                "post_type": post.get("postType", "unknown"),
                "category": post.get("category", ""),
                "reactions": _parse_count(post.get("reactions", 0)),
                "comments": _parse_count(post.get("comments", 0)),
                "reposts": _parse_count(post.get("reposts", 0)),
                "screenshot": post.get("screenshot", ""),
                "urn": post.get("urn", ""),
            })
    return all_posts


def _classify_post(post: dict) -> dict | None:
    """Send post text to LLM for visual type classification."""
    prompt = CLASSIFICATION_PROMPT.format(
        text=post["text"][:2000],  # Truncate very long posts
        post_type=post["post_type"],
        creator=post["creator"],
        category=post["category"],
    )

    payload = {
        "model": "anthropic/claude-sonnet-4-6",
        "max_tokens": 500,
        "temperature": 0.1,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    try:
        resp = requests.post(PROXY_URL, json=payload, headers=PROXY_HEADERS, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        # Extract JSON from response
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return json.loads(text)
    except Exception as exc:
        log.error("Classification failed: %s", exc)
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max posts to classify (0=all)")
    parser.add_argument("--resume", action="store_true", help="Skip already-classified posts")
    args = parser.parse_args()

    posts = _load_all_posts()
    log.info("Loaded %d posts from %d creators", len(posts), len({p["creator"] for p in posts}))

    # Load already-classified if resuming
    done: set[str] = set()
    if args.resume and OUT_PATH.exists():
        for line in OUT_PATH.read_text().splitlines():
            if line.strip():
                entry = json.loads(line)
                done.add(entry.get("urn", ""))
        log.info("Resuming — %d already classified", len(done))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume else "w"

    classified = 0
    errors = 0
    with open(OUT_PATH, mode) as f:
        for i, post in enumerate(posts):
            if args.limit and classified >= args.limit:
                break
            if post["urn"] in done:
                continue

            log.info("[%d/%d] %s — %.60s", i + 1, len(posts), post["creator"], post["text"][:60])
            result = _classify_post(post)

            if result is None:
                errors += 1
                time.sleep(2)
                continue

            entry = {
                "creator": post["creator"],
                "urn": post["urn"],
                "post_type": post["post_type"],
                "category": post["category"],
                "text_preview": post["text"][:200],
                "screenshot": post["screenshot"],
                **result,
                "engagement_reactions": post["reactions"],
                "engagement_comments": post["comments"],
                "engagement_reposts": post["reposts"],
                "engagement_total": post["reactions"] + post["comments"] + post["reposts"],
            }

            f.write(json.dumps(entry) + "\n")
            f.flush()
            classified += 1

            # Rate limit
            time.sleep(0.5)

    log.info("Done. Classified: %d, Errors: %d, Output: %s", classified, errors, OUT_PATH)

    # Print summary
    if OUT_PATH.exists():
        type_counts: dict[str, int] = {}
        for line in OUT_PATH.read_text().splitlines():
            if line.strip():
                entry = json.loads(line)
                vt = entry.get("ideal_visual_type", "unknown")
                type_counts[vt] = type_counts.get(vt, 0) + 1
        log.info("\n=== Visual Type Distribution ===")
        for vt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            log.info("  %-25s %d", vt, count)


if __name__ == "__main__":
    main()
