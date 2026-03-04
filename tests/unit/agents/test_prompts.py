"""Tests for prompts.py — prompt templates and brand identity formatting helpers.

Covers:
  - Prompt template constants — verify placeholders exist and are well-formed
  - format_brand_identity() — empty, partial, and full brand dicts
  - format_content_pillars() — empty, single, and multiple pillars
  - format_voice() — empty, partial, and full voice config
  - format_positioning() — empty, partial, and full positioning
  - format_anti_patterns() — empty, single, and multiple categories
  - format_product_info() — none product, known product, missing product
"""

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_brand() -> dict:
    """Build a complete brand identity dict for testing."""
    return {
        "story": {
            "origin": "Started as a solo engineer",
            "journey": ["Built Pilaster", "Launched genpeli", "AI consulting"],
        },
        "positioning": {
            "one_liner": "AI builder turned consultant",
            "category": "AI Implementation",
            "differentiation": ["Builds real products", "Not just theory"],
            "what_i_am": ["Builder", "Consultant"],
            "what_i_am_not": ["Influencer", "Guru"],
            "market": "NYC",
        },
        "products_as_proof": {
            "framing": "Each product is evidence of builder expertise",
            "pilaster": {"proof_narrative": "Built an AI image platform with memory"},
            "genpeli": {"proof_narrative": "Automated video editing pipeline"},
            "invoz": {"proof_narrative": "Built an audio ML API"},
        },
        "voice": {
            "archetype": "Builder-Philosopher",
            "summary": "First person, short paragraphs, shows the work",
            "tone": ["Direct", "Grounded", "Evidence-based"],
            "hooks": {
                "question": "What if AI could remember?",
                "bold_claim": "Most AI tools are broken.",
            },
            "closers": {
                "question": "What would you build?",
                "forward": "Next week I'll share more.",
            },
        },
        "anti_patterns": {
            "phrases": ["game-changer", "revolutionary", "unlock the power"],
            "behaviors": ["Passive voice", "Unsubstantiated claims"],
        },
        "content_pillars": [
            {
                "id": "builder_stories",
                "name": "Builder Stories",
                "description": "What I built and what I learned",
                "frequency": "2x/week",
                "goal": "Demonstrate builder credibility",
            },
            {
                "id": "ai_frameworks",
                "name": "AI Frameworks",
                "description": "How to deploy AI in your company",
                "frequency": "1x/week",
                "goal": "Show consulting expertise",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Tests: Prompt Template Constants
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    """Verify prompt templates have expected placeholders."""

    def test_opus_strategy_has_all_placeholders(self):
        expected = [
            "brand_identity",
            "content_pillars",
            "audience_knowledge",
            "platform_knowledge",
            "niche_research",
            "content_formats",
            "viral_frameworks",
            "memory",
            "analytics",
            "anti_patterns",
        ]
        for placeholder in expected:
            assert f"{{{placeholder}}}" in OPUS_STRATEGY_PROMPT, f"Missing {{{placeholder}}}"

    def test_sonnet_content_has_all_placeholders(self):
        expected = [
            "topic",
            "content_pillar",
            "hook",
            "framework",
            "reasoning",
            "voice",
            "positioning",
            "product_info",
            "anti_patterns",
        ]
        for placeholder in expected:
            assert f"{{{placeholder}}}" in SONNET_CONTENT_PROMPT, f"Missing {{{placeholder}}}"

    def test_repurpose_has_all_placeholders(self):
        expected = ["target_platform", "original_text", "platform_rules", "voice"]
        for placeholder in expected:
            assert f"{{{placeholder}}}" in REPURPOSE_PROMPT, f"Missing {{{placeholder}}}"

    def test_niche_extraction_has_search_results_placeholder(self):
        assert "{search_results}" in NICHE_EXTRACTION_PROMPT

    def test_opus_strategy_contains_json_output_format(self):
        assert "json" in OPUS_STRATEGY_PROMPT.lower()
        assert "content_pillar" in OPUS_STRATEGY_PROMPT

    def test_sonnet_content_mentions_linkedin_rules(self):
        assert "3,000 characters" in SONNET_CONTENT_PROMPT
        assert "First person" in SONNET_CONTENT_PROMPT

    def test_repurpose_prompt_is_platform_agnostic(self):
        # Should use {target_platform} placeholder, not hardcode any platform
        assert "{target_platform}" in REPURPOSE_PROMPT

    def test_niche_extraction_defines_json_schema(self):
        assert "source_url" in NICHE_EXTRACTION_PROMPT
        assert "why_it_works" in NICHE_EXTRACTION_PROMPT
        assert "pillar_fit" in NICHE_EXTRACTION_PROMPT


# ---------------------------------------------------------------------------
# Tests: format_brand_identity()
# ---------------------------------------------------------------------------


class TestFormatBrandIdentity:
    """Test brand identity formatting for prompt injection."""

    def test_empty_brand_returns_fallback(self):
        result = format_brand_identity({})
        assert "No brand identity loaded" in result

    def test_none_brand_returns_fallback(self):
        result = format_brand_identity({})
        assert "general professional tone" in result

    def test_story_origin_included(self):
        brand = {"story": {"origin": "Started as a solo engineer"}}
        result = format_brand_identity(brand)
        assert "Started as a solo engineer" in result
        assert "**Origin:**" in result

    def test_story_journey_items_listed(self):
        brand = {"story": {"journey": ["Built Pilaster", "Launched genpeli"]}}
        result = format_brand_identity(brand)
        assert "Built Pilaster" in result
        assert "Launched genpeli" in result

    def test_positioning_one_liner(self):
        brand = {"positioning": {"one_liner": "AI builder turned consultant"}}
        result = format_brand_identity(brand)
        assert "AI builder turned consultant" in result

    def test_positioning_category(self):
        brand = {"positioning": {"category": "AI Implementation"}}
        result = format_brand_identity(brand)
        assert "AI Implementation" in result

    def test_positioning_differentiation_listed(self):
        brand = {"positioning": {"differentiation": ["Builds real products", "Not just theory"]}}
        result = format_brand_identity(brand)
        assert "Builds real products" in result

    def test_products_as_proof_framing(self):
        brand = {"products_as_proof": {"framing": "Each product is evidence"}}
        result = format_brand_identity(brand)
        assert "Each product is evidence" in result

    def test_products_as_proof_narratives(self):
        brand = {
            "products_as_proof": {
                "pilaster": {"proof_narrative": "Built an AI image platform"},
                "genpeli": {"proof_narrative": "Automated video editing"},
            }
        }
        result = format_brand_identity(brand)
        assert "Built an AI image platform" in result
        assert "Automated video editing" in result

    def test_full_brand_includes_all_sections(self):
        result = format_brand_identity(_full_brand())
        assert "**Origin:**" in result
        assert "**One-liner:**" in result
        assert "**Products as Proof:**" in result

    def test_missing_story_key_no_crash(self):
        brand = {"positioning": {"one_liner": "Test"}}
        result = format_brand_identity(brand)
        assert "Test" in result
        # No story section, no crash


# ---------------------------------------------------------------------------
# Tests: format_content_pillars()
# ---------------------------------------------------------------------------


class TestFormatContentPillars:
    """Test content pillar formatting."""

    def test_empty_pillars_returns_fallback(self):
        result = format_content_pillars({})
        assert "No content pillars defined" in result

    def test_no_pillars_key(self):
        result = format_content_pillars({"other_key": "value"})
        assert "No content pillars defined" in result

    def test_single_pillar(self):
        brand = {
            "content_pillars": [
                {"id": "builder_stories", "name": "Builder Stories", "description": "What I built"}
            ]
        }
        result = format_content_pillars(brand)
        assert "Builder Stories" in result
        assert "builder_stories" in result
        assert "What I built" in result

    def test_pillar_frequency_shown(self):
        brand = {
            "content_pillars": [
                {"id": "test", "name": "Test", "description": "Desc", "frequency": "2x/week"}
            ]
        }
        result = format_content_pillars(brand)
        assert "2x/week" in result

    def test_pillar_goal_shown(self):
        brand = {
            "content_pillars": [
                {"id": "test", "name": "Test", "description": "Desc", "goal": "Build credibility"}
            ]
        }
        result = format_content_pillars(brand)
        assert "Build credibility" in result

    def test_multiple_pillars(self):
        result = format_content_pillars(_full_brand())
        assert "Builder Stories" in result
        assert "AI Frameworks" in result

    def test_pillar_missing_optional_fields(self):
        brand = {
            "content_pillars": [{"id": "minimal", "name": "Minimal", "description": "Just basics"}]
        }
        result = format_content_pillars(brand)
        assert "Minimal" in result
        # No frequency/goal — no crash


# ---------------------------------------------------------------------------
# Tests: format_voice()
# ---------------------------------------------------------------------------


class TestFormatVoice:
    """Test voice profile formatting."""

    def test_empty_voice_returns_fallback(self):
        result = format_voice({})
        assert "Professional" in result

    def test_empty_voice_dict_returns_fallback(self):
        result = format_voice({"voice": {}})
        assert "Professional" in result

    def test_archetype_shown(self):
        brand = {"voice": {"archetype": "Builder-Philosopher"}}
        result = format_voice(brand)
        assert "Builder-Philosopher" in result

    def test_summary_shown(self):
        brand = {"voice": {"summary": "First person, shows the work"}}
        result = format_voice(brand)
        assert "First person, shows the work" in result

    def test_tone_rules_listed(self):
        brand = {"voice": {"tone": ["Direct", "Grounded"]}}
        result = format_voice(brand)
        assert "Direct" in result
        assert "Grounded" in result

    def test_hooks_shown(self):
        brand = {"voice": {"hooks": {"question": "What if AI could remember?"}}}
        result = format_voice(brand)
        assert "What if AI could remember?" in result
        assert "question" in result

    def test_closers_shown(self):
        brand = {"voice": {"closers": {"forward": "Next week I'll share more."}}}
        result = format_voice(brand)
        assert "Next week I'll share more." in result

    def test_full_voice(self):
        result = format_voice(_full_brand())
        assert "Builder-Philosopher" in result
        assert "Direct" in result
        assert "What if AI could remember?" in result
        assert "What would you build?" in result


# ---------------------------------------------------------------------------
# Tests: format_positioning()
# ---------------------------------------------------------------------------


class TestFormatPositioning:
    """Test positioning formatting."""

    def test_empty_returns_fallback(self):
        result = format_positioning({})
        assert "AI builder and consultant" in result

    def test_empty_positioning_dict_returns_fallback(self):
        result = format_positioning({"positioning": {}})
        assert "AI builder and consultant" in result

    def test_one_liner_shown(self):
        brand = {"positioning": {"one_liner": "AI builder turned consultant"}}
        result = format_positioning(brand)
        assert "AI builder turned consultant" in result

    def test_category_shown(self):
        brand = {"positioning": {"category": "AI Implementation"}}
        result = format_positioning(brand)
        assert "AI Implementation" in result

    def test_what_i_am_listed(self):
        brand = {"positioning": {"what_i_am": ["Builder", "Consultant"]}}
        result = format_positioning(brand)
        assert "Builder" in result
        assert "Consultant" in result
        assert "What Camilo IS" in result

    def test_what_i_am_not_listed(self):
        brand = {"positioning": {"what_i_am_not": ["Influencer", "Guru"]}}
        result = format_positioning(brand)
        assert "Influencer" in result
        assert "What Camilo is NOT" in result

    def test_full_positioning(self):
        result = format_positioning(_full_brand())
        assert "AI builder turned consultant" in result
        assert "Builder" in result
        assert "Influencer" in result


# ---------------------------------------------------------------------------
# Tests: format_anti_patterns()
# ---------------------------------------------------------------------------


class TestFormatAntiPatterns:
    """Test anti-pattern formatting."""

    def test_empty_returns_fallback(self):
        result = format_anti_patterns({})
        assert "generic marketing language" in result

    def test_empty_anti_patterns_dict_returns_fallback(self):
        result = format_anti_patterns({"anti_patterns": {}})
        assert "generic marketing language" in result

    def test_single_category(self):
        brand = {"anti_patterns": {"phrases": ["game-changer", "revolutionary"]}}
        result = format_anti_patterns(brand)
        assert "game-changer" in result
        assert "revolutionary" in result
        assert "**Phrases:**" in result

    def test_multiple_categories(self):
        brand = {
            "anti_patterns": {
                "phrases": ["game-changer"],
                "behaviors": ["Passive voice"],
            }
        }
        result = format_anti_patterns(brand)
        assert "game-changer" in result
        assert "Passive voice" in result

    def test_non_list_values_skipped(self):
        brand = {"anti_patterns": {"note": "this is a string, not a list"}}
        result = format_anti_patterns(brand)
        # String values should be skipped, not crash
        assert "generic marketing language" in result

    def test_empty_list_skipped(self):
        brand = {"anti_patterns": {"phrases": []}}
        result = format_anti_patterns(brand)
        assert "generic marketing language" in result


# ---------------------------------------------------------------------------
# Tests: format_product_info()
# ---------------------------------------------------------------------------


class TestFormatProductInfo:
    """Test product info formatting for content generation."""

    def test_none_product_returns_general(self):
        result = format_product_info("none", {})
        assert "general AI implementation expertise" in result

    def test_empty_product_returns_general(self):
        result = format_product_info("", {})
        assert "general AI implementation expertise" in result

    def test_known_product_formatted(self):
        products = {
            "pilaster": {
                "description": "AI image generation platform",
                "target_audience": "AI artists",
                "features": ["Character memory", "Backend-agnostic"],
                "value_prop": "Generate with memory",
                "pain_point": "Inconsistent characters",
            }
        }
        result = format_product_info("pilaster", products)
        assert "Pilaster" in result
        assert "AI image generation platform" in result
        assert "AI artists" in result
        assert "Character memory" in result
        assert "Generate with memory" in result
        assert "Inconsistent characters" in result

    def test_missing_product_shows_na(self):
        result = format_product_info("unknown_product", {})
        assert "Unknown_Product" in result or "N/A" in result

    def test_product_with_missing_fields(self):
        products = {"genpeli": {"description": "Video editor"}}
        result = format_product_info("genpeli", products)
        assert "Video editor" in result
        assert "N/A" in result  # Missing fields show N/A

    def test_product_uses_audience_fallback(self):
        """If target_audience missing, falls back to audience key."""
        products = {"invoz": {"audience": "Developers"}}
        result = format_product_info("invoz", products)
        assert "Developers" in result

    def test_product_uses_tagline_fallback(self):
        """If value_prop missing, falls back to tagline key."""
        products = {"invoz": {"tagline": "Audio ML API"}}
        result = format_product_info("invoz", products)
        assert "Audio ML API" in result

    def test_proof_not_pitch_framing(self):
        products = {"pilaster": {"description": "Test"}}
        result = format_product_info("pilaster", products)
        assert "proof point, not the pitch" in result
