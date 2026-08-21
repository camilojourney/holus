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
from dataclasses import dataclass
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
            dots.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{color}" opacity="{opacity:.2f}"/>')
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
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{c}" opacity="{o}"/>'
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


@dataclass(frozen=True)
class _FlowchartLayout:
    """Calculated dimensions for one flowchart layout."""

    is_vertical: bool
    is_grid: bool
    node_width: int
    node_height: int
    gap: int
    svg_width: int
    svg_height: int
    columns: int


def _flowchart_layout(node_count: int, layout: str, width: int) -> _FlowchartLayout:
    is_vertical = layout == "vertical"
    is_grid = layout == "grid"
    node_width = 250 if is_grid else (160 if not is_vertical else 260)
    node_height = 116 if is_grid else (126 if not is_vertical else 92)
    gap = 28 if is_grid else (24 if not is_vertical else 56)
    columns = 3 if node_count > 3 else node_count

    if is_grid:
        rows = (node_count + columns - 1) // columns
        svg_width = width
        svg_height = rows * node_height + (rows - 1) * gap + 80
    elif is_vertical:
        svg_width = width
        svg_height = node_count * node_height + (node_count - 1) * gap + 80
    else:
        total_width = node_count * (node_width + gap) - gap + 80
        svg_width = max(width, total_width)
        svg_height = 190

    return _FlowchartLayout(
        is_vertical=is_vertical,
        is_grid=is_grid,
        node_width=node_width,
        node_height=node_height,
        gap=gap,
        svg_width=svg_width,
        svg_height=svg_height,
        columns=columns,
    )


def _flowchart_positions(
    nodes: list[dict[str, str]], layout: _FlowchartLayout
) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    for index, node in enumerate(nodes):
        if layout.is_grid:
            total_width = layout.columns * layout.node_width + (layout.columns - 1) * layout.gap
            start_x = (layout.svg_width - total_width) / 2
            col = index % layout.columns
            row = index // layout.columns
            cx = start_x + col * (layout.node_width + layout.gap) + layout.node_width / 2
            cy = 40 + row * (layout.node_height + layout.gap) + layout.node_height / 2
        elif layout.is_vertical:
            cx = layout.svg_width / 2
            cy = 40 + index * (layout.node_height + layout.gap) + layout.node_height / 2
        else:
            cx = 40 + index * (layout.node_width + layout.gap) + layout.node_width / 2
            cy = layout.svg_height / 2
        positions[node["id"]] = (cx, cy)
    return positions


def _flowchart_marker(edge_color: str) -> str:
    return (
        "<defs>"
        f'<marker id="fc-arrow" viewBox="0 0 10 10" refX="10" refY="5" '
        f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{edge_color}"/>'
        "</marker>"
        "</defs>"
    )


def _flowchart_edge_elements(
    edges: list[dict[str, str]],
    positions: dict[str, tuple[float, float]],
    layout: _FlowchartLayout,
    edge_color: str,
) -> list[str]:
    if layout.is_grid:
        # The grid layout reads by number; connector lines add clutter at thumbnail size.
        return []

    elements: list[str] = []
    for edge in edges:
        from_id = edge.get("from_id", "")
        to_id = edge.get("to_id", "")
        if from_id not in positions or to_id not in positions:
            continue
        fx, fy = positions[from_id]
        tx, ty = positions[to_id]
        if layout.is_vertical:
            y1 = fy + layout.node_height / 2
            y2 = ty - layout.node_height / 2
            elements.append(
                f'<line x1="{fx}" y1="{y1}" x2="{tx}" y2="{y2}" '
                f'stroke="{edge_color}" stroke-width="4" '
                f'marker-end="url(#fc-arrow)"/>'
            )
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
            x1 = fx + layout.node_width / 2
            x2 = tx - layout.node_width / 2
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
    return elements


def _flowchart_node_elements(
    nodes: list[dict[str, str]],
    positions: dict[str, tuple[float, float]],
    layout: _FlowchartLayout,
    node_color: str,
    text_color: str,
    bg_color: str,
) -> list[str]:
    elements: list[str] = []
    label_width = 20 if layout.is_grid else (14 if not layout.is_vertical else 24)
    for node in nodes:
        nid = node["id"]
        label = node.get("label", nid)
        desc = node.get("description", "")
        cx, cy = positions[nid]
        rx = cx - layout.node_width / 2
        ry = cy - layout.node_height / 2

        elements.append(
            f'<rect x="{rx}" y="{ry}" width="{layout.node_width}" height="{layout.node_height}" '
            f'rx="16" fill="{bg_color}" stroke="{node_color}" stroke-width="2"/>'
        )
        elements.append(
            f'<circle cx="{rx + 24}" cy="{ry + 24}" r="14" fill="{node_color}" opacity="0.14"/>'
        )
        elements.append(
            f'<text x="{rx + 24}" y="{ry + 25}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{node_color}" '
            f'font-size="14" font-weight="850" font-family="Inter, sans-serif">'
            f"{_escape_xml(nid)}</text>"
        )

        label_lines = _wrap_text_lines(label, label_width)
        start_y = cy - (len(label_lines[:3]) - 1) * 13
        for line_index, line in enumerate(label_lines[:3]):
            elements.append(
                f'<text x="{cx}" y="{start_y + line_index * 26}" text-anchor="middle" '
                f'dominant-baseline="middle" fill="{text_color}" '
                f'font-size="22" font-weight="800" '
                f'font-family="Inter, sans-serif">'
                f"{_escape_xml(line)}</text>"
            )

        if desc:
            desc_lines = _wrap_text_lines(desc, 28)
            for line_index, line in enumerate(desc_lines[:2]):
                elements.append(
                    f'<text x="{cx}" y="{cy + 12 + line_index * 16}" text-anchor="middle" '
                    f'dominant-baseline="middle" fill="{text_color}" '
                    f'font-size="12" opacity="0.7" '
                    f'font-family="var(--brand-font-secondary)">'
                    f"{_escape_xml(line)}</text>"
                )
    return elements


