"""Integration tests for Holus.

Covers:
  1. MarketingAgent full cycle (observe → reason → act → evaluate) with mocked LLM.
  2. content_queue round-trip (enqueue / approve / reject / mark_published).
  3. MCP server tool dispatch (skipped — no MCP dispatcher module found in integrations/).
  4. Authority Engine e2e (brand.yaml, authority framing, repurposing, anti-patterns).
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
import yaml

from holus.agents.marketing.content_queue import (
    QueuedContent,
    approve,
    enqueue,
    humanize,
    list_approved,
    list_pending,
    mark_published,
    reject,
)
from holus.core.config import HolusConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_holus_config(tmp_path: Path) -> HolusConfig:
    """Build a minimal HolusConfig that won't try to connect to Redis/Claude."""
    return HolusConfig(
        ANTHROPIC_API_KEY="",  # empty → triggers fallback path (no real API calls)
        REDIS_URL="redis://localhost:6379",
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
    )


def _make_fake_products(tmp_path: Path) -> None:
    """Write a minimal config/products.yaml under tmp_path."""
    products_dir = tmp_path / "config"
    products_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "products": {
            "pilaster": {
                "name": "Pilaster",
                "tagline": "AI image studio",
                "description": "Generate and edit images with AI.",
                "platforms": ["linkedin", "twitter"],
                "audience": "Designers",
                "pain_point": "Slow image iteration",
            }
        }
    }
    (products_dir / "products.yaml").write_text(yaml.dump(data))


def _make_fake_knowledge(tmp_path: Path) -> None:
    """Write placeholder knowledge files under tmp_path."""
    knowledge_dir = tmp_path / ".self-improvement" / "knowledge" / "current"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "platforms.md").write_text("Use concise, value-first content.")
    (knowledge_dir / "audience-profiles.md").write_text("Audience: tech professionals.")


def _make_fake_memory(tmp_path: Path) -> None:
    """Write a minimal MEMORY.md under tmp_path."""
    memory_dir = tmp_path / ".self-improvement"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "MEMORY.md").write_text("## Holus Memory\n\nNo entries yet.\n")


def _make_mock_redis() -> MagicMock:
    redis = MagicMock()
    redis.get.return_value = None  # kill switch not set
    redis.exists.return_value = 0  # kill switch key does not exist
    redis.publish.return_value = 1
    redis.xadd.return_value = "1234567890-0"
    redis.xrange.return_value = []
    redis.xread.return_value = []
    redis.set.return_value = True
    redis.delete.return_value = 1
    redis.pubsub.return_value = MagicMock()
    return redis


def _make_passing_health():
    """Return a HealthResult that passes all blocking checks."""
    from holus.core.cycle_state import HealthResult

    return HealthResult(
        blocking_ok=True,
        available_silos=["social_media", "pilaster", "genpeli"],
        warnings=[],
    )


# ---------------------------------------------------------------------------
# 1. MarketingAgent full cycle
# ---------------------------------------------------------------------------


