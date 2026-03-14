from __future__ import annotations

import pytest

from holus.visual.poll import generate_poll_svg
from holus.visual.spec_converter import poll_to_spec


def test_poll_svg_returns_svg() -> None:
    svg = generate_poll_svg("Best AI tool?", ["GPT-4", "Claude"])

    assert svg.startswith("<svg")


def test_poll_svg_contains_question() -> None:
    svg = generate_poll_svg("Best AI tool?", ["GPT-4", "Claude"])

    assert "Best AI tool?" in svg


def test_poll_svg_contains_options() -> None:
    svg = generate_poll_svg("Best AI tool?", ["GPT-4", "Claude"])

    assert "GPT-4" in svg
    assert "Claude" in svg


def test_poll_svg_four_options() -> None:
    svg = generate_poll_svg("Q?", ["A", "B", "C", "D"])

    assert svg.startswith("<svg")


def test_poll_svg_too_few_options_raises() -> None:
    with pytest.raises(ValueError):
        generate_poll_svg("Q?", ["A"])


def test_poll_svg_too_many_options_raises() -> None:
    with pytest.raises(ValueError):
        generate_poll_svg("Q?", ["A", "B", "C", "D", "E"])


def test_poll_to_spec_returns_render_spec() -> None:
    spec = poll_to_spec({"question": "Q?", "options": ["A", "B"]})

    assert spec.template == "single_image/poll"
    assert "svg_content" in spec.variables