def flowchart_svg(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    *,
    layout: str = "vertical",
    width: int = 940,
    node_color: str = "#2563eb",
    edge_color: str = "#94a3b8",
    text_color: str = "#111827",
    bg_color: str = "#ffffff",
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

    flow_layout = _flowchart_layout(len(nodes), layout, width)
    positions = _flowchart_positions(nodes, flow_layout)

    elements: list[str] = [_flowchart_marker(edge_color)]
    elements.extend(_flowchart_edge_elements(edges, positions, flow_layout, edge_color))

    elements.extend(
        _flowchart_node_elements(
            nodes,
            positions,
            flow_layout,
            node_color,
            text_color,
            bg_color,
        )
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {flow_layout.svg_width} {flow_layout.svg_height}" '
        f'width="{flow_layout.svg_width}" height="{flow_layout.svg_height}" '
        f'role="img" aria-label="Flowchart">'
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
    header_color: str = "#b45309",
    text_color: str = "#111827",
    divider_color: str = "#d1d5db",
    row_even_color: str = "#ffffff",
    row_odd_color: str = "#f8fafc",
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

    row_h = 102
    header_h = 82
    padding = 24
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
        f'rx="18" fill="#fffbeb" stroke="#fde68a" stroke-width="2"/>'
    )
    elements.append(
        f'<text x="{left_cx}" y="{header_h / 2}" text-anchor="middle" '
        f'dominant-baseline="middle" fill="{header_color}" '
        f'font-size="30" font-weight="850" '
        f'font-family="var(--brand-font-primary)">'
        f"{_escape_xml(left_label)}</text>"
    )
    elements.append(
        f'<text x="{dim_cx}" y="{header_h / 2}" text-anchor="middle" '
        f'dominant-baseline="middle" fill="{text_color}" '
        f'font-size="18" font-weight="800" opacity="0.55" '
        f'font-family="var(--brand-font-secondary)">'
        f"VS</text>"
    )
    elements.append(
        f'<text x="{right_cx}" y="{header_h / 2}" text-anchor="middle" '
        f'dominant-baseline="middle" fill="{header_color}" '
        f'font-size="30" font-weight="850" '
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
            f'<rect x="0" y="{y + 8}" width="{width}" height="{row_h - 12}" '
            f'rx="16" fill="{bg}" stroke="#e5e7eb" stroke-width="1"/>'
        )

        # Dimension label (center)
        elements.append(
            f'<text x="{dim_cx}" y="{y + row_h / 2}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{text_color}" '
            f'font-size="24" font-weight="850" opacity="0.86" '
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
            f'font-size="25" font-weight="800" font-family="Inter, sans-serif">'
            f"{_escape_xml(left_val)}</text>"
        )
        elements.append(
            f'<text x="{right_text_x}" y="{y + row_h / 2}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{text_color}" '
            f'font-size="25" font-weight="800" font-family="Inter, sans-serif">'
            f"{_escape_xml(right_val)}</text>"
        )

        # Winner/loser indicators
        # Check mark: Unicode ✓ | X mark: Unicode ✗
        mark_y = y + row_h / 2
        if winner == "left":
            elements.append(
                f'<text x="{left_col_end - indicator_offset}" y="{mark_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{winner_color}" font-size="30" font-weight="850">'
                f"&#x2713;</text>"
            )
            elements.append(
                f'<text x="{right_col_start + indicator_offset}" y="{mark_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{loser_color}" font-size="28" opacity="0.35">'
                f"&#x2717;</text>"
            )
        elif winner == "right":
            elements.append(
                f'<text x="{left_col_end - indicator_offset}" y="{mark_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{loser_color}" font-size="28" opacity="0.35">'
                f"&#x2717;</text>"
            )
            elements.append(
                f'<text x="{right_col_start + indicator_offset}" y="{mark_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="{winner_color}" font-size="30" font-weight="850">'
                f"&#x2713;</text>"
            )
        # tie: no indicators

    # Center divider lines
    elements.append(
        f'<line x1="{dim_start}" y1="0" x2="{dim_start}" y2="{total_h}" '
        f'stroke="{divider_color}" stroke-width="1" opacity="0.7"/>'
    )
    elements.append(
        f'<line x1="{dim_end}" y1="0" x2="{dim_end}" y2="{total_h}" '
        f'stroke="{divider_color}" stroke-width="1" opacity="0.7"/>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total_h}" '
        f'width="{width}" height="{total_h}" role="img" '
        f'aria-label="Comparison table: {_escape_xml(left_label)} vs '
        f'{_escape_xml(right_label)}">'
        f"{''.join(elements)}"
        f"</svg>"
    )
