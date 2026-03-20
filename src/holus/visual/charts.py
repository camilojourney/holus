"""Inline SVG chart generators for carousel slides.

All functions return raw SVG strings (no external dependencies).
Charts use brand CSS custom properties for colors so they adapt to themes.

Usage::

    from holus.visual.charts import sparkline_svg, bar_chart_svg, decorative_svg

    svg = sparkline_svg([10, 30, 25, 45, 40, 60, 55, 70])
    svg = bar_chart_svg({"ML": 73, "NLP": 58, "CV": 42})
    svg = decorative_svg("circles")
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Sparkline — tiny line chart for stat slides
# ---------------------------------------------------------------------------


def sparkline_svg(
    values: list[float | int],
    *,
    width: int = 400,
    height: int = 80,
    stroke_color: str = "var(--brand-color-primary)",
    fill_color: str = "var(--brand-color-primary)",
    stroke_width: float = 2.5,
) -> str:
    """Generate a sparkline SVG from a list of numeric values.

    Returns a minimal SVG string with a polyline and optional gradient fill.
    """
    if not values or len(values) < 2:
        return ""

    lo = min(values)
    hi = max(values)
    spread = hi - lo if hi != lo else 1.0
    pad = 4

    points: list[str] = []
    for i, v in enumerate(values):
        x = pad + (i / (len(values) - 1)) * (width - 2 * pad)
        y = pad + (1 - (v - lo) / spread) * (height - 2 * pad)
        points.append(f"{x:.1f},{y:.1f}")

    polyline = " ".join(points)
    # Fill area: close path at bottom
    fill_points = f"{pad},{height - pad} {polyline} {width - pad},{height - pad}"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="Sparkline chart">'
        f"<defs>"
        f'<linearGradient id="spark-fill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{fill_color}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{fill_color}" stop-opacity="0.02"/>'
        f"</linearGradient>"
        f"</defs>"
        f'<polygon points="{fill_points}" fill="url(#spark-fill)"/>'
        f'<polyline points="{polyline}" fill="none" '
        f'stroke="{stroke_color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# Bar chart — horizontal bars for data slides
# ---------------------------------------------------------------------------


def bar_chart_svg(
    data: dict[str, float | int],
    *,
    width: int = 600,
    bar_height: int = 36,
    gap: int = 16,
    bar_color: str = "var(--brand-color-primary)",
    label_color: str = "var(--brand-color-text)",
    value_color: str = "var(--brand-color-muted)",
) -> str:
    """Generate a horizontal bar chart SVG from label→value pairs.

    Bars are scaled relative to the maximum value.
    """
    if not data:
        return ""

    max_val = max(data.values()) or 1
    n = len(data)
    label_width = 120
    value_width = 60
    chart_width = width - label_width - value_width - 20
    height = n * (bar_height + gap) - gap + 20

    bars: list[str] = []
    for i, (label, value) in enumerate(data.items()):
        y = i * (bar_height + gap) + 10
        w = max(4, (value / max_val) * chart_width)

        # Label
        bars.append(
            f'<text x="{label_width - 12}" y="{y + bar_height / 2 + 5}" '
            f'text-anchor="end" fill="{label_color}" '
            f'font-size="16" font-family="var(--brand-font-primary)">'
            f"{label}</text>"
        )
        # Bar
        bars.append(
            f'<rect x="{label_width}" y="{y}" width="{w:.1f}" '
            f'height="{bar_height}" rx="4" fill="{bar_color}" opacity="0.85"/>'
        )
        # Value
        bars.append(
            f'<text x="{label_width + w + 10}" y="{y + bar_height / 2 + 5}" '
            f'fill="{value_color}" font-size="14" '
            f'font-family="var(--brand-font-secondary)">'
            f"{value}</text>"
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="Bar chart">'
        f"{''.join(bars)}"
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# Donut chart — percentage ring for stat slides
# ---------------------------------------------------------------------------


def donut_svg(
    percentage: float,
    *,
    size: int = 160,
    stroke_width: int = 14,
    color: str = "var(--brand-color-primary)",
    track_color: str = "rgba(255,255,255,0.08)",
    label: str = "",
) -> str:
    """Generate a donut/ring chart showing a percentage."""
    r = (size - stroke_width) / 2
    cx = cy = size / 2
    circumference = 2 * math.pi * r
    dash = (percentage / 100) * circumference
    gap = circumference - dash

    label_el = ""
    if label:
        label_el = (
            f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" '
            f'fill="var(--brand-color-text)" font-size="28" '
            f'font-weight="700" font-family="var(--brand-font-primary)">'
            f"{label}</text>"
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" role="img" aria-label="Donut chart {percentage}%">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
        f'stroke="{track_color}" stroke-width="{stroke_width}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-dasharray="{dash:.1f} {gap:.1f}" '
        f'stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>'
        f"{label_el}"
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# Decorative SVG — abstract patterns for split slides
# ---------------------------------------------------------------------------

_PATTERN_REGISTRY: dict[str, Any] = {}


def _register(name: str) -> Callable[..., Any]:
    def decorator(fn: Callable[..., str]) -> Callable[..., str]:
        _PATTERN_REGISTRY[name] = name
        _PATTERN_REGISTRY[f"_fn_{name}"] = fn
        return fn
    return decorator


@_register("circles")
def _circles(
    primary: str = "var(--brand-color-primary)",
    accent: str = "var(--brand-color-accent)",
) -> str:
    """Overlapping circles — modern, tech feel."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" '
        'width="400" height="500" role="img" aria-label="Decorative circles">'
        f'<circle cx="200" cy="180" r="140" fill="{primary}" opacity="0.15"/>'
        f'<circle cx="260" cy="260" r="100" fill="{accent}" opacity="0.12"/>'
        f'<circle cx="150" cy="320" r="80" fill="{primary}" opacity="0.1"/>'
        f'<circle cx="300" cy="380" r="60" fill="{accent}" opacity="0.08"/>'
        f'<circle cx="200" cy="180" r="140" fill="none" stroke="{primary}" '
        f'stroke-width="1" opacity="0.25"/>'
        "</svg>"
    )


