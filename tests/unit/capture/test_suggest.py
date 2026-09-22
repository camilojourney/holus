"""Unit tests for capture routing suggestions."""

from __future__ import annotations

from holus.capture.suggest import detect_attachment_kind, suggest_routes


def test_detect_pdf_and_image_and_link() -> None:
    assert detect_attachment_kind(filename="deck.pdf") == "pdf"
    assert detect_attachment_kind(content_type="image/png") == "image"
    assert detect_attachment_kind(attachment_url="https://example.com/post") == "link"
    assert detect_attachment_kind() == "none"


def test_suggest_text_prefers_linkedin_for_long_copy() -> None:
    text = "A" * 450
    suggestions = suggest_routes(text=text)
    channels = [item.channel for item in suggestions]
    assert "linkedin_text" in channels
    assert suggestions[0].preview_text


def test_suggest_short_text_includes_twitter() -> None:
    suggestions = suggest_routes(text="Ship the loop, not the slide deck.")
    platforms = {item.platform for item in suggestions}
    assert "twitter" in platforms or "threads" in platforms


def test_suggest_respects_connected_platforms() -> None:
    suggestions = suggest_routes(
        text="Builder note about agents.",
        connected_platforms=["linkedin"],
    )
    assert suggestions
    assert all(item.platform == "linkedin" for item in suggestions)


def test_suggest_pdf_routes_to_linkedin_carousel() -> None:
    suggestions = suggest_routes(
        text="Quarterly learnings",
        attachment_kind="pdf",
    )
    assert any(item.channel == "linkedin_carousel" for item in suggestions)