class TestMarketingAgentCycle:
    """End-to-end test for the MarketingAgent observe→reason→act→evaluate loop."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path):
        """Prepare filesystem fixtures and patch infrastructure."""
        self.tmp = tmp_path

        # Create required files relative to tmp_path
        _make_fake_products(tmp_path)
        _make_fake_knowledge(tmp_path)
        _make_fake_memory(tmp_path)
        (tmp_path / "data" / "content-queue").mkdir(parents=True, exist_ok=True)

        # Patch cwd so relative Path() lookups in MarketingAgent resolve to tmp_path
        with patch("holus.agents.marketing.agent.Path") as _:
            pass  # We'll patch at a higher level below

    def test_full_cycle_with_mocked_llm(self, tmp_path: Path, monkeypatch):
        """
        Run MarketingAgent.run() with:
          - No Anthropic API key (forces fallback path so no real HTTP calls)
          - Mocked Redis (no real Redis needed)
          - Filesystem rooted at tmp_path via monkeypatching class-level Path constants

        Asserts all 4 stages completed and state is populated.
        """
        from holus.agents.marketing.agent import MarketingAgent

        # -- Patch path constants to point to tmp_path ---------------------
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._PRODUCTS_PATH",
            tmp_path / "config" / "products.yaml",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._KNOWLEDGE_DIR",
            tmp_path / ".self-improvement" / "knowledge" / "current",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._MEMORY_PATH",
            tmp_path / ".self-improvement" / "MEMORY.md",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._QUEUE_DIR",
            tmp_path / "data" / "content-queue",
        )
        traj_dir = tmp_path / ".self-improvement" / "memory"
        traj_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._TRAJECTORY_PATH",
            traj_dir / "trajectory.jsonl",
        )

        mock_redis = _make_mock_redis()

        # -- Patch Redis and EventBus so no real connections are attempted --
        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=mock_redis),
            patch("holus.agents.base.EventBus") as mock_event_bus_cls,
            patch(
                "holus.agents.marketing.agent.run_preflight_checks",
                return_value=_make_passing_health(),
            ),
        ):
            mock_event_bus_cls.return_value = MagicMock()

            config = _make_holus_config(tmp_path)
            agent = MarketingAgent(config=config)

            # Run the full cycle (no API key → fallback decisions + fallback content)
            final_state = asyncio.run(asyncio.wait_for(agent.run(), timeout=120))

        # -- Assertions -------------------------------------------------------
        # observe: product_updates loaded
        assert isinstance(final_state.get("product_updates"), dict)
        assert "products" in final_state["product_updates"]

        # reason: content_decisions produced (fallback path)
        decisions = final_state.get("content_decisions", [])
        assert isinstance(decisions, list)
        assert len(decisions) >= 1, "Expected at least one content decision"

        # act: generated_content produced
        generated = final_state.get("generated_content", [])
        assert isinstance(generated, list)
        assert len(generated) >= 1, "Expected at least one generated content piece"

        first = generated[0]
        assert "text" in first
        assert len(first["text"]) > 0

        # evaluate: evaluation dict present
        evaluation = final_state.get("evaluation", {})
        assert isinstance(evaluation, dict)
        assert "cycle_id" in evaluation or "decisions_count" in evaluation or len(evaluation) > 0

        # No error
        assert final_state.get("error") is None

    def test_observe_loads_products_and_knowledge(self, tmp_path: Path, monkeypatch):
        """Observe phase should load products.yaml and knowledge files."""
        from holus.agents.marketing.agent import MarketingAgent

        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._PRODUCTS_PATH",
            tmp_path / "config" / "products.yaml",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._KNOWLEDGE_DIR",
            tmp_path / ".self-improvement" / "knowledge" / "current",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._MEMORY_PATH",
            tmp_path / ".self-improvement" / "MEMORY.md",
        )
        monkeypatch.setattr(
            "holus.agents.marketing.agent.MarketingAgent._QUEUE_DIR",
            tmp_path / "data" / "content-queue",
        )

        mock_redis = _make_mock_redis()

        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=mock_redis),
            patch("holus.agents.base.EventBus") as mock_event_bus_cls,
        ):
            mock_event_bus_cls.return_value = MagicMock()
            config = _make_holus_config(tmp_path)
            agent = MarketingAgent(config=config)

            initial_state: dict[str, Any] = agent.default_state()
            result = asyncio.run(agent.observe(initial_state))  # type: ignore[arg-type]

        assert "products" in result.get("product_updates", {})
        assert isinstance(result.get("knowledge"), dict)
        assert "platforms" in result["knowledge"]
        assert "No entries yet" in result.get("memory_context", "")


# ---------------------------------------------------------------------------
# 2. content_queue round-trip
# ---------------------------------------------------------------------------


class TestContentQueueRoundTrip:
    """Tests for the content_queue enqueue/approve/reject/mark_published flow."""

    def _make_item(self, **kwargs) -> QueuedContent:
        defaults = {
            "product": "pilaster",
            "platform": "linkedin",
            "content_type": "tutorial",
            "topic": "Test topic",
            "text": "This is a test post about Pilaster.",
            "reasoning": "Integration test fixture",
        }
        defaults.update(kwargs)
        return QueuedContent(**defaults)

    def test_enqueue_and_list_pending(self, tmp_path: Path, monkeypatch):
        """enqueue → list_pending returns the item."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        item = self._make_item()
        path = enqueue(item)

        assert path.exists()
        assert path.suffix == ".yaml"

        pending = list_pending()
        assert len(pending) == 1
        assert pending[0].piece_id == item.piece_id
        assert pending[0].status == "pending_review"

    def test_approve_moves_to_approved(self, tmp_path: Path, monkeypatch):
        """enqueue → humanize → approve → list_approved returns the item."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        item = self._make_item()
        enqueue(item)

        humanize(item.piece_id, "This is a test post about Pilaster — edited.")
        approve(item.piece_id)

        pending = list_pending()
        assert len(pending) == 0

        approved = list_approved()
        assert len(approved) == 1
        assert approved[0].piece_id == item.piece_id
        assert approved[0].status == "approved"

    def test_reject_with_reason(self, tmp_path: Path, monkeypatch):
        """enqueue → reject → item status is 'rejected' with reason."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        item = self._make_item()
        enqueue(item)

        reject(item.piece_id, reason="Not relevant this week")

        pending = list_pending()
        assert len(pending) == 0

        # Read directly from file to verify rejection_reason
        queue_file = tmp_path / "queue" / f"{item.piece_id}.yaml"
        data = yaml.safe_load(queue_file.read_text())
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Not relevant this week"

    def test_mark_published(self, tmp_path: Path, monkeypatch):
        """enqueue → humanize → approve → mark_published → status is 'published'."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        item = self._make_item()
        enqueue(item)
        humanize(item.piece_id, "This is a test post about Pilaster — edited.")
        approve(item.piece_id)
        mark_published(item.piece_id, post_id="post_001")

        queue_file = tmp_path / "queue" / f"{item.piece_id}.yaml"
        data = yaml.safe_load(queue_file.read_text())
        assert data["status"] == "published"

    def test_multiple_items_in_queue(self, tmp_path: Path, monkeypatch):
        """Multiple items can be enqueued and listed."""
        import holus.agents.marketing.content_queue as cq

        monkeypatch.setattr(cq, "QUEUE_DIR", tmp_path / "queue")

        items = [self._make_item(topic=f"Topic {i}") for i in range(3)]
        for item in items:
            enqueue(item)

        pending = list_pending()
        assert len(pending) == 3

        # Approve one (humanize first per SPEC-032), reject another
        humanize(items[0].piece_id, "This is a test post about Pilaster — edited.")
        approve(items[0].piece_id)
        reject(items[1].piece_id, reason="Off-brand")

        pending = list_pending()
        assert len(pending) == 1
        assert pending[0].piece_id == items[2].piece_id

        approved = list_approved()
        assert len(approved) == 1
        assert approved[0].piece_id == items[0].piece_id


# ---------------------------------------------------------------------------
# 3. Authority Engine E2E
# ---------------------------------------------------------------------------

# Realistic mock responses for Claude API calls during authority engine cycle.

_MOCK_REASON_JSON = json.dumps(
    {
        "product": "pilaster",
        "platform": "linkedin",
        "content_type": "tutorial",
        "content_pillar": "builder_stories",
        "topic": "How I made AI image generation backend-agnostic",
        "hook": "I spent 6 months locked into one AI backend. Then I rebuilt everything.",
        "framework": "confession_framework",
        "reasoning": (
            "Builder stories demonstrate hands-on consulting expertise to CTOs "
            "and VPs Engineering evaluating AI transitions."
        ),
        "priority": 1,
        "estimated_engagement": "high",
        "repurpose_notes": "Strong story arc for Twitter. Visual for Instagram.",
    }
)

_MOCK_LINKEDIN_POST = (
    "I spent 6 months locked into one AI backend. Then I rebuilt everything.\n\n"
    "When I started Pilaster, I picked ComfyUI because it was the obvious choice. "
    "Fast iteration, great community, powerful nodes.\n\n"
    "But then I needed to run the same workflow on Replicate for scale. "
    "And Runway for video. And a custom pipeline for a client.\n\n"
    "So I built an abstraction layer. One interface, multiple backends.\n\n"
    "Three things I learned:\n\n"
    "-> Your AI stack will outlive any single vendor\n"
    "-> Abstraction is not premature if you have already been burned\n"
    "-> The real cost of lock-in is not technical -- it is strategic\n\n"
    "This pattern transfers to any AI deployment. "
    "If you are building AI systems, architect for change from day one.\n\n"
    "What is the biggest vendor dependency in your AI stack?\n\n"
    "#AI #ProductionAI #AIArchitecture #Builder"
)

_MOCK_REPURPOSED: dict[str, str] = {
    "twitter": (
        "I spent 6 months locked into one AI backend. Then I rebuilt everything.\n\n"
        "One interface. Multiple backends. Architect for change from day one."
    ),
    "instagram": (
        "I spent 6 months locked into one AI backend. Then I rebuilt everything.\n\n"
        "Built Pilaster on ComfyUI. Needed to scale to Replicate, Runway.\n\n"
        "-> Your AI stack will outlive any single vendor\n\n"
        "Save this if you are building AI systems.\n\n"
        "#AI #ProductionAI #Builder #MachineLearning #TechFounder"
    ),
    "threads": (
        "Honestly, I spent 6 months locked into one AI backend before I "
        "realized the mistake.\n\n"
        "Built an abstraction layer. One interface, any backend.\n\n"
        "What backend are you locked into?"
    ),
    "facebook": (
        "I spent 6 months locked into one AI backend. Then I rebuilt everything.\n\n"
        "When I started Pilaster, I picked ComfyUI. But then I needed Replicate "
        "for scale, Runway for video, and a custom pipeline for a client.\n\n"
        "So I built an abstraction layer. One interface, multiple backends.\n\n"
        "-> Your AI stack will outlive any single vendor\n"
        "-> The real cost of lock-in is not technical, it is strategic\n\n"
        "Comment if this resonates."
    ),
}

# Anti-pattern phrases that must NEVER appear in generated content.
_ANTI_PATTERN_PHRASES = [
    "leverage synergies",
    "game-changing",
    "unlock potential",
    "drive engagement",
    "Let's dive in",
    "In today's fast-paced world",
    "Furthermore",
    "Additionally",
    "Moreover",
]


def _make_claude_response_mock(text: str) -> MagicMock:
    """Build a mock Claude API response with the given text."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    return response