@_register("grid")
def _grid(
    color: str = "var(--brand-color-primary)",
) -> str:
    """Dot grid pattern — clean, structured."""
    dots: list[str] = []
    for row in range(12):
        for col in range(8):
            x = 25 + col * 50
            y = 25 + row * 42
            opacity = 0.06 + (row * 0.02)
            dots.append(
                f'<circle cx="{x}" cy="{y}" r="3" fill="{color}" opacity="{opacity:.2f}"/>'
            )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" '
        'width="400" height="500" role="img" aria-label="Decorative grid">'
        f"{''.join(dots)}"
        "</svg>"
    )


@_register("waves")
def _waves(
    color: str = "var(--brand-color-primary)",
) -> str:
    """Flowing wave lines — organic, fluid."""
    paths: list[str] = []
    for i in range(6):
        y_base = 80 + i * 70
        opacity = 0.08 + i * 0.03
        d = (
            f"M0,{y_base} "
            f"C100,{y_base - 30} 200,{y_base + 30} 300,{y_base} "
            f"S400,{y_base + 20} 400,{y_base}"
        )
        paths.append(
            f'<path d="{d}" fill="none" stroke="{color}" '
            f'stroke-width="1.5" opacity="{opacity:.2f}"/>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" '
        'width="400" height="500" role="img" aria-label="Decorative waves">'
        f"{''.join(paths)}"
        "</svg>"
    )


@_register("blocks")
def _blocks(
    primary: str = "var(--brand-color-primary)",
    accent: str = "var(--brand-color-accent)",
) -> str:
    """Scattered rounded rectangles — modern, geometric."""
    rects = [
        (40, 60, 120, 80, primary, 0.12),
        (200, 30, 80, 120, accent, 0.1),
        (100, 200, 160, 60, primary, 0.08),
        (60, 320, 100, 100, accent, 0.1),
        (220, 280, 140, 80, primary, 0.06),
        (160, 400, 120, 70, accent, 0.09),
    ]
    elements = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
        f'fill="{c}" opacity="{o}"/>'
        for x, y, w, h, c, o in rects
    ]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" '
        'width="400" height="500" role="img" aria-label="Decorative blocks">'
        f"{''.join(elements)}"
        "</svg>"
    )


def decorative_svg(pattern: str = "circles") -> str:
    """Get a decorative SVG by pattern name.

    Available: circles, grid, waves, blocks.
    Falls back to circles if unknown.
    """
    fn_key = f"_fn_{pattern}"
    if fn_key in _PATTERN_REGISTRY:
        result: str = _PATTERN_REGISTRY[fn_key]()
        return result
    fallback: str = _PATTERN_REGISTRY["_fn_circles"]()
    return fallback


def list_patterns() -> list[str]:
    """List available decorative pattern names."""
    return [k for k in _PATTERN_REGISTRY if not k.startswith("_fn_")]
