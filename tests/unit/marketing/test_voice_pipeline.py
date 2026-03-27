"""Tests for LinkedIn voice pipeline (SPEC-035)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from holus.agents.marketing.voice_pipeline import (
    EnrichedContext,
    IdeaMetadata,
    VoicePipeline,
    _parse_json_response,
    _parse_voice_sections,
)


# -- Unit tests for parsers ------------------------------------------------


def test_parse_voice_sections_standard() -> None:
    text = """
[HOOK]
Most people debug agents. I build systems that debug themselves.

[BODY]
I spent 3 months building Holus — an AI that decides what to post, creates the content, and learns from what works.

The hard part wasn't the AI. It was the eval gate.

[CTA]
What would you automate first if you had a reliable eval loop?

[VOICE_CHECK]
PASS
"""
    hook, body, cta, voice_check = _parse_voice_sections(text)
    assert "Most people debug agents" in hook
    assert "Holus" in body
    assert "automate" in cta
    assert voice_check == "PASS"


def test_parse_voice_sections_fail() -> None:
    text = """
[HOOK]
Let's dive in to the world of AI agents!

[BODY]
Some body text.

[CTA]
Great question!

[VOICE_CHECK]
FAIL: "Let's dive in!" violates anti-pattern rule
"""
    _, _, _, voice_check = _parse_voice_sections(text)
    assert voice_check.startswith("FAIL")


def test_parse_json_response_plain() -> None:
    text = '{"content_pillar": "ai_engineering", "product_angle": "holus"}'
    data = _parse_json_response(text)
    assert data["content_pillar"] == "ai_engineering"


def test_parse_json_response_fenced() -> None:
    text = '```json\n{"content_pillar": "building_in_public"}\n```'
    data = _parse_json_response(text)
    assert data["content_pillar"] == "building_in_public"


# -- Integration-style tests with mocked LLM -------------------------------


@pytest.fixture
def mock_loader() -> MagicMock:
    loader = MagicMock()
    loader.get_prompt.return_value = "You are a test agent."
    return loader


@pytest.fixture
def pipeline(mock_loader: MagicMock) -> VoicePipeline:
    return VoicePipeline(loader=mock_loader)


def _inject_response() -> str:
    return '{"core_idea": "MCPs are the new frontier", "content_pillar": "ai_engineering", "product_angle": "holus", "suggested_hook": "bold_claim", "confidence": "high"}'


def _enrich_response() -> str:
    return '{"enriched_idea": "MCPs solve agent communication", "supporting_data": ["250+ MCP servers on GitHub"], "product_connection": "Holus uses MCPs", "angle": "builder perspective", "anti_pattern_flags": []}'


def _voice_response(voice_check: str = "PASS") -> str:
    return f"""
[HOOK]
I've been building with MCPs for 6 months. Here's what nobody tells you.

[BODY]
The protocol is simple. The integration is not.

Every silo tool in Holus talks to each other through MCPs — genpeli, pilaster, social-media. I didn't invent this pattern. I just built it.

[CTA]
What communication pattern are you using for your agents?

[VOICE_CHECK]
{voice_check}
"""


def test_pipeline_run_success(pipeline: VoicePipeline) -> None:
    with patch(
        "holus.agents.marketing.voice_pipeline._call_llm",
        side_effect=[_inject_response(), _enrich_response(), _voice_response("PASS")],
    ):
        result = pipeline.run("MCPs are the new frontier for agents")

    assert result.voice_check == "PASS"
    assert result.retried is False
    assert "HOOK" not in result.full_post  # sections stripped
    assert len(result.full_post) > 0
    assert result.metadata.content_pillar == "ai_engineering"
    assert result.context.product_connection == "Holus uses MCPs"


def test_pipeline_retries_on_voice_fail(pipeline: VoicePipeline) -> None:
    with patch(
        "holus.agents.marketing.voice_pipeline._call_llm",
        side_effect=[
            _inject_response(),
            _enrich_response(),
            _voice_response("FAIL: used 'Let's dive in!'"),
            _voice_response("PASS"),  # retry succeeds
        ],
    ):
        result = pipeline.run("MCPs are the new frontier for agents")

    assert result.retried is True
    assert result.voice_check == "PASS"


def test_pipeline_handles_inject_parse_error(pipeline: VoicePipeline) -> None:
    """Gracefully falls back when idea-injector returns non-JSON."""
    with patch(
        "holus.agents.marketing.voice_pipeline._call_llm",
        side_effect=[
            "This is not JSON",  # inject fails
            _enrich_response(),
            _voice_response("PASS"),
        ],
    ):
        result = pipeline.run("MCPs are the new frontier")

    # Should still produce output with fallback defaults
    assert result.metadata.content_pillar == "ai_engineering"
    assert result.error is None
