"""Tests for judge feedback injection into generation prompts.

Covers:
  - _format_generation_feedback() platform filtering
  - Feedback injection into SONNET_CONTENT_PROMPT (monolithic fallback)
  - Feedback injection into specialist chain (storyteller input)
  - Feedback injection into REPURPOSE_PROMPT (per-platform)
  - Edge cases (no feedback, empty trajectory, missing platform)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
import yaml

from holus.agents.marketing.agent import MarketingAgent
from holus.agents.marketing.models import ContentDecision, ContentType, Platform
from holus.agents.marketing.prompts import REPURPOSE_PROMPT, SONNET_CONTENT_PROMPT
from holus.agents.marketing.repurpose import _claude_adapt, repurpose_content
from holus.core.config import AgentConfig, HolusConfig

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_TRAJECTORY_ENTRIES = [
    {
        "timestamp": "2026-03-26T21:50:00+00:00",
        "agent_id": "evaluate-content-cli",
        "task_type": "content_evaluation",
        "judge_verdict": "PARTIAL",
        "judge_score": 0.68,
        "judge_feedback": "Output truncated mid-sentence. Narrative arc incomplete.",
        "metadata": {
            "platform": "threads",
            "content_type": "educational",
            "dimension_scores": {
                "hook_strength": 0.9,
                "narrative_arc": 0.55,
                "completeness": 0.45,
            },
        },
    },
    {
        "timestamp": "2026-03-26T21:51:00+00:00",
        "agent_id": "evaluate-content-cli",
        "task_type": "content_evaluation",
        "judge_verdict": "FAIL",
        "judge_score": 0.38,
        "judge_feedback": "Unfinished draft. Missing framework. No CTA.",
        "metadata": {
            "platform": "twitter",
            "content_type": "educational",
            "dimension_scores": {
                "hook_strength": 0.7,
                "completeness": 0.2,
                "actionability": 0.3,
            },
        },
    },
    {
        "timestamp": "2026-03-26T21:52:00+00:00",
        "agent_id": "evaluate-content-cli",
        "task_type": "content_evaluation",
        "judge_verdict": "PASS",
        "judge_score": 0.89,
        "judge_feedback": "Strong authority signal. Great hook.",
        "metadata": {
            "platform": "linkedin",
            "content_type": "builder_story",
            "dimension_scores": {
                "hook_strength": 0.92,
                "authority_signal": 0.88,
            },
        },
    },
]


@pytest.fixture()
def tmp_config(tmp_path: Path) -> dict[str, Any]:
    """Create minimal config for MarketingAgent instantiation."""
    products_path = tmp_path / "config" / "products.yaml"
    products_path.parent.mkdir(parents=True, exist_ok=True)
    products_path.write_text(yaml.dump({"products": {"pilaster": {"name": "Pilaster"}}}))

    knowledge_dir = tmp_path / ".self-improvement" / "knowledge" / "current"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("platforms.md", "audience-profiles.md", "content-formats.md"):
        (knowledge_dir / fname).write_text(f"# {fname}\nTest knowledge.")

    memory_path = tmp_path / ".self-improvement" / "MEMORY.md"
    memory_path.write_text("# Memory\nTest memory.")

    trajectory_path = tmp_path / ".self-improvement" / "memory" / "trajectory.jsonl"
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    trajectory_path.touch()

    brand_path = tmp_path / "config" / "brand.yaml"
    brand_path.write_text(yaml.dump({"voice": {"tone": "builder"}}))

    queue_dir = tmp_path / "data" / "content-queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    return {
        "tmp_path": tmp_path,
        "trajectory_path": trajectory_path,
        "products_path": products_path,
        "brand_path": brand_path,
        "knowledge_dir": knowledge_dir,
    }


def _write_trajectory(path: Path, entries: list[dict[str, Any]]) -> None:
    """Write trajectory entries to JSONL file."""
    with path.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _make_agent(tmp_path: Path) -> MarketingAgent:
    """Create a MarketingAgent with test config."""
    config = HolusConfig(
        agents={
            "marketing": AgentConfig(
                name="marketing",
                model="claude-sonnet-4-6",
                prompt_file="",
            )
        },
        anthropic_api_key="test-key",
    )
    agent = MarketingAgent.__new__(MarketingAgent)
    agent.config = config
    agent.agent_name = "marketing-agent"
    agent._config_dir = tmp_path / "config"
    agent._knowledge_dir = tmp_path / ".self-improvement" / "knowledge" / "current"
    agent._memory_path = tmp_path / ".self-improvement" / "MEMORY.md"
    agent._trajectory_path = tmp_path / ".self-improvement" / "memory" / "trajectory.jsonl"
    agent._queue_dir = tmp_path / "data" / "content-queue"
    return agent


# ---------------------------------------------------------------------------
# Tests: _format_generation_feedback()
# ---------------------------------------------------------------------------


class TestFormatGenerationFeedback:
    """Tests for _format_generation_feedback() platform filtering."""

    def test_returns_no_feedback_when_empty(self, tmp_config: dict[str, Any]) -> None:
        agent = _make_agent(tmp_config["tmp_path"])
        result = agent._format_generation_feedback("threads", prior_feedback="")
        assert result == "No prior feedback for this platform."

    def test_filters_by_platform(self, tmp_config: dict[str, Any]) -> None:
        agent = _make_agent(tmp_config["tmp_path"])
        prior = (
            "## Prior Cycle Feedback (learn from these mistakes)\n"
            "- [THREADS — PARTIAL] Output truncated mid-sentence.\n"
            "  Weak dimensions: narrative_arc=0.55, completeness=0.45\n"
            "- [TWITTER — FAIL] Unfinished draft. Missing framework.\n"
            "  Weak dimensions: completeness=0.20, actionability=0.30"
        )
        result = agent._format_generation_feedback("threads", prior_feedback=prior)
        assert "THREADS" in result
        assert "TWITTER" not in result

    def test_includes_weak_dimensions(self, tmp_config: dict[str, Any]) -> None:
        agent = _make_agent(tmp_config["tmp_path"])
        prior = (
            "## Prior Cycle Feedback (learn from these mistakes)\n"
            "- [THREADS — PARTIAL] Truncated.\n"
            "  Weak dimensions: narrative_arc=0.55\n"
        )
        result = agent._format_generation_feedback("threads", prior_feedback=prior)
        assert "Weak dimensions" in result
        assert "narrative_arc" in result

    def test_no_matching_platform(self, tmp_config: dict[str, Any]) -> None:
        agent = _make_agent(tmp_config["tmp_path"])
        prior = "- [LINKEDIN — PARTIAL] Some feedback."
        result = agent._format_generation_feedback("threads", prior_feedback=prior)
        assert result == "No prior feedback for this platform."

    def test_case_insensitive_platform_match(self, tmp_config: dict[str, Any]) -> None:
        agent = _make_agent(tmp_config["tmp_path"])
        prior = "- [threads — PARTIAL] Truncated output."
        result = agent._format_generation_feedback("threads", prior_feedback=prior)
        assert "Truncated" in result

    def test_twitter_platform_match(self, tmp_config: dict[str, Any]) -> None:
        agent = _make_agent(tmp_config["tmp_path"])
        prior = "- [TWITTER — FAIL] Unfinished draft.\n  Weak dimensions: completeness=0.20"
        result = agent._format_generation_feedback("twitter", prior_feedback=prior)
        assert "FAIL" in result
        assert "Unfinished" in result


# ---------------------------------------------------------------------------
# Tests: Feedback in SONNET_CONTENT_PROMPT
# ---------------------------------------------------------------------------


class TestSonnetContentPromptFeedback:
    """Tests that SONNET_CONTENT_PROMPT accepts and renders prior_feedback."""

    def test_prompt_has_prior_feedback_placeholder(self) -> None:
        assert "{prior_feedback}" in SONNET_CONTENT_PROMPT

    def test_prompt_renders_with_feedback(self) -> None:
        rendered = SONNET_CONTENT_PROMPT.format(
            topic="Test topic",
            content_pillar="builder_stories",
            hook="Test hook",
            framework="original",
            reasoning="Test reasoning",
            voice="Builder voice",
            positioning="Test positioning",
            product_info="Test product",
            anti_patterns="No jargon",
            prior_feedback="- [LINKEDIN — PARTIAL] Weak authority signal.",
        )
        assert "Weak authority signal" in rendered

    def test_prompt_renders_with_no_feedback(self) -> None:
        rendered = SONNET_CONTENT_PROMPT.format(
            topic="Test topic",
            content_pillar="builder_stories",
            hook="Test hook",
            framework="original",
            reasoning="Test reasoning",
            voice="Builder voice",
            positioning="Test positioning",
            product_info="Test product",
            anti_patterns="No jargon",
            prior_feedback="No prior feedback for this platform.",
        )
        assert "No prior feedback for this platform." in rendered


# ---------------------------------------------------------------------------
# Tests: Feedback in REPURPOSE_PROMPT
# ---------------------------------------------------------------------------


class TestRepurposePromptFeedback:
    """Tests that REPURPOSE_PROMPT accepts and renders prior_feedback."""

    def test_prompt_has_prior_feedback_placeholder(self) -> None:
        assert "{prior_feedback}" in REPURPOSE_PROMPT

    def test_prompt_renders_with_feedback(self) -> None:
        rendered = REPURPOSE_PROMPT.format(
            target_platform="Threads",
            original_text="Original LinkedIn post here.",
            platform_rules="Keep it casual.",
            voice="Builder voice",
            prior_feedback="- [THREADS — PARTIAL] Output truncated mid-sentence.",
        )
        assert "Output truncated mid-sentence" in rendered
        assert "MUST be complete" in rendered

    def test_claude_adapt_passes_feedback(self) -> None:
        """_claude_adapt() correctly formats prompt with prior_feedback."""
        mock_client = MagicMock()
        text_block = MagicMock()
        text_block.text = "Adapted text for threads."
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_client.call.return_value = mock_response

        result = _claude_adapt(
            original_text="Original post.",
            target=Platform.THREADS,
            rules={"style": "casual"},
            voice="Builder voice",
            claude_client=mock_client,
            agent_id="test",
            prior_feedback="- [THREADS — PARTIAL] Truncated output.",
        )

        # Verify the system prompt passed to claude contains the feedback
        call_args = mock_client.call.call_args
        system_prompt = call_args.kwargs["cached_prompt"].system_prompt
        assert "Truncated output" in system_prompt
        assert result == "Adapted text for threads."


# ---------------------------------------------------------------------------
# Tests: Feedback flows through repurpose_content()
# ---------------------------------------------------------------------------


class TestRepurposeFeedbackFlow:
    """Tests that repurpose_content() passes feedback to each platform adapter."""

    @pytest.mark.asyncio
    async def test_repurpose_passes_feedback_to_adapter(self) -> None:
        mock_client = MagicMock()
        text_block = MagicMock()
        text_block.text = "Adapted text."
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_response.usage = MagicMock(
            input_tokens=50,
            output_tokens=30,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        mock_client.call.return_value = mock_response
        mock_client.sonnet_model = "claude-sonnet-4-6"

        decision = ContentDecision(
            product="pilaster",
            platform=Platform.LINKEDIN,
            content_type=ContentType.EDUCATIONAL,
            topic="test",
            hook="test hook",
            reasoning="test reasoning",
        )

        calls_received: list[str] = []

        def fake_format_fn(platform: str, *, prior_feedback: str = "") -> str:
            calls_received.append(platform)
            return f"Feedback for {platform}"

        pieces = await repurpose_content(
            original_text="Original LinkedIn post about AI.",
            decision=decision,
            claude_client=mock_client,
            brand={},
            cycle_id="test-cycle",
            piece_index=1,
            targets=[Platform.TWITTER],
            prior_feedback="- [TWITTER — FAIL] Unfinished draft.",
            format_feedback_fn=fake_format_fn,
        )

        assert len(pieces) == 1
        assert "twitter" in calls_received

    @pytest.mark.asyncio
    async def test_repurpose_no_feedback_fn_still_works(self) -> None:
        """repurpose_content() works without feedback (backwards compat)."""
        mock_client = MagicMock()
        text_block = MagicMock()
        text_block.text = "Adapted text."
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_response.usage = MagicMock(
            input_tokens=50,
            output_tokens=30,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        mock_client.call.return_value = mock_response
        mock_client.sonnet_model = "claude-sonnet-4-6"

        decision = ContentDecision(
            product="pilaster",
            platform=Platform.LINKEDIN,
            content_type=ContentType.EDUCATIONAL,
            topic="test",
            hook="test hook",
            reasoning="test reasoning",
        )

        pieces = await repurpose_content(
            original_text="Original LinkedIn post.",
            decision=decision,
            claude_client=mock_client,
            brand={},
            cycle_id="test-cycle",
            piece_index=1,
            targets=[Platform.TWITTER],
        )

        assert len(pieces) == 1


# ---------------------------------------------------------------------------
# Tests: _load_prior_judge_feedback() (existing method, tested for coverage)
# ---------------------------------------------------------------------------


class TestLoadPriorJudgeFeedback:
    """Tests for _load_prior_judge_feedback() reading trajectory.jsonl."""

    def test_loads_failures_from_trajectory(
        self, tmp_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_config["tmp_path"])
        agent = _make_agent(tmp_config["tmp_path"])
        _write_trajectory(tmp_config["trajectory_path"], SAMPLE_TRAJECTORY_ENTRIES)

        result = agent._load_prior_judge_feedback()
        assert "THREADS" in result
        assert "TWITTER" in result
        # PASS entries should NOT appear
        assert "Strong authority signal" not in result

    def test_returns_empty_when_no_trajectory(
        self, tmp_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_config["tmp_path"])
        agent = _make_agent(tmp_config["tmp_path"])
        tmp_config["trajectory_path"].unlink()

        result = agent._load_prior_judge_feedback()
        assert result == ""

    def test_returns_empty_when_all_pass(
        self, tmp_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_config["tmp_path"])
        agent = _make_agent(tmp_config["tmp_path"])
        pass_entry = {
            "judge_verdict": "PASS",
            "judge_score": 0.9,
            "judge_feedback": "Great content.",
            "metadata": {"platform": "linkedin"},
        }
        _write_trajectory(tmp_config["trajectory_path"], [pass_entry])

        result = agent._load_prior_judge_feedback()
        assert result == ""

    def test_includes_weak_dimensions(
        self, tmp_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_config["tmp_path"])
        agent = _make_agent(tmp_config["tmp_path"])
        _write_trajectory(tmp_config["trajectory_path"], SAMPLE_TRAJECTORY_ENTRIES)

        result = agent._load_prior_judge_feedback()
        assert "Weak dimensions" in result
        assert "completeness" in result

    def test_caps_at_5_entries(
        self, tmp_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_config["tmp_path"])
        agent = _make_agent(tmp_config["tmp_path"])
        entries = []
        for i in range(10):
            entries.append(
                {
                    "judge_verdict": "FAIL",
                    "judge_score": 0.3,
                    "judge_feedback": f"Failure number {i}.",
                    "metadata": {"platform": "threads", "dimension_scores": {}},
                }
            )
        _write_trajectory(tmp_config["trajectory_path"], entries)

        result = agent._load_prior_judge_feedback()
        # Should have at most 5 failure lines (last 5)
        fail_lines = [line for line in result.splitlines() if line.startswith("- [")]
        assert len(fail_lines) <= 5
