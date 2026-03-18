"""Tests for specialist dispatch pipeline."""

from holus.agents.marketing.specialist_dispatch import (
    PIPELINES,
    SPECIALIST_TASKS,
    SpecialistDispatcher,
    SpecialistOutput,
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
            SpecialistOutput(specialist_id="cta-strategist", output="What's your agent's feedback loop?"),
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
