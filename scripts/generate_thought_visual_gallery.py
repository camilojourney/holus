"""Generate a local gallery for Thought Studio visual strategy testing.

This is a deterministic smoke/eval utility, not a publishing path. It lets us
inspect how different raw thoughts become rendered images and creative contracts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import yaml

from holus.agents.marketing.thought_pipeline import ThoughtContentPipeline

DEFAULT_THOUGHTS = [
    "Simplicity is king when working with AI. The model knows a lot; it needs focus, not noise.",
    "The mistake I keep making is trying to automate judgment before I understand the taste.",
    "A good product demo is not a tour. It is one painful before-and-after shown clearly.",
    "Most creators do not need more ideas. They need a repeatable way to package the ideas they already have.",
    "The best AI systems feel calm because the complexity is hidden behind one obvious next action.",
]


async def _run(thoughts: list[str], output_dir: Path) -> list[dict[str, Any]]:
    queue_dir = output_dir / "content-queue"
    rendered_dir = output_dir / "rendered-content"
    pipeline = ThoughtContentPipeline(queue_dir=queue_dir, rendered_dir=rendered_dir)
    manifest: list[dict[str, Any]] = []

    for thought in thoughts:
        content_set = await pipeline.create_content_set(
            thought=thought,
            channels=["instagram_image", "linkedin_carousel"],
        )
        for record in content_set.records:
            visual_spec = record.get("visual_spec") or {}
            manifest.append(
                {
                    "piece_id": record["piece_id"],
                    "group_id": record["group_id"],
                    "platform": record["platform"],
                    "content_type": record["content_type"],
                    "thought": thought,
                    "asset": record.get("rendered_image_path") or record.get("rendered_pdf_path"),
                    "visual_type": visual_spec.get("type"),
                    "style_profile": visual_spec.get("style_profile"),
                    "creative_contract": visual_spec.get("creative_contract"),
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="data/visual-gallery/thought-studio",
        help="Where to write queue records, rendered assets, and manifests.",
    )
    parser.add_argument(
        "--thought",
        action="append",
        dest="thoughts",
        help="Custom thought to render. Can be passed multiple times.",
    )
    args = parser.parse_args()

    thoughts = args.thoughts or DEFAULT_THOUGHTS
    manifest = asyncio.run(_run(thoughts, Path(args.output_dir)))
    for item in manifest:
        print(f"{item['piece_id']}: {item['visual_type']} -> {item['asset']}")
    print(f"Wrote {len(manifest)} records to {args.output_dir}")


if __name__ == "__main__":
    main()