def _authority_claude_side_effect(**kwargs: Any) -> MagicMock:
    """Route mock Claude calls to the right response based on the prompt."""
    cached_prompt = kwargs.get("cached_prompt")
    system_prompt = getattr(cached_prompt, "system_prompt", "") if cached_prompt else ""

    # Reason stage (OPUS_STRATEGY_PROMPT)
    if "authority-building engine" in system_prompt:
        return _make_claude_response_mock(_MOCK_REASON_JSON)

    # Act stage — content generation (SONNET_CONTENT_PROMPT)
    if "writing a LinkedIn post as Camilo" in system_prompt:
        return _make_claude_response_mock(_MOCK_LINKEDIN_POST)

    # Act stage — repurposing (REPURPOSE_PROMPT)
    if "adapting a LinkedIn post for" in system_prompt.lower():
        for platform_key, text in _MOCK_REPURPOSED.items():
            if platform_key in system_prompt.lower():
                return _make_claude_response_mock(text)
        return _make_claude_response_mock(_MOCK_REPURPOSED["twitter"])

    # Niche research / extraction — return empty (not testing niche here)
    return _make_claude_response_mock("[]")


def _make_full_brand_yaml(tmp_path: Path) -> None:
    """Write a complete brand.yaml for authority engine testing."""
    brand_data = {
        "story": {
            "origin": "Colombian AI engineer who moved to NYC and built 3 AI products",
            "journey": [
                "Built Pilaster -- AI image generation platform with memory",
                "Built genpeli -- automated video editing pipeline",
                "Built invoz -- Whisper-powered audio ML API",
            ],
            "turning_point": "Companies need someone who has done it to guide their transformation.",
        },
        "positioning": {
            "one_liner": "I build AI systems that actually work in production.",
            "category": "AI implementation consultant / technical founder",
            "differentiation": [
                "Builder, not advisor",
                "Multi-product track record",
                "Full-stack AI",
            ],
            "what_i_am": [
                "A builder who shows the work",
                "A technical founder with production experience",
            ],
            "what_i_am_not": [
                "Not a guru selling a course",
                "Not an AI influencer chasing trends",
            ],
            "market": "NYC",
        },
        "offer": {
            "headline": "AI transition consulting for companies that want to ship",
        },
        "target_client": {
            "primary": {
                "title": "CTO / VP Engineering / Technical Founder",
                "company_size": "50-500 employees",
                "pain_points": [
                    "Board asking about AI strategy",
                    "Cannot get from POC to production",
                ],
            },
        },
        "products_as_proof": {
            "framing": "Products are evidence of builder expertise.",
            "pilaster": {
                "proof_narrative": "I built an AI image platform with memory.",
                "consulting_angle": "Backend abstraction patterns transfer to any AI deployment.",
            },
            "genpeli": {
                "proof_narrative": "I automated my video editing pipeline.",
                "consulting_angle": "Workflow automation and Whisper integration.",
            },
            "invoz": {
                "proof_narrative": "I built an audio ML API.",
                "consulting_angle": "API design and ML model serving.",
            },
        },
        "voice": {
            "archetype": "Builder-philosopher",
            "summary": "Direct, intellectually honest, first-person narratives.",
            "tone": [
                "First person always",
                "Short paragraphs",
                "Arrow bullets for technical lists",
                "Contractions always",
            ],
            "hooks": {
                "contrarian": "Most people are playing with AI. A few are building with it.",
                "confession": "I used to believe the formula was simple...",
            },
            "closers": {
                "question": "What would you build if you had 4x the output capacity?",
                "forward": "Still early. Still messy. But interesting.",
            },
            "language": {"primary": "en", "secondary": "es"},
        },
        "anti_patterns": {
            "language": [
                "leverage synergies",
                "drive engagement",
                "game-changing",
                "revolutionary",
            ],
            "style": [
                "Walls of text",
                "Passive voice",
                "Exclamation marks",
            ],
            "content": [
                "Financial advice",
                "Trading content",
            ],
        },
        "content_pillars": [
            {
                "id": "builder_stories",
                "name": "Builder Stories",
                "description": "I built X, here is what I learned",
                "frequency": "2x/week",
                "products": ["pilaster", "genpeli", "invoz"],
                "goal": "Demonstrate expertise through real experience",
            },
            {
                "id": "ai_frameworks",
                "name": "AI Implementation Frameworks",
                "description": "How to deploy AI in your company",
                "frequency": "1x/week",
                "products": [],
                "goal": "Provide actionable value to consulting prospects",
            },
            {
                "id": "industry_analysis",
                "name": "Industry Analysis",
                "description": "What is working in AI and what is hype",
                "frequency": "1x/week",
                "products": [],
                "goal": "Position as someone who sees the full landscape",
            },
            {
                "id": "results_proof",
                "name": "Results and Proof",
                "description": "Real numbers, real architectures, real outcomes",
                "frequency": "0.5x/week",
                "products": ["pilaster", "genpeli", "invoz"],
                "goal": "Back up authority with evidence",
            },
            {
                "id": "contrarian_takes",
                "name": "Contrarian Takes",
                "description": "Everyone is doing X wrong. Here is why.",
                "frequency": "0.5x/week",
                "products": [],
                "goal": "Stand out and spark discussion",
            },
        ],
        "platform_strategy": {
            "primary": "linkedin",
            "cadence": {
                "linkedin": "5x/week",
                "twitter": "3x/week",
                "instagram": "2x/week",
                "threads": "2x/week",
                "facebook": "1x/week",
            },
        },
    }
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "brand.yaml").write_text(yaml.dump(brand_data, sort_keys=False))


