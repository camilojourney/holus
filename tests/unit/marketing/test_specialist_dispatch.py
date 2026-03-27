"""Tests for specialist dispatch pipeline."""

from holus.agents.marketing.specialist_dispatch import (
    PIPELINES,
    SPECIALIST_TASKS,
    SpecialistDispatcher,
    SpecialistOutput,
    _derive_hashtags,
    _enrich_for_platform,
)


class TestPipelines:
    def test_text_post_pipeline(self):
        pipeline = PIPELINES["text_post"]
        assert pipeline[0] == "hook-architect"
        assert pipeline[-1] == "voice-guardian"
        assert len(pipeline) == 4

    def test_carousel_pipeline(self):
        pipeline = PIPELINES["carousel_outline"]
        assert "carousel-architect" in pipeline
        assert "hook-architect" in pipeline

    def test_all_specialists_have_tasks(self):
        all_specialists = set()
        for pipeline in PIPELINES.values():
            all_specialists.update(pipeline)
        for specialist in all_specialists:
            assert specialist in SPECIALIST_TASKS, f"{specialist} missing task"


class TestAssembledContent:
    def test_assembly(self):
        outputs = [
            SpecialistOutput(specialist_id="hook-architect", output="73% of agents fail."),
            SpecialistOutput(specialist_id="storyteller", output="Here's why they break down."),
            SpecialistOutput(
                specialist_id="cta-strategist", output="What's your agent's feedback loop?"
            ),
            SpecialistOutput(specialist_id="voice-guardian", output="PASS — voice is consistent."),
        ]

        dispatcher = SpecialistDispatcher()
        content = dispatcher._assemble(outputs, "text_post")

        assert "73% of agents fail" in content.text
        assert "break down" in content.text
        assert "feedback loop" in content.text
        assert content.voice_check == "PASS"
        assert content.hook == "73% of agents fail."

    def test_voice_fail(self):
        outputs = [
            SpecialistOutput(specialist_id="hook-architect", output="Test"),
            SpecialistOutput(specialist_id="storyteller", output="Body"),
            SpecialistOutput(specialist_id="cta-strategist", output="CTA"),
            SpecialistOutput(specialist_id="voice-guardian", output="FAIL — too formal, uses 'we'"),
        ]
        dispatcher = SpecialistDispatcher()
        content = dispatcher._assemble(outputs, "text_post")
        assert content.voice_check == "FAIL"


class TestSpecialistDispatcher:
    def test_build_prompt_includes_idea(self):
        dispatcher = SpecialistDispatcher()
        prompt = dispatcher._build_specialist_prompt(
            specialist_id="hook-architect",
            idea="AI agents fail after week 1",
            platform="linkedin",
            content_type="text_post",
            pillar="ai_engineering",
            task="Write the hook",
            chain_context="",
        )
        assert "AI agents fail" in prompt
        assert "linkedin" in prompt

    def test_build_prompt_includes_chain_context(self):
        dispatcher = SpecialistDispatcher()
        prompt = dispatcher._build_specialist_prompt(
            specialist_id="storyteller",
            idea="Test idea",
            platform="linkedin",
            content_type="text_post",
            pillar="ai_engineering",
            task="Write the body",
            chain_context="--- hook-architect output ---\n73% of agents fail.",
        )
        assert "prior_outputs" in prompt
        assert "73% of agents fail" in prompt


class TestPlatformEnrichment:
    """Test platform-aware post-processing for specialist pipeline outputs."""

    def test_instagram_video_script_gets_hashtags(self):
        text = "HOOK: Building agents that actually learn.\n\nSETUP: Most agent loops are static.\n\nBODY: Here is why.\n\nCTA: What does your agent remember?"
        result = _enrich_for_platform(text, "video_script", "instagram")
        assert "#" in result
        assert result != text  # Text was enriched

    def test_linkedin_video_script_no_hashtags(self):
        text = "HOOK: Building agents.\n\nBODY: Details.\n\nCTA: Question?"
        result = _enrich_for_platform(text, "video_script", "linkedin")
        assert result == text  # LinkedIn video_script not enriched

    def test_text_post_not_enriched(self):
        text = "A regular text post about AI."
        result = _enrich_for_platform(text, "text_post", "instagram")
        assert result == text  # Only video_script gets enriched

    def test_no_double_hashtags(self):
        text = "Video script content.\n\n#ExistingTag #AlreadyThere"
        result = _enrich_for_platform(text, "video_script", "instagram")
        assert result == text  # Already has hashtags, skip

    def test_tiktok_video_script_gets_hashtags(self):
        text = "HOOK: Agents that learn.\n\nBODY: Why it matters.\n\nCTA: Try it."
        result = _enrich_for_platform(text, "video_script", "tiktok")
        assert "#" in result

    def test_assemble_with_platform_instagram(self):
        """Full pipeline: _assemble adds hashtags for Instagram video_script."""
        outputs = [
            SpecialistOutput(specialist_id="hook-architect", output="Building Agents That Learn"),
            SpecialistOutput(
                specialist_id="storyteller", output="Most frameworks are static loops."
            ),
            SpecialistOutput(
                specialist_id="cta-strategist", output="What does your agent remember?"
            ),
        ]
        dispatcher = SpecialistDispatcher()
        content = dispatcher._assemble(outputs, "video_script", "instagram")
        assert "#" in content.text
        assert "Building Agents" in content.text

    def test_assemble_without_platform_no_enrichment(self):
        """Without platform, no enrichment happens (backwards compatible)."""
        outputs = [
            SpecialistOutput(specialist_id="hook-architect", output="Hook"),
            SpecialistOutput(specialist_id="storyteller", output="Body"),
            SpecialistOutput(specialist_id="cta-strategist", output="CTA"),
        ]
        dispatcher = SpecialistDispatcher()
        content = dispatcher._assemble(outputs, "video_script")
        assert "#" not in content.text


class TestDeriveHashtags:
    def test_extracts_capitalised_words(self):
        text = "Building Agents That Learn From Experience"
        tags = _derive_hashtags(text, 5)
        assert len(tags) <= 5
        assert all(t.startswith("#") for t in tags)

    def test_respects_limit(self):
        text = "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta"
        tags = _derive_hashtags(text, 3)
        assert len(tags) == 3

    def test_filters_common_words(self):
        text = "This That When What With From Your They"
        tags = _derive_hashtags(text, 10)
        # Common words filtered out, falls back to base tags
        assert all(t != "#This" for t in tags)
        assert len(tags) > 0  # At least base tags
