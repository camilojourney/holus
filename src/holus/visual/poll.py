"""Pure-Python SVG poll generation for the visual pipeline."""

from __future__ import annotations

from html import escape

_SVG_WIDTH = 800
_SVG_HEIGHT = 500
_BAR_WIDTH = 680
_BAR_HEIGHT = 56
_BAR_X = 60
_BARS_TOP = 186
_BARS_BOTTOM = 452


def _validate_color(color: str) -> str:
    stripped = color.strip()
    return stripped if stripped else "#6366f1"


def generate_poll_svg(
    question: str,
    options: list[str],
    color_accent: str = "#6366f1",
) -> str:
    """Generate an SVG poll graphic (800x500 viewBox)."""
    if not question or not question.strip():
        msg = "question must be a non-empty string"
        raise ValueError(msg)

    if not 2 <= len(options) <= 4:
        msg = "options must contain between 2 and 4 items"
        raise ValueError(msg)

    if any(not str(option).strip() for option in options):
        msg = "poll options must not contain empty strings"
        raise ValueError(msg)

    safe_color = escape(_validate_color(color_accent))
    safe_options = [escape(option) for option in options]
    question_lines = _wrap_text(question, max_chars=26)
    question_y = 88 - ((len(question_lines) - 1) * 20)

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" '
        'width="800" height="500" role="img" aria-label="Generated poll graphic">',
        f'<rect x="0" y="0" width="{_SVG_WIDTH}" height="{_SVG_HEIGHT}" rx="32" fill="#020617" />',
        '<rect x="24" y="24" width="752" height="452" rx="28" fill="#0f172a" '
        'stroke="#1e293b" stroke-width="2" />',
        '<text x="400" y="52" text-anchor="middle" font-family="Inter, sans-serif" '
        'font-size="16" font-weight="600" letter-spacing="3" fill="#94a3b8">COMMUNITY POLL</text>',
        (
            f'<text x="400" y="{question_y}" text-anchor="middle" '
            'font-family="Inter, sans-serif" font-size="34" font-weight="800" fill="#f8fafc">'
        ),
    ]

    for index, line in enumerate(question_lines):
        dy = "0" if index == 0 else "42"
        parts.append(f'<tspan x="400" dy="{dy}">{escape(line)}</tspan>')
    parts.append("</text>")

    gap = 0.0
    if len(safe_options) > 1:
        gap = (_BARS_BOTTOM - _BARS_TOP - (_BAR_HEIGHT * len(safe_options))) / (
            len(safe_options) - 1
        )

    for index, option in enumerate(safe_options):
        y = _BARS_TOP + index * (_BAR_HEIGHT + gap)
        text_y = y + 35
        parts.append(
            f'<rect x="{_BAR_X}" y="{y:.2f}" width="{_BAR_WIDTH}" height="{_BAR_HEIGHT}" '
            f'rx="28" fill="#0f172a" stroke="{safe_color}" stroke-width="3" />'
        )
        parts.append(
            f'<text x="{_BAR_X + 36}" y="{text_y:.2f}" font-family="Inter, sans-serif" '
            'font-size="24" font-weight="600" fill="#e2e8f0">'
            f"{option}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)


def _wrap_text(text: str, *, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return [text.strip() or "Poll"]

    lines: list[str] = []
    current_line = words[0]
    for word in words[1:]:
        candidate = f"{current_line} {word}"
        if len(candidate) <= max_chars:
            current_line = candidate
            continue
        lines.append(current_line)
        current_line = word

    lines.append(current_line)
    return lines[:3]
