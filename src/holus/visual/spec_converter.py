"""Convert visual specialist agent outputs to RenderSpec objects.

Each function takes agent output (JSON-like dicts matching agent output contracts)
and produces a RenderSpec ready for PlaywrightEngine rendering.

Spec 025/026: These converters bridge the gap between specialist agent outputs
and the visual rendering pipeline.
"""

from __future__ import annotations

from typing import Any

from holus.visual.chart import generate_svg
from holus.visual.models import CarouselSpec, OutputFormat, RenderSpec, SlideSpec
from holus.visual.poll import generate_poll_svg


def data_viz_to_spec(
    visualizer_output: dict[str, Any],
    *,
    output_format: OutputFormat = OutputFormat.PNG,
    viewport_width: int = 1080,
    viewport_height: int = 1080,
) -> RenderSpec:
    """Convert data-visualizer agent output to a RenderSpec.

    The data-visualizer agent produces output with chart configuration:
    - chart_type: str (bar, line, pie, comparison, metric)
    - title: str
    - data_points: list[dict] with label + value keys
    - highlight_index: int | None (which bar/point to emphasize)
    - source_label: str (attribution text)
    - color_scheme: str | None (override brand palette)

    Args:
        visualizer_output: Dict from data-visualizer agent output contract.
        output_format: Target format (PNG or PDF).
        viewport_width: Render width in px.
        viewport_height: Render height in px.

    Returns:
        RenderSpec configured for the ``single_image/data_viz`` template.

    Raises:
        ValueError: If required fields (chart_type, title, data_points) are missing.
    """
    _require_keys(visualizer_output, ["chart_type", "title", "data_points"])

    data_points = visualizer_output["data_points"]
    if not isinstance(data_points, list) or len(data_points) == 0:
        msg = "data_points must be a non-empty list"
        raise ValueError(msg)

    # Flatten data_points into template-friendly parallel lists
    labels = [str(dp.get("label", "")) for dp in data_points]
    values = [str(dp.get("value", 0)) for dp in data_points]
    highlight_index = visualizer_output.get("highlight_index")
    color_scheme = visualizer_output.get("color_scheme")
    color = str(color_scheme or "#6366f1")

    # generate_svg rejects empty/whitespace label strings — use a dash placeholder for SVG only
    svg_labels = [lbl if lbl.strip() else "-" for lbl in labels]
    svg_str = generate_svg(
        chart_type=str(visualizer_output["chart_type"]),
        labels=svg_labels,
        values=values,
        highlight_index=int(highlight_index) if highlight_index is not None else None,
        color_accent=color,
    )

    variables: dict[str, str | int | float | bool | list[str]] = {
        "chart_type": str(visualizer_output["chart_type"]),
        "title": str(visualizer_output["title"]),
        "labels": labels,
        "values": values,
        "svg_content": svg_str,
        "source_label": str(visualizer_output.get("source_label", "")),
    }

    if highlight_index is not None:
        variables["highlight_index"] = int(highlight_index)

    if color_scheme is not None:
        variables["color_scheme"] = str(color_scheme)

    return RenderSpec(
        template="single_image/data_viz",
        variables=variables,
        output_format=output_format,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )


def poll_to_spec(
    poll_output: dict[str, Any],
    *,
    output_format: OutputFormat = OutputFormat.PNG,
    viewport_width: int = 1080,
    viewport_height: int = 1080,
) -> RenderSpec:
    """Convert poll agent output to a RenderSpec."""
    _require_keys(poll_output, ["question", "options"])

    options = poll_output["options"]
    if not isinstance(options, list) or not (2 <= len(options) <= 4):
        msg = "options must be a list of 2-4 items"
        raise ValueError(msg)

    color = str(poll_output.get("color_scheme") or "#6366f1")
    svg_str = generate_poll_svg(
        question=str(poll_output["question"]),
        options=[str(option) for option in options],
        color_accent=color,
    )
    variables: dict[str, str | int | float | bool | list[str]] = {
        "question": str(poll_output["question"]),
        "svg_content": svg_str,
        "platform_label": str(poll_output.get("platform", "")),
    }

    return RenderSpec(
        template="single_image/poll",
        variables=variables,
        output_format=output_format,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )


