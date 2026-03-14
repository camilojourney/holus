"""Pure-Python SVG chart generation for the visual pipeline."""

from __future__ import annotations

from html import escape

_MUTED_COLOR = "#94a3b8"
_SVG_WIDTH = 800
_SVG_HEIGHT = 400


def _validate_color(color: str) -> str:
    """Strip and validate a CSS color string. Returns the color unchanged if valid."""
    stripped = color.strip()
    if not stripped:
        return "#6366f1"
    return stripped


def generate_svg(
    chart_type: str,
    labels: list[str],
    values: list[str],
    highlight_index: int | None = None,
    color_accent: str = "#6366f1",
) -> str:
    """Generate an inline SVG string for the requested chart type."""
    if chart_type not in {"bar", "line", "metric"}:
        msg = "chart_type must be one of: bar, line, metric"
        raise ValueError(msg)

    if highlight_index is not None and not (0 <= highlight_index < len(labels)):
        msg = f"highlight_index {highlight_index} out of range for {len(labels)} data points"
        raise ValueError(msg)

    if len(labels) != len(values) or not labels:
        msg = "labels and values must be non-empty lists of the same length"
        raise ValueError(msg)

    if any(not str(label).strip() for label in labels):
        msg = "labels must not contain empty strings"
        raise ValueError(msg)
    if any(not str(value).strip() for value in values):
        msg = "values must not contain empty strings"
        raise ValueError(msg)

    color_accent = _validate_color(color_accent)

    if chart_type == "metric":
        return _generate_metric_svg(values[0], labels[0], color_accent)

    numeric_values = [_parse_numeric(value) for value in values]
    if chart_type == "bar":
        return _generate_bar_svg(labels, values, numeric_values, highlight_index, color_accent)
    return _generate_line_svg(labels, values, numeric_values, highlight_index, color_accent)


def _generate_bar_svg(
    labels: list[str],
    raw_values: list[str],
    numeric_values: list[float],
    highlight_index: int | None,
    color_accent: str,
) -> str:
    max_value = max(numeric_values) or 1.0
    chart_left = 90.0
    chart_top = 56.0
    chart_bottom = 310.0
    chart_height = chart_bottom - chart_top
    slot_width = 620.0 / len(labels)
    bar_width = min(76.0, slot_width * 0.58)
    axis_y = chart_bottom

    parts = [_svg_open(), _background_panel(), _chart_title("Bar Chart")]
    parts.append(
        f'<line x1="{chart_left}" y1="{axis_y}" x2="730" y2="{axis_y}" '
        'stroke="#334155" stroke-width="2" />'
    )

    for index, (label, raw_value, numeric_value) in enumerate(zip(labels, raw_values, numeric_values, strict=True)):
        height = 0.0 if max_value == 0 else (numeric_value / max_value) * chart_height
        x = chart_left + slot_width * index + (slot_width - bar_width) / 2
        y = axis_y - height
        fill = color_accent if highlight_index == index else _MUTED_COLOR
        text_x = x + (bar_width / 2)

        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{height:.2f}" '
            f'rx="12" fill="{escape(fill)}" />'
        )
        parts.append(
            f'<text x="{text_x:.2f}" y="{max(36.0, y - 12):.2f}" text-anchor="middle" '
            'font-family="Inter, sans-serif" font-size="18" font-weight="700" fill="#e2e8f0">'
            f"{escape(raw_value)}</text>"
        )
        parts.append(
            f'<text x="{text_x:.2f}" y="344" text-anchor="middle" '
            'font-family="Inter, sans-serif" font-size="16" fill="#94a3b8">'
            f"{escape(label)}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)


def _generate_line_svg(
    labels: list[str],
    raw_values: list[str],
    numeric_values: list[float],
    highlight_index: int | None,
    color_accent: str,
) -> str:
    max_value = max(numeric_values) or 1.0
    min_value = min(numeric_values)
    chart_left = 90.0
    chart_top = 72.0
    chart_bottom = 286.0
    chart_height = chart_bottom - chart_top
    chart_width = 620.0
    axis_y = 320.0
    point_count = len(labels)
    denominator = max(1, point_count - 1)

    def y_position(value: float) -> float:
        if max_value == min_value:
            return chart_top + (chart_height / 2)
        normalized = (value - min_value) / (max_value - min_value)
        return chart_bottom - (normalized * chart_height)

    points: list[tuple[float, float]] = []
    for index, numeric_value in enumerate(numeric_values):
        x = chart_left + (chart_width * index / denominator)
        points.append((x, y_position(numeric_value)))

    polyline_points = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)

    parts = [_svg_open(), _background_panel(), _chart_title("Line Chart")]
    parts.append(
        f'<line x1="{chart_left}" y1="{axis_y}" x2="730" y2="{axis_y}" '
        'stroke="#334155" stroke-width="2" />'
    )
    parts.append(
        f'<polyline points="{polyline_points}" fill="none" stroke="{escape(color_accent)}" '
        'stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />'
    )

    for index, ((x, y), label, raw_value) in enumerate(zip(points, labels, raw_values, strict=True)):
        fill = color_accent if highlight_index == index else _MUTED_COLOR
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="8" fill="{escape(fill)}" stroke="#0f172a" stroke-width="3" />'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{max(36.0, y - 14):.2f}" text-anchor="middle" '
            'font-family="Inter, sans-serif" font-size="18" font-weight="700" fill="#e2e8f0">'
            f"{escape(raw_value)}</text>"
        )
        parts.append(
            f'<text x="{x:.2f}" y="356" text-anchor="middle" '
            'font-family="Inter, sans-serif" font-size="16" fill="#94a3b8">'
            f"{escape(label)}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)


def _generate_metric_svg(value_text: str, subtitle: str, color_accent: str) -> str:
    return (
        f'{_svg_open()}'
        f"{_background_panel()}"
        '<text x="400" y="170" text-anchor="middle" font-family="Inter, sans-serif" '
        f'font-size="120" font-weight="800" fill="{escape(color_accent)}">{escape(value_text)}</text>'
        '<text x="400" y="238" text-anchor="middle" font-family="Inter, sans-serif" '
        f'font-size="28" fill="#cbd5e1">{escape(subtitle)}</text>'
        '<line x1="280" y1="268" x2="520" y2="268" stroke="#334155" stroke-width="2" />'
        "</svg>"
    )


def _svg_open() -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" '
        'width="800" height="400" role="img" aria-label="Generated chart">'
    )


def _background_panel() -> str:
    return (
        f'<rect x="0" y="0" width="{_SVG_WIDTH}" height="{_SVG_HEIGHT}" rx="28" fill="#020617" />'
        '<rect x="24" y="24" width="752" height="352" rx="24" fill="#0f172a" '
        'stroke="#1e293b" stroke-width="2" />'
    )


def _chart_title(title: str) -> str:
    return (
        '<text x="48" y="58" font-family="Inter, sans-serif" font-size="20" '
        f'font-weight="600" fill="#94a3b8">{escape(title)}</text>'
    )


def _parse_numeric(value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        msg = f"value {value!r} is not numeric"
        raise ValueError(msg) from exc
