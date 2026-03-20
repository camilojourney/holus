"""Inline SVG chart generators for carousel slides.

All functions return raw SVG strings (no external dependencies).
Charts use brand CSS custom properties for colors so they adapt to themes.

Usage::

    from holus.visual.charts import sparkline_svg, bar_chart_svg, decorative_svg
    from holus.visual.charts import flowchart_svg, architecture_svg, comparison_table_svg

    svg = sparkline_svg([10, 30, 25, 45, 40, 60, 55, 70])
    svg = bar_chart_svg({"ML": 73, "NLP": 58, "CV": 42})
    svg = decorative_svg("circles")
    svg = flowchart_svg(nodes=[...], edges=[...])
    svg = architecture_svg(layers=[...], connections=[...])
    svg = comparison_table_svg(items=[...], left_label="A", right_label="B")
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


# ---------------------------------------------------------------------------
# Flowchart — node-and-edge diagram for process/decision slides
# ---------------------------------------------------------------------------


def _escape_xml(text: str) -> str:
    """Escape text for safe embedding in SVG/XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _wrap_text_lines(text: str, max_chars: int = 30) -> list[str]:
    """Split text into lines that fit within a given character width."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines or [""]


def flowchart_svg(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    *,
    layout: str = "vertical",
    width: int = 900,
    node_color: str = "var(--brand-color-primary)",
    edge_color: str = "var(--brand-color-accent)",
    text_color: str = "var(--brand-color-text)",
    bg_color: str = "var(--brand-color-surface)",
) -> str:
    """Generate a flowchart SVG with connected nodes.

    Args:
        nodes: List of dicts with keys ``id``, ``label``, ``description``.
        edges: List of dicts with keys ``from_id``, ``to_id``, and optional ``label``.
        layout: ``"vertical"`` (top-to-bottom) or ``"horizontal"`` (left-to-right).
        width: SVG width in pixels.
        node_color: Fill color for node boxes.
        edge_color: Color for edge lines and arrowheads.
        text_color: Color for text inside nodes.
        bg_color: Background color for node boxes.

    Returns:
        Raw SVG string.
    """
    if not nodes:
        return ""

    n = len(nodes)
    is_vertical = layout == "vertical"

    # Node sizing
    node_w = 220
    node_h = 80
    gap = 60

    if is_vertical:
        total_h = n * node_h + (n - 1) * gap + 80
        svg_w = width
        svg_h = total_h
    else:
        total_w = n * (node_w + gap) - gap + 80
        svg_w = max(width, total_w)
        svg_h = 260

    # Build id→position map
    positions: dict[str, tuple[float, float]] = {}
    for i, node in enumerate(nodes):
        if is_vertical:
            cx = svg_w / 2
            cy = 40 + i * (node_h + gap) + node_h / 2
        else:
            cx = 40 + i * (node_w + gap) + node_w / 2
            cy = svg_h / 2
        positions[node["id"]] = (cx, cy)

    # Arrowhead marker
    marker = (
        "<defs>"
        f'<marker id="fc-arrow" viewBox="0 0 10 10" refX="10" refY="5" '
        f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{edge_color}"/>'
        "</marker>"
        "</defs>"
    )

    elements: list[str] = [marker]

    # Draw edges first (behind nodes)
    for edge in edges:
        from_id = edge.get("from_id", "")
        to_id = edge.get("to_id", "")
        if from_id not in positions or to_id not in positions:
            continue
        fx, fy = positions[from_id]
        tx, ty = positions[to_id]

        if is_vertical:
            y1 = fy + node_h / 2
            y2 = ty - node_h / 2
            elements.append(
                f'<line x1="{fx}" y1="{y1}" x2="{tx}" y2="{y2}" '
                f'stroke="{edge_color}" stroke-width="2" '
                f'marker-end="url(#fc-arrow)"/>'
            )
            # Edge label
            edge_label = edge.get("label", "")
            if edge_label:
                mid_y = (y1 + y2) / 2
                mid_x = (fx + tx) / 2 + 12
                elements.append(
                    f'<text x="{mid_x}" y="{mid_y}" fill="{edge_color}" '
                    f'font-size="12" font-family="var(--brand-font-secondary)" '
                    f'dominant-baseline="middle">'
                    f"{_escape_xml(edge_label)}</text>"
                )
        else:
            x1 = fx + node_w / 2
            x2 = tx - node_w / 2
            elements.append(
                f'<line x1="{x1}" y1="{fy}" x2="{x2}" y2="{ty}" '
                f'stroke="{edge_color}" stroke-width="2" '
                f'marker-end="url(#fc-arrow)"/>'
            )
            edge_label = edge.get("label", "")
            if edge_label:
                mid_x = (x1 + x2) / 2
                mid_y = (fy + ty) / 2 - 10
                elements.append(
                    f'<text x="{mid_x}" y="{mid_y}" fill="{edge_color}" '
                    f'font-size="12" font-family="var(--brand-font-secondary)" '
                    f'text-anchor="middle">'
                    f"{_escape_xml(edge_label)}</text>"
                )

    # Draw nodes
    for node in nodes:
        nid = node["id"]
        label = node.get("label", nid)
        desc = node.get("description", "")
        cx, cy = positions[nid]
        rx = cx - node_w / 2
        ry = cy - node_h / 2

        # Node box
        elements.append(
            f'<rect x="{rx}" y="{ry}" width="{node_w}" height="{node_h}" '
            f'rx="12" fill="{bg_color}" stroke="{node_color}" stroke-width="2"/>'
        )
        # Label
        elements.append(
            f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{text_color}" '
            f'font-size="16" font-weight="700" '
            f'font-family="var(--brand-font-primary)">'
            f"{_escape_xml(label)}</text>"
        )
        # Description (smaller, below label)
        if desc:
            desc_lines = _wrap_text_lines(desc, 28)
            for li, line in enumerate(desc_lines[:2]):
                elements.append(
                    f'<text x="{cx}" y="{cy + 12 + li * 16}" text-anchor="middle" '
                    f'dominant-baseline="middle" fill="{text_color}" '
                    f'font-size="12" opacity="0.7" '
                    f'font-family="var(--brand-font-secondary)">'
                    f"{_escape_xml(line)}</text>"
                )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}" role="img" aria-label="Flowchart">'
        f"{''.join(elements)}"
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# Architecture diagram — layered component view
# ---------------------------------------------------------------------------


def architecture_svg(
    layers: list[dict[str, Any]],
    connections: list[dict[str, int]],
    *,
    width: int = 900,
    layer_color: str = "var(--brand-color-surface)",
    comp_color: str = "var(--brand-color-primary)",
    text_color: str = "var(--brand-color-text)",
) -> str:
    """Generate an architecture diagram SVG with stacked layers and components.

    Args:
        layers: List of dicts with ``name`` (str) and ``components``
            (list of dicts with ``name`` and optional ``description``).
        connections: List of dicts with ``from_layer``, ``from_comp``,
            ``to_layer``, ``to_comp`` (zero-based indices).
        width: SVG width in pixels.
        layer_color: Background color for layer bands.
        comp_color: Fill/stroke color for component boxes.
        text_color: Color for all text.

    Returns:
        Raw SVG string.
    """
    if not layers:
        return ""

    padding = 40
    layer_gap = 30
    layer_label_h = 28
    comp_h = 56
    comp_gap = 20
    layer_pad = 16
    layer_h = layer_label_h + comp_h + layer_pad * 2 + 8

    n_layers = len(layers)
    total_h = padding * 2 + n_layers * layer_h + (n_layers - 1) * layer_gap

    # Pre-compute component positions: comp_positions[layer_idx][comp_idx] = (cx, cy)
    comp_positions: dict[tuple[int, int], tuple[float, float]] = {}
    elements: list[str] = []

    for li, layer in enumerate(layers):
        comps = layer.get("components", [])
        n_comps = max(len(comps), 1)
        layer_y = padding + li * (layer_h + layer_gap)

        # Layer background band
        elements.append(
            f'<rect x="{padding}" y="{layer_y}" '
            f'width="{width - padding * 2}" height="{layer_h}" '
            f'rx="10" fill="{layer_color}" opacity="0.5"/>'
        )
        # Layer name
        layer_name = _escape_xml(layer.get("name", f"Layer {li + 1}"))
        elements.append(
            f'<text x="{padding + layer_pad}" y="{layer_y + layer_pad + 14}" '
            f'fill="{text_color}" font-size="14" font-weight="700" '
            f'font-family="var(--brand-font-primary)" opacity="0.6" '
            f'text-transform="uppercase" letter-spacing="0.08em">'
            f"{layer_name}</text>"
        )

        # Components within layer
        usable_w = width - padding * 2 - layer_pad * 2
        comp_w = (usable_w - (n_comps - 1) * comp_gap) / n_comps
        comp_w = min(comp_w, 240)
        total_comps_w = n_comps * comp_w + (n_comps - 1) * comp_gap
        start_x = padding + layer_pad + (usable_w - total_comps_w) / 2

        comp_y = layer_y + layer_label_h + layer_pad + 8
        for ci, comp in enumerate(comps):
            cx = start_x + ci * (comp_w + comp_gap) + comp_w / 2
            cy = comp_y + comp_h / 2
            comp_positions[(li, ci)] = (cx, cy)

            comp_x = cx - comp_w / 2
            # Component box
            elements.append(
                f'<rect x="{comp_x}" y="{comp_y}" '
                f'width="{comp_w}" height="{comp_h}" '
                f'rx="8" fill="none" stroke="{comp_color}" stroke-width="2"/>'
            )
            # Component name
            comp_name = _escape_xml(comp.get("name", ""))
            elements.append(
                f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" '
                f'dominant-baseline="middle" fill="{text_color}" '
                f'font-size="14" font-weight="600" '
                f'font-family="var(--brand-font-primary)">'
                f"{comp_name}</text>"
            )
            # Component description
            comp_desc = comp.get("description", "")
            if comp_desc:
                desc_lines = _wrap_text_lines(comp_desc, int(comp_w / 7))
                for di, dline in enumerate(desc_lines[:1]):
                    elements.append(
                        f'<text x="{cx}" y="{cy + 14 + di * 14}" '
                        f'text-anchor="middle" dominant-baseline="middle" '
                        f'fill="{text_color}" font-size="11" opacity="0.6" '
                        f'font-family="var(--brand-font-secondary)">'
                        f"{_escape_xml(dline)}</text>"
                    )

    # Draw connections (dashed lines between components in different layers)
    for conn in connections:
        from_key = (conn.get("from_layer", 0), conn.get("from_comp", 0))
        to_key = (conn.get("to_layer", 0), conn.get("to_comp", 0))
        if from_key not in comp_positions or to_key not in comp_positions:
            continue
        fx, fy = comp_positions[from_key]
        tx, ty = comp_positions[to_key]

        # Adjust endpoints to box edges
        if fy < ty:
            fy += comp_h / 2
            ty -= comp_h / 2
        else:
            fy -= comp_h / 2
            ty += comp_h / 2

        elements.append(
            f'<line x1="{fx}" y1="{fy}" x2="{tx}" y2="{ty}" '
            f'stroke="{comp_color}" stroke-width="1.5" '
            f'stroke-dasharray="6 4" opacity="0.5"/>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total_h}" '
        f'width="{width}" height="{total_h}" role="img" '
        f'aria-label="Architecture diagram">'
        f"{''.join(elements)}"
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# Comparison table — two-column comparison with winner indicators
# ---------------------------------------------------------------------------


def comparison_table_svg(
    items: list[dict[str, str]],
    left_label: str,
    right_label: str,
    *,
    width: int = 900,
    header_color: str = "var(--brand-color-primary)",
    text_color: str = "var(--brand-color-text)",
    divider_color: str = "var(--brand-color-accent)",
    row_even_color: str = "rgba(255,255,255,0.03)",
    row_odd_color: str = "rgba(255,255,255,0.06)",
    winner_color: str = "#22c55e",
    loser_color: str = "#ef4444",
) -> str:
    """Generate a comparison table SVG with two columns and winner indicators.

    Args:
        items: List of dicts with ``dimension``, ``left``, ``right``,
            and ``winner`` (one of ``"left"``, ``"right"``, ``"tie"``).
        left_label: Header text for the left column.
        right_label: Header text for the right column.
        width: SVG width in pixels.
        header_color: Color for the header row background and text.
        text_color: Color for body text.
        divider_color: Color for the center vertical divider.
        row_even_color: Background for even rows.
        row_odd_color: Background for odd rows.
        winner_color: Color for the winner check mark.
        loser_color: Color for the loser X mark.

    Returns:
        Raw SVG string.
    """
    if not items:
        return ""

    row_h = 52
    header_h = 56
    padding = 20
    n_rows = len(items)
    total_h = header_h + n_rows * row_h + padding

    center_x = width / 2
    dim_w = 160
    col_w = (width - dim_w) / 2
    left_cx = dim_w / 2 + (col_w / 2) - dim_w / 2 + padding
    right_cx = width - col_w / 2 + dim_w / 2 - padding
    # Recalculate for cleaner layout:
    # |--- left col ---|--- dimension ---|--- right col ---|
    left_col_start = 0
    left_col_end = (width - dim_w) / 2
    dim_start = left_col_end
    dim_end = dim_start + dim_w
    right_col_start = dim_end
    right_col_end = width

    left_cx = left_col_start + (left_col_end - left_col_start) / 2
    right_cx = right_col_start + (right_col_end - right_col_start) / 2
    dim_cx = center_x

    elements: list[str] = []

    # Header row
    elements.append(
        f'<rect x="0" y="0" width="{width}" height="{header_h}" '
        f'rx="8" fill="{header_color}" opacity="0.15"/>'
    )
    elements.append(
        f'<text x="{left_cx}" y="{header_h / 2}" text-anchor="middle" '
        f'dominant-baseline="middle" fill="{header_color}" '
        f'font-size="18" font-weight="700" '
        f'font-family="var(--brand-font-primary)">'
        f"{_escape_xml(left_label)}</text>"
    )
    elements.append(
        f'<text x="{dim_cx}" y="{header_h / 2}" text-anchor="middle" '
        f'dominant-baseline="middle" fill="{text_color}" '
        f'font-size="13" font-weight="600" opacity="0.5" '
        f'font-family="var(--brand-font-secondary)">'
        f"VS</text>"
    )
    elements.append(
        f'<text x="{right_cx}" y="{header_h / 2}" text-anchor="middle" '
        f'dominant-baseline="middle" fill="{header_color}" '
        f'font-size="18" font-weight="700" '
        f'font-family="var(--brand-font-primary)">'
        f"{_escape_xml(right_label)}</text>"
    )

    # Data rows
    for i, item in enumerate(items):
        y = header_h + i * row_h
        bg = row_even_color if i % 2 == 0 else row_odd_color
        dimension = item.get("dimension", "")
        left_val = item.get("left", "")
        right_val = item.get("right", "")
        winner = item.get("winner", "tie")

        # Row background
        elements.append(
            f'<rect x="0" y="{y}" width="{width}" height="{row_h}" '
            f'fill="{bg}"/>'
        )

        # Dimension label (center)
        elements.append(
            f'<text x="{dim_cx}" y="{y + row_h / 2}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{text_color}" '
            f'font-size="13" font-weight="600" opacity="0.7" '
            f'font-family="var(--brand-font-secondary)">'
            f"{_escape_xml(dimension)}</text>"
        )

        # Left value + indicator
        indicator_offset = 22
        left_text_x = left_cx
        right_text_x = right_cx

        elements.append(
            f'<text x="{left_text_x}" y="{y + row_h / 2}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{text_color}" '
            f'font-size="14" font-family="var(--brand-font-primary)">'
            f"{_escape_xml(left_val)}</text>"
        )
        elements.append(
            f'<text x="{right_text_x}" y="{y + row_h / 2}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{text_color}" '
            f'font-size="14" font-family="var(--brand-font-primary)">'
            f"{_escape_xml(right_val)}</text>"
        )

        # Winner/loser indicators
        # Check mark: Unicode ✓ | X mark: Unicode ✗
        mark_y = y + row_h / 2
        if winner == "left":
            elements.append(
                f'<text x="{left_col_end - indicator_offset}" y="{mark_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{winner_color}" font-size="18" font-weight="700">'
                f"&#x2713;</text>"
            )
            elements.append(
                f'<text x="{right_col_start + indicator_offset}" y="{mark_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{loser_color}" font-size="16" opacity="0.4">'
                f"&#x2717;</text>"
            )
        elif winner == "right":
            elements.append(
                f'<text x="{left_col_end - indicator_offset}" y="{mark_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{loser_color}" font-size="16" opacity="0.4">'
                f"&#x2717;</text>"
            )
            elements.append(
                f'<text x="{right_col_start + indicator_offset}" y="{mark_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{winner_color}" font-size="18" font-weight="700">'
                f"&#x2713;</text>"
            )
        # tie: no indicators

    # Center divider lines
    elements.append(
        f'<line x1="{dim_start}" y1="0" x2="{dim_start}" y2="{total_h}" '
        f'stroke="{divider_color}" stroke-width="1" opacity="0.2"/>'
    )
    elements.append(
        f'<line x1="{dim_end}" y1="0" x2="{dim_end}" y2="{total_h}" '
        f'stroke="{divider_color}" stroke-width="1" opacity="0.2"/>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total_h}" '
        f'width="{width}" height="{total_h}" role="img" '
        f'aria-label="Comparison table: {_escape_xml(left_label)} vs '
        f'{_escape_xml(right_label)}">'
        f"{''.join(elements)}"
        f"</svg>"
    )
