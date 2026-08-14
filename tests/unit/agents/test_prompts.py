"""Behavior-level contracts for current marketing prompt outputs."""

from __future__ import annotations

from holus.agents.marketing.prompts import (
    NICHE_EXTRACTION_PROMPT,
    OPUS_STRATEGY_PROMPT,
    REPURPOSE_PROMPT,
    SONNET_CONTENT_PROMPT,
    format_anti_patterns,
    format_brand_identity,
    format_content_pillars,
    format_positioning,
    format_product_info,
    format_voice,
)


def test_strategy_prompt_renders_current_context_and_review_feedback() -> None:
    """The reason-stage prompt retains its authority and feedback inputs."""
    rendered = OPUS_STRATEGY_PROMPT.format(
        brand_identity="Builder proof",
        content_pillars="- Builder stories",
        audience_knowledge="CTOs",
        platform_knowledge="LinkedIn",
        niche_research="Agent reliability is trending",
        content_formats="Tutorial",
        viral_frameworks="Contrarian claim",
        memory="Past lesson",
        analytics="Strong comments",
        anti_patterns="No hype",
        prior_feedback="Avoid vague outcomes",
    )

    for value in ("Builder proof", "Agent reliability is trending", "Avoid vague outcomes"):
        assert value in rendered
    assert "ONE authority-building" in rendered
    assert "consulting prospects" in rendered


def test_content_prompt_renders_brief_and_requires_publishable_text() -> None:
    """The generation prompt keeps supplied context and its output-only contract."""
    rendered = SONNET_CONTENT_PROMPT.format(
        topic="AI deployment",
        content_pillar="ai_frameworks",
        hook="Most AI pilots fail before production.",
        framework="case study",
        reasoning="Useful to engineering leaders",
        voice="Grounded",
        positioning="Builder consultant",
        product_info="Pilaster proof",
        anti_patterns="No hype",
        prior_feedback="Use concrete evidence",
    )

    assert "AI deployment" in rendered
    assert "Use concrete evidence" in rendered
    assert "Return ONLY the post text" in rendered
    assert 'NEVER start the post with the word "I"' in rendered


def test_repurpose_prompt_uses_target_specific_rules_and_feedback() -> None:
    """Repurposing preserves the human-review-ready completion requirement."""
    rendered = REPURPOSE_PROMPT.format(
        target_platform="Twitter",
        original_text="The original LinkedIn insight",
        platform_rules="Keep each tweet concise.",
        voice="Direct builder voice",
        prior_feedback="Avoid generic calls to action.",
    )

    assert rendered.count("Twitter") >= 2
    assert "Avoid generic calls to action." in rendered
    assert "never end mid-sentence" in rendered


def test_niche_extraction_prompt_includes_supplied_results_and_structured_fields() -> None:
    """Research extraction receives source material and asks for actionable insight fields."""
    rendered = NICHE_EXTRACTION_PROMPT.format(search_results="Result: deployment teams need proof")

    assert "Result: deployment teams need proof" in rendered
    for field in ("source_url", "why_it_works", "relevance_to_camilo", "pillar_fit"):
        assert field in rendered


def test_brand_formatters_include_available_evidence_without_exact_snapshots() -> None:
    """Formatter output retains meaningful brand facts across prompt consumers."""
    brand = {
        "story": {"origin": "Built production AI systems"},
        "positioning": {"one_liner": "Builder consultant", "what_i_am": ["Practitioner"]},
        "products_as_proof": {"pilaster": {"proof_narrative": "Built image memory"}},
        "content_pillars": [
            {"id": "builder_stories", "name": "Builder Stories", "description": "Lessons"}
        ],
        "voice": {"archetype": "Builder-philosopher", "tone": ["Direct"]},
        "anti_patterns": {"phrases": ["game-changing"]},
    }

    for output, expected in (
        (format_brand_identity(brand), "Built production AI systems"),
        (format_content_pillars(brand), "Builder Stories"),
        (format_voice(brand), "Builder-philosopher"),
        (format_positioning(brand), "Practitioner"),
        (format_anti_patterns(brand), "game-changing"),
    ):
        assert expected in output


def test_product_formatter_uses_proof_framing_and_config_fallbacks() -> None:
    """Product context remains evidence-led when optional config fields are absent."""
    rendered = format_product_info(
        "invoz", {"invoz": {"audience": "Developers", "tagline": "Audio ML API"}}
    )

    assert "proof point, not the pitch" in rendered
    assert "Developers" in rendered
    assert "Audio ML API" in rendered