def _make_full_products(tmp_path: Path) -> None:
    """Write a full products.yaml for authority testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "products": {
            "pilaster": {
                "name": "Pilaster",
                "tagline": "AI image generation platform with memory",
                "description": "Backend-agnostic image generation with character registry.",
                "audience": "AI artists, content creators",
                "pain_point": "Fragmented AI image tools",
                "platforms": ["linkedin", "tiktok"],
            },
            "genpeli": {
                "name": "Genpeli",
                "tagline": "AI video editing pipeline",
                "description": "Automated video editing with silence removal and captions.",
                "audience": "Content creators, video editors",
                "pain_point": "Time-consuming video editing",
                "platforms": ["linkedin", "instagram"],
            },
            "invoz": {
                "name": "Invoz",
                "tagline": "Audio ML API",
                "description": "Whisper-powered transcription, diarization, silence detection.",
                "audience": "Developers",
                "pain_point": "Complex ML model serving",
                "platforms": ["linkedin", "twitter"],
            },
        }
    }
    (config_dir / "products.yaml").write_text(yaml.dump(data, sort_keys=False))


def _make_full_knowledge(tmp_path: Path) -> None:
    """Write knowledge files for authority engine testing."""
    kdir = tmp_path / ".self-improvement" / "knowledge" / "current"
    kdir.mkdir(parents=True, exist_ok=True)
    (kdir / "platforms.md").write_text(
        "# Platform Strategy\n\nLinkedIn: professional authority building, 5x/week.\n"
        "Twitter: condensed insights, 3x/week.\n"
    )
    (kdir / "audience-profiles.md").write_text(
        "# Audience\n\nPrimary: CTOs, VPs Engineering, founders at 50-500 employee companies.\n"
        "Pain: Board asking about AI, stuck between POC and production.\n"
    )
    (kdir / "content-formats.md").write_text(
        "# Content Formats\n\nTutorials, builder stories, frameworks, contrarian takes.\n"
    )
    (kdir / "viral-frameworks.md").write_text(
        "# Viral Frameworks\n\n"
        "Confession framework: start with what you got wrong, then the fix.\n"
        "Before/after: show transformation with real numbers.\n"
    )
    (kdir / "voice-profile.md").write_text(
        "# Voice Profile\n\n"
        "Archetype: Builder-philosopher. First person, short paragraphs, honest.\n"
    )
    mem_dir = tmp_path / ".self-improvement"
    (mem_dir / "MEMORY.md").write_text(
        "# Holus Memory\n\n"
        "LinkedIn tutorials get 2x engagement vs product announcements.\n"
        "Authority-framed content outperforms promotional content.\n"
    )


def _patch_agent_paths(monkeypatch: Any, tmp_path: Path) -> None:
    """Monkeypatch all MarketingAgent path constants to tmp_path."""
    prefix = "holus.agents.marketing.agent.MarketingAgent"
    monkeypatch.setattr(f"{prefix}._PRODUCTS_PATH", tmp_path / "config" / "products.yaml")
    monkeypatch.setattr(f"{prefix}._BRAND_PATH", tmp_path / "config" / "brand.yaml")
    monkeypatch.setattr(
        f"{prefix}._KNOWLEDGE_DIR", tmp_path / ".self-improvement" / "knowledge" / "current"
    )
    monkeypatch.setattr(f"{prefix}._MEMORY_PATH", tmp_path / ".self-improvement" / "MEMORY.md")
    monkeypatch.setattr(f"{prefix}._QUEUE_DIR", tmp_path / "data" / "content-queue")
    traj_dir = tmp_path / ".self-improvement" / "memory"
    traj_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(f"{prefix}._TRAJECTORY_PATH", traj_dir / "trajectory.jsonl")
    # Disable niche research (no queries file in temp dir)
    monkeypatch.setattr(f"{prefix}._NICHE_QUERIES_PATH", tmp_path / "nonexistent.md")


class TestAuthorityEngineE2E:
    """End-to-end authority engine test.

    Validates full marketing cycle with brand.yaml, authority framing,
    content repurposing, anti-pattern enforcement, and consulting targeting.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        _make_full_brand_yaml(tmp_path)
        _make_full_products(tmp_path)
        _make_full_knowledge(tmp_path)
        (tmp_path / "data" / "content-queue").mkdir(parents=True, exist_ok=True)

    def test_fallback_path_uses_authority_framing(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Full cycle with no API key uses fallback decisions with authority framing."""
        from holus.agents.marketing.agent import MarketingAgent

        _patch_agent_paths(monkeypatch, tmp_path)
        # Ensure no leaked env vars cause real LLM calls
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        mock_redis = _make_mock_redis()

        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=mock_redis),
            patch("holus.agents.base.EventBus") as mock_eb,
            patch(
                "holus.agents.marketing.agent.run_preflight_checks",
                return_value=_make_passing_health(),
            ),
        ):
            mock_eb.return_value = MagicMock()
            config = _make_holus_config(tmp_path)
            agent = MarketingAgent(config=config)
            state = asyncio.run(asyncio.wait_for(agent.run(), timeout=30))

        # Brand identity loaded
        brand = state.get("brand_identity", {})
        assert brand.get("voice", {}).get("archetype") == "Builder-philosopher"
        assert "build" in brand.get("positioning", {}).get("one_liner", "").lower()
        assert len(brand.get("content_pillars", [])) == 5

        # Fallback decisions use authority framing
        decisions = state.get("content_decisions", [])
        assert len(decisions) >= 1
        first_decision = decisions[0]
        assert first_decision["platform"] == "linkedin"
        assert first_decision["content_pillar"] == "builder_stories"
        assert (
            "learned" in first_decision["topic"].lower()
            or "built" in first_decision["topic"].lower()
        )

        # Fallback content uses first person
        generated = state.get("generated_content", [])
        assert len(generated) >= 1
        linkedin_piece = generated[0]
        text = linkedin_piece["text"]
        assert "I built" in text or "I learned" in text or "I " in text

        # No anti-patterns in fallback content
        for phrase in _ANTI_PATTERN_PHRASES:
            assert phrase not in text, f"Anti-pattern found in fallback content: {phrase}"

        # Evaluation logged
        evaluation = state.get("evaluation", {})
        assert evaluation.get("logged") is True
        assert evaluation.get("pieces_created", 0) >= 1

    def test_mocked_claude_full_authority_cycle(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Full cycle with mocked Claude returns authority-framed content + repurposing."""
        from holus.agents.marketing.agent import MarketingAgent

        _patch_agent_paths(monkeypatch, tmp_path)
        mock_redis = _make_mock_redis()

        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=mock_redis),
            patch("holus.agents.base.EventBus") as mock_eb,
            patch(
                "holus.agents.marketing.agent.run_preflight_checks",
                return_value=_make_passing_health(),
            ),
        ):
            mock_eb.return_value = MagicMock()
            config = HolusConfig(
                ANTHROPIC_API_KEY="sk-ant-test-authority",
                REDIS_URL="redis://localhost:6379",
                config_dir=tmp_path / "config",
                data_dir=tmp_path / "data",
            )
            agent = MarketingAgent(config=config)
            # Replace the claude client with our routing mock
            agent.claude = MagicMock()
            agent.claude.call = MagicMock(side_effect=_authority_claude_side_effect)
            agent.claude.sonnet_model = "claude-sonnet-4-6"

            state = asyncio.run(asyncio.wait_for(agent.run(), timeout=30))

        # --- Brand identity ---
        brand = state.get("brand_identity", {})
        assert brand.get("voice", {}).get("archetype") == "Builder-philosopher"
        positioning = brand.get("positioning", {})
        assert "production" in positioning.get("one_liner", "").lower()
        assert len(positioning.get("differentiation", [])) >= 3

        # --- Reason: authority-framed decision ---
        decisions = state.get("content_decisions", [])
        assert len(decisions) == 1
        decision = decisions[0]
        assert decision["platform"] == "linkedin"
        assert decision["content_pillar"] == "builder_stories"
        assert decision["hook"] != ""
        reasoning = decision["reasoning"].lower()
        assert any(word in reasoning for word in ("consulting", "expertise", "cto", "vp")), (
            f"Reasoning should target consulting prospects: {reasoning}"
        )

        # --- Act: LinkedIn content quality ---
        generated = state.get("generated_content", [])
        # 1 LinkedIn + 4 repurposed = 5 total
        assert len(generated) == 5, (
            f"Expected 5 pieces (1 LinkedIn + 4 repurposed), got {len(generated)}"
        )

        linkedin_pieces = [p for p in generated if p["platform"] == "linkedin"]
        assert len(linkedin_pieces) == 1
        linkedin_text = linkedin_pieces[0]["text"]

        # First person voice
        assert "I " in linkedin_text, "LinkedIn post should use first person"

        # No anti-patterns
        for phrase in _ANTI_PATTERN_PHRASES:
            assert phrase not in linkedin_text, f"Anti-pattern in LinkedIn post: {phrase}"

        # --- Repurposing: all 4 secondary platforms ---
        platforms_in_output = {p["platform"] for p in generated}
        assert "twitter" in platforms_in_output, "Missing Twitter repurposing"
        assert "instagram" in platforms_in_output, "Missing Instagram repurposing"
        assert "threads" in platforms_in_output, "Missing Threads repurposing"
        assert "facebook" in platforms_in_output, "Missing Facebook repurposing"

        # Twitter respects character limit
        twitter_pieces = [p for p in generated if p["platform"] == "twitter"]
        assert len(twitter_pieces) == 1
        assert len(twitter_pieces[0]["text"]) <= 280

        # Threads respects character limit
        threads_pieces = [p for p in generated if p["platform"] == "threads"]
        assert len(threads_pieces) == 1
        assert len(threads_pieces[0]["text"]) <= 500

        # --- Queue files created ---
        queue_files = list((tmp_path / "data" / "content-queue").glob("*.yaml"))
        assert len(queue_files) == 5, f"Expected 5 queue files, found {len(queue_files)}"

        # Verify queue file content
        first_queue = yaml.safe_load(queue_files[0].read_text())
        assert first_queue["status"] == "pending_review"
        assert "piece_id" in first_queue
        assert "text" in first_queue

        # --- Trajectory logged ---
        traj_path = tmp_path / ".self-improvement" / "memory" / "trajectory.jsonl"
        assert traj_path.exists()
        traj_lines = [line for line in traj_path.read_text().strip().split("\n") if line]
        assert len(traj_lines) >= 5, f"Expected 5+ trajectory entries, got {len(traj_lines)}"

        # Find the first agent-level entry (from TrajectoryLogger inside evaluate()).
        # CycleContext transition events also appear in the same file; skip those.
        agent_entries = [
            json.loads(ln)
            for ln in traj_lines
            if "agent_id" in json.loads(ln)
        ]
        assert agent_entries, "Expected at least one agent-level trajectory entry"
        first_entry = agent_entries[0]
        assert first_entry["agent_id"] == "marketing-agent"
        assert first_entry["task_type"] == "content_creation"
        assert first_entry["status"] == "success"

        # --- Evaluation summary ---
        evaluation = state.get("evaluation", {})
        assert evaluation.get("logged") is True
        assert evaluation.get("pieces_created") == 5
        assert evaluation.get("entries_written") == 5

    def test_brand_identity_validation(self, tmp_path: Path, monkeypatch: Any) -> None:
        """BrandIdentity model validates all sections from brand.yaml."""
        from holus.agents.marketing.agent import MarketingAgent

        _patch_agent_paths(monkeypatch, tmp_path)
        mock_redis = _make_mock_redis()

        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=mock_redis),
            patch("holus.agents.base.EventBus") as mock_eb,
        ):
            mock_eb.return_value = MagicMock()
            config = _make_holus_config(tmp_path)
            agent = MarketingAgent(config=config)
            initial = agent.default_state()
            result = asyncio.run(agent.observe(initial))  # type: ignore[arg-type]

        brand = result.get("brand_identity", {})

        # Story section
        assert "origin" in brand.get("story", {})
        journey = brand.get("story", {}).get("journey", [])
        assert len(journey) >= 3

        # Positioning
        pos = brand.get("positioning", {})
        assert pos.get("one_liner") != ""
        assert pos.get("category") != ""
        assert len(pos.get("what_i_am", [])) >= 2
        assert len(pos.get("what_i_am_not", [])) >= 2

        # Voice
        voice = brand.get("voice", {})
        assert voice.get("archetype") == "Builder-philosopher"
        assert len(voice.get("tone", [])) >= 4
        assert "contrarian" in voice.get("hooks", {})
        assert "question" in voice.get("closers", {})

        # Anti-patterns
        anti = brand.get("anti_patterns", {})
        assert len(anti.get("language", [])) >= 3
        assert len(anti.get("style", [])) >= 2
        assert len(anti.get("content", [])) >= 1

        # Content pillars
        pillars = brand.get("content_pillars", [])
        assert len(pillars) == 5
        pillar_ids = {p["id"] for p in pillars}
        assert pillar_ids == {
            "builder_stories",
            "ai_frameworks",
            "industry_analysis",
            "results_proof",
            "contrarian_takes",
        }

        # Products as proof
        proof = brand.get("products_as_proof", {})
        assert "pilaster" in proof
        assert "genpeli" in proof
        assert "invoz" in proof

    def test_no_anti_patterns_in_repurposed_content(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Anti-pattern phrases must be absent from all repurposed platform content."""
        from holus.agents.marketing.agent import MarketingAgent

        _patch_agent_paths(monkeypatch, tmp_path)
        mock_redis = _make_mock_redis()

        with (
            patch("holus.agents.base.redis.Redis.from_url", return_value=mock_redis),
            patch("holus.agents.base.EventBus") as mock_eb,
        ):
            mock_eb.return_value = MagicMock()
            config = HolusConfig(
                ANTHROPIC_API_KEY="sk-ant-test-antipattern",
                REDIS_URL="redis://localhost:6379",
                config_dir=tmp_path / "config",
                data_dir=tmp_path / "data",
            )
            agent = MarketingAgent(config=config)
            agent.claude = MagicMock()
            agent.claude.call = MagicMock(side_effect=_authority_claude_side_effect)
            agent.claude.sonnet_model = "claude-sonnet-4-6"

            state = asyncio.run(asyncio.wait_for(agent.run(), timeout=30))

        for piece in state.get("generated_content", []):
            text = piece.get("text", "")
            platform = piece.get("platform", "unknown")
            for phrase in _ANTI_PATTERN_PHRASES:
                assert phrase not in text, f"Anti-pattern '{phrase}' found in {platform} content"


# ---------------------------------------------------------------------------
# 4. MCP server tool dispatch
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "No MCP dispatcher module found in src/holus/integrations/. "
        "Holus calls external MCP servers (genpeli-mcp, social-media-mcp, pilaster-mcp) "
        "via HTTP but does not host an MCP server itself. "
        "MCP integration tests should be added when holus/integrations/mcp/ exists."
    )
)
def test_mcp_tool_dispatch_placeholder():
    """Placeholder for MCP tool dispatch tests."""
    pass