def before_after_to_spec(
    designer_output: dict[str, Any],
    *,
    output_format: OutputFormat = OutputFormat.PNG,
    viewport_width: int = 1080,
    viewport_height: int = 1080,
) -> RenderSpec:
    """Convert brand-designer before/after agent output to a RenderSpec.

    The designer agent produces output with:
    - before_label: str (e.g. "Before")
    - after_label: str (e.g. "After")
    - before_description: str (what the old state looks like)
    - after_description: str (what the new state looks like)
    - headline: str (overall improvement headline)
    - product: str (which product this showcases)
    - before_image_url: str | None (optional screenshot/image URL)
    - after_image_url: str | None (optional screenshot/image URL)

    Args:
        designer_output: Dict from designer agent output contract.
        output_format: Target format (PNG or PDF).
        viewport_width: Render width in px.
        viewport_height: Render height in px.

    Returns:
        RenderSpec configured for the ``single_image/before_after`` template.

    Raises:
        ValueError: If required fields are missing.
    """
    _require_keys(designer_output, ["before_description", "after_description", "headline"])

    variables: dict[str, str | int | float | bool | list[str]] = {
        "headline": str(designer_output["headline"]),
        "before_label": str(designer_output.get("before_label", "Before")),
        "after_label": str(designer_output.get("after_label", "After")),
        "before_description": str(designer_output["before_description"]),
        "after_description": str(designer_output["after_description"]),
        "product": str(designer_output.get("product", "")),
    }

    for url_key in ("before_image_url", "after_image_url"):
        url_val = designer_output.get(url_key)
        if url_val is not None:
            variables[url_key] = str(url_val)

    return RenderSpec(
        template="single_image/before_after",
        variables=variables,
        output_format=output_format,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )


def insight_to_spec(
    text: str,
    stat: str | None = None,
    quote: str | None = None,
    *,
    output_format: OutputFormat = OutputFormat.PNG,
    viewport_width: int = 1080,
    viewport_height: int = 1080,
) -> RenderSpec:
    """Convert a text insight into a single-image RenderSpec.

    Used for quote cards, stat highlights, and key takeaway images.

    Args:
        text: Main body text / insight.
        stat: Optional bold statistic (e.g. "4.2x faster").
        quote: Optional pull-quote to feature prominently.
        output_format: Target format (PNG or PDF).
        viewport_width: Render width in px.
        viewport_height: Render height in px.

    Returns:
        RenderSpec configured for the ``single_image/insight`` template.

    Raises:
        ValueError: If text is empty.
    """
    if not text or not text.strip():
        msg = "text must be a non-empty string"
        raise ValueError(msg)

    variables: dict[str, str | int | float | bool | list[str]] = {
        "text": text.strip(),
    }

    if stat is not None:
        variables["stat"] = stat.strip()

    if quote is not None:
        variables["quote"] = quote.strip()

    return RenderSpec(
        template="single_image/insight",
        variables=variables,
        output_format=output_format,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )


def carousel_spec_to_slides(
    carousel_output: dict[str, Any],
    *,
    output_format: OutputFormat = OutputFormat.PNG,
    viewport_width: int = 1080,
    viewport_height: int = 1350,
) -> CarouselSpec:
    """Convert carousel-architect agent JSON output to a CarouselSpec.

    The carousel-architect agent produces output with:
    - slides: list[dict] — ordered slide definitions, each containing:
        - type: str — one of "hook", "body", "summary", "cta"
        - variables: dict — template-specific variables (headline, body, takeaways, etc.)
    - title: str (optional) — carousel title for metadata

    Template mapping:
    - "hook" → "carousel/hook_slide"
    - "body" → "carousel/body_slide"
    - "summary" → "carousel/summary_slide"
    - "cta" → "carousel/cta_slide"

    Args:
        carousel_output: Dict from carousel-architect agent output contract.
        output_format: Target format (PNG or PDF).
        viewport_width: Slide width in px.
        viewport_height: Slide height in px (default 1350 for 4:5 aspect).

    Returns:
        CarouselSpec with ordered SlideSpecs.

    Raises:
        ValueError: If slides is missing, empty, or contains unknown slide types.
    """
    _require_keys(carousel_output, ["slides"])

    raw_slides = carousel_output["slides"]
    if not isinstance(raw_slides, list) or len(raw_slides) == 0:
        msg = "slides must be a non-empty list"
        raise ValueError(msg)

    type_to_template = {
        "hook": "carousel/hook_slide",
        "body": "carousel/body_slide",
        "summary": "carousel/summary_slide",
        "cta": "carousel/cta_slide",
    }

    slide_specs: list[SlideSpec] = []
    for i, raw_slide in enumerate(raw_slides, start=1):
        slide_type = raw_slide.get("type", "body")
        if slide_type not in type_to_template:
            msg = f"Unknown slide type '{slide_type}' at index {i - 1}. Valid types: {', '.join(type_to_template)}"
            raise ValueError(msg)

        template = type_to_template[slide_type]
        variables = dict(raw_slide.get("variables", {}))

        slide_specs.append(
            SlideSpec(
                template=template,
                variables=variables,
                slide_number=i,
            )
        )

    return CarouselSpec(
        slides=slide_specs,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        output_format=output_format,
    )


def _require_keys(data: dict[str, Any], keys: list[str]) -> None:
    """Raise ValueError if any required key is missing from data."""
    missing = [k for k in keys if k not in data]
    if missing:
        msg = f"Missing required keys: {', '.join(missing)}"
        raise ValueError(msg)
