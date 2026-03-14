#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from holus.visual.engine import PlaywrightEngine
from holus.visual.templates import TemplateEngine


@dataclass(frozen=True)
class BaselineCapture:
    template_name: str
    variables: dict[str, str | int | float | bool | list[str]]
    viewport: tuple[int, int]


CAPTURES = [
    BaselineCapture(
        template_name="single_image/insight",
        variables={
            "headline": "AI is changing content creation",
            "body": "Creators who use AI tools produce 3x more content",
            "stat_value": "3x",
            "stat_label": "more content",
            "author_name": "Camilo",
        },
        viewport=(1080, 1080),
    ),
    BaselineCapture(
        template_name="carousel/hook_slide",
        variables={
            "headline": "5 Ways AI Beats Manual Content",
            "subheadline": "A data-driven breakdown",
            "slide_number": 1,
            "total_slides": 5,
            "author_name": "Camilo",
        },
        viewport=(1080, 1350),
    ),
    BaselineCapture(
        template_name="carousel/body_slide",
        variables={
            "title": "Speed",
            "body_text": "AI generates a first draft in seconds",
            "bullets": ["No writer's block", "Consistent tone", "Scales infinitely"],
            "slide_number": 2,
            "total_slides": 5,
        },
        viewport=(1080, 1350),
    ),
    BaselineCapture(
        template_name="single_image/data_viz",
        variables={
            "title": "Content Performance",
            "svg_content": (
                "<svg viewBox='0 0 800 400' width='800' height='400'>"
                "<rect width='800' height='400' fill='#0f172a'/>"
                "<text x='400' y='200' text-anchor='middle' fill='white' font-size='24'>"
                "Sample Chart"
                "</text></svg>"
            ),
            "source_label": "Source: internal data",
        },
        viewport=(1080, 1080),
    ),
]


async def main() -> None:
    template_engine = TemplateEngine()
    output_dir = Path("data/visual-baselines")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with PlaywrightEngine(template_engine=template_engine) as renderer:
            for capture in CAPTURES:
                html = template_engine.render(capture.template_name, capture.variables)

                try:
                    result = await renderer.render_png(html, viewport=capture.viewport)
                except Exception as exc:
                    print(f"Warning: failed to render {capture.template_name}: {exc}")
                    continue

                if not result.success or result.output_bytes is None:
                    print(
                        "Warning: failed to render "
                        f"{capture.template_name}: {result.error or 'unknown error'}"
                    )
                    continue

                output_path = output_dir / f"{capture.template_name.replace('/', '-')}.png"
                output_path.write_bytes(result.output_bytes)
                print(output_path)
    except Exception as exc:
        for capture in CAPTURES:
            print(f"Warning: failed to initialize renderer for {capture.template_name}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
