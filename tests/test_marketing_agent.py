"""Tests for holus.agents.marketing.agent.

Tests cover all four stages of the marketing agent:
  - observe: Load products, knowledge, memory
  - reason: Generate content decisions with Claude
  - act: Generate platform-specific content
  - evaluate: Log trajectory entries
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from holus.agents.marketing.agent import MarketingAgent
from holus.agents.marketing.models import ContentDecision, ContentType, Platform
from holus.core.config import AgentConfig, HolusConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_config_files(tmp_path):
    """Create temporary config files for testing."""
    # Products config
    products_path = tmp_path / "config" / "products.yaml"
    products_path.parent.mkdir(parents=True, exist_ok=True)
    products_data = {
        "products": {
            "pilaster": {
                "name": "Pilaster.ai",
                "tagline": "AI image generation made easy",
                "description": "Generate stunning AI images with simple prompts",
                "audience": "content creators, marketers",
                "pain_point": "Complex AI tools",
                "platforms": ["linkedin", "twitter", "instagram"],
            },
            "genpeli": {
                "name": "Genpeli",
                "tagline": "Smart video editing automation",
                "description": "Automated video editing pipeline",
                "audience": "video creators, influencers",
                "pain_point": "Time-consuming video editing",
                "platforms": ["tiktok", "youtube"],
            },
        }
    }
    products_path.write_text(yaml.dump(products_data))

    # Knowledge files
    knowledge_dir = tmp_path / ".self-improvement" / "knowledge" / "current"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    (knowledge_dir / "platforms.md").write_text(
        "# Platform Guidelines\n\nLinkedIn: Professional, thought leadership\n"
        "Twitter: Concise, engaging hooks\n"
        "TikTok: Visual, fast-paced\n"
    )

    (knowledge_dir / "audience-profiles.md").write_text(
        "# Audience Profiles\n\n"
        "Content creators: Looking for time-saving tools\n"
        "Marketers: Need consistent, high-quality content\n"
    )

    (knowledge_dir / "content-formats.md").write_text(
        "# Content Formats\n\n"
        "Tutorials: Step-by-step guides (high engagement)\n"
        "Demos: Show the product in action\n"
        "Tips: Quick actionable advice\n"
    )

    # Memory file
    memory_path = tmp_path / ".self-improvement" / "MEMORY.md"
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(
        "# Marketing Memory\n\n"
        "## Past Performance\n\n"
        "- LinkedIn tutorials get 2x engagement\n"
        "- Twitter threads underperform\n"
        "- Best posting time: 9-11am EST\n"
    )

    # Brand config
    brand_path = tmp_path / "config" / "brand.yaml"
    brand_data = {
        "story": {
            "origin": "Colombian AI engineer who moved to NYC",
            "journey": ["Built Pilaster", "Built genpeli"],
        },
        "positioning": {
            "one_liner": "I build AI systems that actually work in production.",
            "category": "AI implementation consultant",
            "differentiation": ["Builder, not advisor"],
            "what_i_am": ["A builder who shows the work"],
            "what_i_am_not": ["Not a guru selling a course"],
            "market": "NYC",
        },
        "voice": {
            "archetype": "Builder-philosopher",
            "summary": "Direct, intellectually honest",
            "tone": ["First person always", "Short paragraphs"],
            "hooks": {"contrarian": "Most people are playing with AI."},
            "closers": {"question": "What would you build?"},
            "language": {"primary": "en", "secondary": "es"},
        },
        "anti_patterns": {
            "language": ["leverage synergies", "game-changing"],
            "style": ["Walls of text"],
            "content": ["Financial advice"],
        },
        "content_pillars": [
            {
                "id": "builder_stories",
                "name": "Builder Stories",
                "description": "I built X, here's what I learned",
                "frequency": "2x/week",
                "products": ["pilaster", "genpeli"],
                "goal": "Demonstrate expertise",
            }
        ],
        "platform_strategy": {
            "primary": "linkedin",
            "cadence": {"linkedin": "5x/week", "twitter": "3x/week"},
        },
    }
    brand_path.write_text(yaml.dump(brand_data))

    # Queue directory
    queue_dir = tmp_path / "data" / "content-queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    # Trajectory file
    trajectory_path = tmp_path / ".self-improvement" / "memory" / "trajectory.jsonl"
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    trajectory_path.touch()

    return {
        "products_path": products_path,
        "brand_path": brand_path,
        "knowledge_dir": knowledge_dir,
        "memory_path": memory_path,
        "queue_dir": queue_dir,
        "trajectory_path": trajectory_path,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def mock_config(temp_config_files):
    """Mock HolusConfig with test paths."""
    config = MagicMock(spec=HolusConfig)
    config.anthropic_api_key = "sk-ant-test-key"
    config.opus_model = "claude-opus-4-6"
    config.sonnet_model = "claude-sonnet-4-6"
    config.redis_url = "redis://localhost:6379"
    config.mem0_api_url = "http://localhost:8000"
    config.langfuse_public_key = None
    config.langfuse_secret_key = None
    config.langfuse_host = "http://localhost:3001"
    config.posting_api_key = ""
    config.social_media_api_base_url = "http://localhost:8000"

    agent_config = AgentConfig(
        enabled=True,
        schedule="0 10 * * *",
        default_model_tier="operational",
        mem0_scope="marketing-agent",
    )
    config.get_agent_config = MagicMock(return_value=agent_config)

    return config


@pytest.fixture
def mock_claude_client():
    """Mock Claude client with realistic responses."""
    client = MagicMock()

    def make_response(text: str):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text
        response.content = [text_block]
        response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=80,
            cache_creation_input_tokens=20,
        )
        return response

    client.call = MagicMock(side_effect=lambda **kwargs: make_response("Mock response"))
    client._cost_log = []
    client.get_costs = MagicMock(return_value=[])

    return client


@pytest.fixture
def marketing_agent(mock_config, temp_config_files, monkeypatch):
    """Create a MarketingAgent with mocked dependencies."""
    # Monkeypatch the class-level paths to use temp paths
    monkeypatch.setattr(MarketingAgent, "_PRODUCTS_PATH", temp_config_files["products_path"])
    monkeypatch.setattr(MarketingAgent, "_BRAND_PATH", temp_config_files["brand_path"])
    monkeypatch.setattr(MarketingAgent, "_KNOWLEDGE_DIR", temp_config_files["knowledge_dir"])
    monkeypatch.setattr(MarketingAgent, "_MEMORY_PATH", temp_config_files["memory_path"])
    monkeypatch.setattr(MarketingAgent, "_QUEUE_DIR", temp_config_files["queue_dir"])
    monkeypatch.setattr(MarketingAgent, "_TRAJECTORY_PATH", temp_config_files["trajectory_path"])

    # Mock Redis and other infrastructure
    with (
        patch("holus.agents.base.redis.Redis") as mock_redis_cls,
        patch("holus.agents.base.EventBus") as mock_event_bus_cls,
        patch("holus.agents.base.KillSwitch") as mock_kill_switch_cls,
        patch("holus.agents.base.HolusClaudeClient") as mock_claude_cls,
    ):
        mock_redis = MagicMock()
        mock_redis_cls.from_url.return_value = mock_redis

        mock_event_bus = MagicMock()
        mock_event_bus_cls.return_value = mock_event_bus

        mock_kill_switch = MagicMock()
        mock_kill_switch.is_active.return_value = False
        mock_kill_switch_cls.return_value = mock_kill_switch

        mock_claude = MagicMock()
        mock_claude_cls.return_value = mock_claude

        agent = MarketingAgent(config=mock_config)
        agent.claude = mock_claude  # Ensure we use the mock
        agent.kill_switch = mock_kill_switch
        agent.event_bus = mock_event_bus
        agent._redis = mock_redis

        yield agent


# ---------------------------------------------------------------------------
# Test Observe Stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observe_loads_all_data(marketing_agent, temp_config_files):
    """Observe stage loads products, knowledge, and memory."""
    state = marketing_agent.default_state()

    result = await marketing_agent.observe(state)

    # Products loaded
    assert "products" in result["product_updates"]
    assert "pilaster" in result["product_updates"]["products"]
    assert "genpeli" in result["product_updates"]["products"]

    # Knowledge loaded
    assert "platforms" in result["knowledge"]
    assert "audience-profiles" in result["knowledge"]
    assert "content-formats" in result["knowledge"]
    assert "LinkedIn" in result["knowledge"]["platforms"]

    # Memory loaded
    assert "Past Performance" in result["memory_context"]
    assert "LinkedIn tutorials" in result["memory_context"]

    # Queue size tracked
    assert result["queue_size_before"] == 0


@pytest.mark.asyncio
async def test_observe_handles_missing_files(marketing_agent, temp_config_files, monkeypatch):
    """Observe stage gracefully handles missing config files."""
    # Point to non-existent paths
    monkeypatch.setattr(MarketingAgent, "_PRODUCTS_PATH", Path("/nonexistent/products.yaml"))
    monkeypatch.setattr(MarketingAgent, "_KNOWLEDGE_DIR", Path("/nonexistent/knowledge"))
    monkeypatch.setattr(MarketingAgent, "_MEMORY_PATH", Path("/nonexistent/MEMORY.md"))

    state = marketing_agent.default_state()
    result = await marketing_agent.observe(state)

    # Should return empty/default values without crashing
    assert result["product_updates"] == {}
    assert result["knowledge"] == {}
    assert result["memory_context"] == ""
    assert result["queue_size_before"] == 0


@pytest.mark.asyncio
async def test_observe_with_existing_queue_items(marketing_agent, temp_config_files):
    """Observe stage counts existing queue items."""
    # Create some queue items (YAML format, matching content_queue.py)
    queue_dir = temp_config_files["queue_dir"]
    (queue_dir / "item1.yaml").write_text("status: pending\n")
    (queue_dir / "item2.yaml").write_text("status: pending\n")
    (queue_dir / "item3.yaml").write_text("status: pending\n")

    state = marketing_agent.default_state()
    result = await marketing_agent.observe(state)

    assert result["queue_size_before"] == 3


# ---------------------------------------------------------------------------
# Test Analytics in Observe Stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observe_fetches_analytics_when_configured(marketing_agent, mock_config):
    """Observe populates analytics when POSTING_API_KEY is set."""
    mock_config.posting_api_key = "test-posting-key"
    mock_config.social_media_api_base_url = "http://localhost:8000"

    mock_analytics = {"total_posts": 10, "success_rate": 0.9}
    mock_top_posts = {"posts": [{"id": 1, "content": "Top post"}]}

    with patch("holus.agents.marketing.agent.SocialMediaClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get_analytics = AsyncMock(return_value=mock_analytics)
        mock_client.get_top_posts = AsyncMock(return_value=mock_top_posts)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        state = marketing_agent.default_state()
        result = await marketing_agent.observe(state)

        assert result["analytics"]["summary"] == mock_analytics
        assert result["analytics"]["top_posts"] == mock_top_posts
        mock_client.get_analytics.assert_awaited_once_with(days=7)
        mock_client.get_top_posts.assert_awaited_once_with(limit=5, days=30)


@pytest.mark.asyncio
async def test_observe_skips_analytics_without_api_key(marketing_agent, mock_config):
    """Observe returns empty analytics when POSTING_API_KEY is not set."""
    mock_config.posting_api_key = ""

    state = marketing_agent.default_state()
    result = await marketing_agent.observe(state)

    assert result["analytics"] == {}


@pytest.mark.asyncio
async def test_observe_analytics_graceful_degradation(marketing_agent, mock_config):
    """Observe continues without analytics if API is unreachable."""
    mock_config.posting_api_key = "test-posting-key"
    mock_config.social_media_api_base_url = "http://localhost:8000"

    with patch("holus.agents.marketing.agent.SocialMediaClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get_analytics = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        state = marketing_agent.default_state()
        result = await marketing_agent.observe(state)

        # Analytics should be empty but observe should succeed
        assert result["analytics"] == {}
        # Other data should still be loaded
        assert "product_updates" in result
        assert "knowledge" in result


@pytest.mark.asyncio
async def test_fetch_analytics_returns_structured_data(marketing_agent, mock_config):
    """_fetch_analytics returns dict with summary and top_posts keys."""
    mock_config.posting_api_key = "test-posting-key"
    mock_config.social_media_api_base_url = "http://localhost:8000"

    mock_analytics = {
        "total_posts": 15,
        "success_rate": 0.93,
        "platforms": {"linkedin": {"posts": 8}},
    }
    mock_top_posts = {
        "posts": [
            {"id": 1, "content": "Post A", "platform": "linkedin"},
            {"id": 2, "content": "Post B", "platform": "twitter"},
        ],
    }

    with patch("holus.agents.marketing.agent.SocialMediaClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get_analytics = AsyncMock(return_value=mock_analytics)
        mock_client.get_top_posts = AsyncMock(return_value=mock_top_posts)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await marketing_agent._fetch_analytics()

        assert "summary" in result
        assert "top_posts" in result
        assert result["summary"]["total_posts"] == 15
        assert len(result["top_posts"]["posts"]) == 2


# ---------------------------------------------------------------------------
# Test Reason Stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reason_generates_decisions_with_claude(marketing_agent):
    """Reason stage calls Claude and parses content decisions."""
    state = marketing_agent.default_state()
    state["product_updates"] = {
        "products": {"pilaster": {"name": "Pilaster", "platforms": ["linkedin", "twitter"]}}
    }
    state["knowledge"] = {"platforms": "LinkedIn is professional"}
    state["memory_context"] = "Tutorials perform well"
    state["analytics"] = {}

    # Mock Claude response with valid JSON
    decisions_json = json.dumps(
        [
            {
                "product": "pilaster",
                "platform": "linkedin",
                "content_type": "tutorial",
                "topic": "How to generate AI images",
                "reasoning": "Educational content works well on LinkedIn",
                "priority": 1,
                "estimated_engagement": "high",
            },
            {
                "product": "pilaster",
                "platform": "twitter",
                "content_type": "tips",
                "topic": "5 AI image tips",
                "reasoning": "Quick tips perform on Twitter",
                "priority": 2,
                "estimated_engagement": "medium",
            },
        ]
    )

    def mock_call(**kwargs):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = decisions_json
        response.content = [text_block]
        return response

    marketing_agent.claude.call = mock_call

    result = await marketing_agent.reason(state)

    # Decisions parsed correctly
    assert len(result["content_decisions"]) == 2
    assert result["content_decisions"][0]["product"] == "pilaster"
    assert result["content_decisions"][0]["platform"] == "linkedin"
    assert result["content_decisions"][1]["priority"] == 2

    # Strategy reasoning captured
    assert result["strategy_reasoning"] == decisions_json


@pytest.mark.asyncio
async def test_reason_handles_claude_failure(marketing_agent):
    """Reason stage falls back to default decisions when Claude fails."""
    state = marketing_agent.default_state()
    state["product_updates"] = {
        "products": {
            "pilaster": {"name": "Pilaster", "platforms": ["linkedin"]},
            "genpeli": {"name": "Genpeli", "platforms": ["tiktok"]},
        }
    }
    state["knowledge"] = {}
    state["memory_context"] = ""

    # Mock Claude to raise an exception
    marketing_agent.claude.call = MagicMock(side_effect=Exception("API error"))

    result = await marketing_agent.reason(state)

    # Fallback decisions generated
    assert len(result["content_decisions"]) > 0
    assert "Fallback strategy" in result["strategy_reasoning"]

    # Fallback decisions are valid
    decision = result["content_decisions"][0]
    assert decision["product"] in ["pilaster", "genpeli"]
    assert decision["content_type"] == "tutorial"


@pytest.mark.asyncio
async def test_reason_limits_to_three_decisions(marketing_agent):
    """Reason stage limits decisions to top 3 by priority."""
    state = marketing_agent.default_state()
    state["product_updates"] = {"products": {"pilaster": {}}}
    state["knowledge"] = {}
    state["memory_context"] = ""

    # Mock Claude response with 5 decisions
    decisions_json = json.dumps(
        [
            {
                "product": "pilaster",
                "platform": "linkedin",
                "content_type": "tutorial",
                "topic": f"Topic {i}",
                "reasoning": f"Reason {i}",
                "priority": i,
                "estimated_engagement": "medium",
            }
            for i in range(1, 6)
        ]
    )

    def mock_call(**kwargs):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = decisions_json
        response.content = [text_block]
        return response

    marketing_agent.claude.call = mock_call

    result = await marketing_agent.reason(state)

    # Only top 3 decisions kept
    assert len(result["content_decisions"]) == 3
    # Sorted by priority (lowest first)
    assert result["content_decisions"][0]["priority"] == 1
    assert result["content_decisions"][1]["priority"] == 2
    assert result["content_decisions"][2]["priority"] == 3


@pytest.mark.asyncio
async def test_reason_parses_json_with_markdown_fence(marketing_agent):
    """Reason stage extracts JSON from markdown code fences."""
    state = marketing_agent.default_state()
    state["product_updates"] = {"products": {"pilaster": {}}}
    state["knowledge"] = {}
    state["memory_context"] = ""

    # Mock Claude response with markdown fence
    decisions_json = """Here are my recommendations:

```json
[
  {
    "product": "pilaster",
    "platform": "linkedin",
    "content_type": "tutorial",
    "topic": "AI image basics",
    "reasoning": "Educational",
    "priority": 1,
    "estimated_engagement": "high"
  }
]
```

These decisions prioritize educational content.
"""

    def mock_call(**kwargs):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = decisions_json
        response.content = [text_block]
        return response

    marketing_agent.claude.call = mock_call

    result = await marketing_agent.reason(state)

    assert len(result["content_decisions"]) == 1
    assert result["content_decisions"][0]["topic"] == "AI image basics"


# ---------------------------------------------------------------------------
# Test Act Stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_act_generates_content_for_decisions(marketing_agent, temp_config_files):
    """Act stage generates text for each content decision."""
    state = marketing_agent.default_state()
    state["cycle_id"] = "test-cycle"
    state["content_decisions"] = [
        {
            "product": "pilaster",
            "platform": "linkedin",
            "content_type": "tutorial",
            "topic": "AI image generation basics",
            "reasoning": "Educational content",
            "priority": 1,
            "estimated_engagement": "high",
        }
    ]
    state["knowledge"] = {"platforms": "LinkedIn guidelines"}
    state["product_updates"] = {
        "products": {
            "pilaster": {
                "name": "Pilaster",
                "tagline": "AI images made easy",
                "description": "Generate stunning AI images",
            }
        }
    }

    # Mock Claude response
    generated_text = "Here's how to generate amazing AI images with Pilaster..."

    def mock_call(**kwargs):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = generated_text
        response.content = [text_block]
        return response

    marketing_agent.claude.call = mock_call

    result = await marketing_agent.act(state)

    # Content generated
    assert len(result["generated_content"]) == 1
    piece = result["generated_content"][0]
    assert piece["text"] == generated_text
    assert piece["platform"] == "linkedin"
    assert piece["decision"]["topic"] == "AI image generation basics"

    # Post results tracked (may include repurposing failure entries)
    successful = [r for r in result["post_results"] if r.get("status") == "pending_review"]
    assert len(successful) == 1
    assert "queue_path" in successful[0]

    # Queue file created (YAML format)
    queue_files = list(temp_config_files["queue_dir"].glob("*.yaml"))
    assert len(queue_files) == 1

    # Queue file content valid
    queue_data = yaml.safe_load(queue_files[0].read_text())
    assert queue_data["text"] == generated_text
    assert queue_data["platform"] == "linkedin"


@pytest.mark.asyncio
async def test_act_enforces_platform_character_limits(marketing_agent, temp_config_files):
    """Act stage truncates content to platform limits."""
    state = marketing_agent.default_state()
    state["cycle_id"] = "test-cycle"
    state["content_decisions"] = [
        {
            "product": "pilaster",
            "platform": "twitter",
            "content_type": "tips",
            "topic": "Quick tips",
            "reasoning": "Twitter engagement",
            "priority": 1,
            "estimated_engagement": "medium",
        }
    ]
    state["knowledge"] = {}
    state["product_updates"] = {"products": {"pilaster": {}}}

    # Mock Claude response with long text (> 280 chars)
    long_text = "A" * 500

    def mock_call(**kwargs):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = long_text
        response.content = [text_block]
        return response

    marketing_agent.claude.call = mock_call

    result = await marketing_agent.act(state)

    # Content truncated to Twitter limit (280 chars)
    piece = result["generated_content"][0]
    assert len(piece["text"]) <= 280
    assert piece["text"].endswith("...")


@pytest.mark.asyncio
async def test_act_uses_fallback_when_no_api_key(marketing_agent, temp_config_files):
    """Act stage uses template fallback when API key not available."""
    # Remove API key
    marketing_agent.config.anthropic_api_key = None

    state = marketing_agent.default_state()
    state["cycle_id"] = "test-cycle"
    state["content_decisions"] = [
        {
            "product": "pilaster",
            "platform": "linkedin",
            "content_type": "tutorial",
            "topic": "AI workflows",
            "reasoning": "Educational",
            "priority": 1,
            "estimated_engagement": "medium",
        }
    ]
    state["knowledge"] = {}
    state["product_updates"] = {"products": {"pilaster": {}}}

    result = await marketing_agent.act(state)

    # Fallback content generated
    piece = result["generated_content"][0]
    assert "workflows" in piece["text"].lower()  # Case-insensitive check
    assert piece["model_used"] == "template-fallback"


@pytest.mark.asyncio
async def test_act_handles_invalid_decision_payload(marketing_agent, temp_config_files):
    """Act stage handles invalid content decision gracefully."""
    state = marketing_agent.default_state()
    state["cycle_id"] = "test-cycle"
    state["content_decisions"] = [
        {
            "invalid": "decision",
            "missing": "required fields",
        }
    ]
    state["knowledge"] = {}
    state["product_updates"] = {}

    # Mock fallback behavior (no API key)
    marketing_agent.config.anthropic_api_key = None

    result = await marketing_agent.act(state)

    # Invalid decision gets coerced to defaults, content still generated
    # This is actually the current behavior - it's resilient
    assert len(result["post_results"]) >= 1
    # Check that it processed something (even with defaults)
    primary = [r for r in result["post_results"] if r.get("phase") != "repurposing"]
    assert len(primary) >= 1
    assert primary[0]["status"] in ["pending_review", "failed"]


@pytest.mark.asyncio
async def test_act_processes_multiple_decisions(marketing_agent, temp_config_files):
    """Act stage processes multiple content decisions."""
    state = marketing_agent.default_state()
    state["cycle_id"] = "test-cycle"
    state["content_decisions"] = [
        {
            "product": "pilaster",
            "platform": "linkedin",
            "content_type": "tutorial",
            "topic": "Topic 1",
            "reasoning": "Reason 1",
            "priority": 1,
            "estimated_engagement": "high",
        },
        {
            "product": "genpeli",
            "platform": "tiktok",
            "content_type": "demo",
            "topic": "Topic 2",
            "reasoning": "Reason 2",
            "priority": 2,
            "estimated_engagement": "medium",
        },
    ]
    state["knowledge"] = {}
    state["product_updates"] = {"products": {"pilaster": {}, "genpeli": {}}}

    def mock_call(**kwargs):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Generated content"
        response.content = [text_block]
        return response

    marketing_agent.claude.call = mock_call

    result = await marketing_agent.act(state)

    # Both pieces generated
    assert len(result["generated_content"]) == 2
    assert result["generated_content"][0]["decision"]["product"] == "pilaster"
    assert result["generated_content"][1]["decision"]["product"] == "genpeli"

    # Both results tracked (may include repurposing failure entries)
    successful = [r for r in result["post_results"] if r.get("status") == "pending_review"]
    assert len(successful) == 2

    # Both queue files created (YAML format)
    queue_files = list(temp_config_files["queue_dir"].glob("*.yaml"))
    assert len(queue_files) == 2


# ---------------------------------------------------------------------------
# Test Evaluate Stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_writes_trajectory_entries(marketing_agent, temp_config_files):
    """Evaluate stage logs successful content to trajectory."""
    state = marketing_agent.default_state()
    state["cycle_id"] = "test-cycle-001"
    state["strategy_reasoning"] = "Educational content strategy"
    state["generated_content"] = [
        {
            "piece_id": "piece-001",
            "decision": {
                "product": "pilaster",
                "platform": "linkedin",
                "content_type": "tutorial",
                "topic": "AI basics",
                "reasoning": "Educational",
            },
            "text": "Content text",
            "platform": "linkedin",
            "model_used": "claude-sonnet-4-6",
            "status": "pending_review",
        }
    ]
    state["post_results"] = [
        {
            "piece_id": "piece-001",
            "status": "pending_review",
            "queue_path": "/path/to/queue.json",
        }
    ]
    state["queue_size_before"] = 0

    result = await marketing_agent.evaluate(state)

    # Evaluation summary
    assert result["evaluation"]["logged"] is True
    assert result["evaluation"]["entries_written"] == 1
    assert result["evaluation"]["pieces_created"] == 1
    assert result["evaluation"]["cycle_id"] == "test-cycle-001"

    # Trajectory file has entries
    trajectory_path = temp_config_files["trajectory_path"]
    content = trajectory_path.read_text()
    assert len(content.strip()) > 0

    # Parse JSONL
    entries = [json.loads(line) for line in content.strip().split("\n") if line]
    assert len(entries) == 1

    entry = entries[0]
    assert entry["agent_id"] == "marketing-agent"
    assert entry["task_type"] == "content_creation"
    assert "tutorial about AI basics" in entry["task_summary"]
    assert entry["status"] == "success"
    assert entry["metadata"]["cycle_id"] == "test-cycle-001"
    assert entry["metadata"]["product"] == "pilaster"


@pytest.mark.asyncio
async def test_evaluate_logs_failures(marketing_agent, temp_config_files):
    """Evaluate stage logs failed content generation attempts."""
    state = marketing_agent.default_state()
    state["cycle_id"] = "test-cycle-002"
    state["strategy_reasoning"] = "Strategy"
    state["generated_content"] = []
    state["post_results"] = [
        {
            "status": "failed",
            "error": "Claude API timeout",
            "decision": {
                "product": "pilaster",
                "platform": "linkedin",
                "content_type": "tutorial",
                "topic": "Failed topic",
            },
        }
    ]
    state["queue_size_before"] = 0

    result = await marketing_agent.evaluate(state)

    # Evaluation summary
    assert result["evaluation"]["entries_written"] == 1
    assert result["evaluation"]["pieces_created"] == 0

    # Trajectory has failure entry
    trajectory_path = temp_config_files["trajectory_path"]
    entries = [json.loads(line) for line in trajectory_path.read_text().strip().split("\n") if line]

    assert len(entries) == 1
    entry = entries[0]
    assert entry["status"] == "error"
    assert entry["error_message"] == "Claude API timeout"


@pytest.mark.asyncio
async def test_evaluate_tracks_queue_size_change(marketing_agent, temp_config_files):
    """Evaluate stage tracks queue size before and after."""
    # Create initial queue items
    queue_dir = temp_config_files["queue_dir"]
    (queue_dir / "existing.yaml").write_text("status: pending\n")

    state = marketing_agent.default_state()
    state["cycle_id"] = "test-cycle-003"
    state["strategy_reasoning"] = "Strategy"
    state["generated_content"] = [
        {
            "piece_id": "new-piece",
            "decision": {
                "product": "pilaster",
                "platform": "linkedin",
                "content_type": "tutorial",
                "topic": "Topic",
            },
            "text": "Text",
            "platform": "linkedin",
            "model_used": "claude-sonnet-4-6",
        }
    ]
    state["post_results"] = []
    state["queue_size_before"] = 1

    # Add new queue item (simulating act stage)
    (queue_dir / "new.yaml").write_text("status: pending\n")

    result = await marketing_agent.evaluate(state)

    assert result["evaluation"]["queue_size_before"] == 1
    assert result["evaluation"]["queue_size_after"] == 2


# ---------------------------------------------------------------------------
# Test Helper Methods
# ---------------------------------------------------------------------------


def test_coerce_decision_valid(marketing_agent):
    """_coerce_decision converts dict to ContentDecision."""
    payload = {
        "product": "pilaster",
        "platform": "linkedin",
        "content_type": "tutorial",
        "topic": "Test topic",
        "reasoning": "Test reasoning",
        "priority": 1,
        "estimated_engagement": "high",
    }

    decision = marketing_agent._coerce_decision(payload)

    assert decision is not None
    assert decision.product == "pilaster"
    assert decision.platform == Platform.LINKEDIN
    assert decision.content_type == ContentType.TUTORIAL
    assert decision.priority == 1


def test_coerce_decision_with_aliases(marketing_agent):
    """_coerce_decision handles platform and content type aliases."""
    payload = {
        "product": "genpeli",
        "platform": "x",  # Alias for twitter
        "content_type": "technical_post",  # Alias for educational
        "topic": "Test",
        "reasoning": "Test",
    }

    decision = marketing_agent._coerce_decision(payload)

    assert decision is not None
    assert decision.platform == Platform.TWITTER
    assert decision.content_type == ContentType.EDUCATIONAL


def test_coerce_decision_invalid_payload(marketing_agent):
    """_coerce_decision returns None for invalid payloads."""
    # Not a dict
    assert marketing_agent._coerce_decision("invalid") is None

    # Empty dict uses defaults (resilient behavior)
    decision = marketing_agent._coerce_decision({})
    assert decision is not None
    assert decision.product == "pilaster"  # Default
    assert decision.platform == Platform.LINKEDIN  # Default

    # Invalid types that can't be coerced - should still work with str() conversion
    payload = {
        "product": None,
        "platform": None,
        "content_type": None,
        "topic": None,
        "reasoning": None,
    }
    decision = marketing_agent._coerce_decision(payload)
    # Should handle gracefully with str() conversion creating defaults


def test_decode_json_payload_valid(marketing_agent):
    """_decode_json_payload extracts JSON from various formats."""
    # Plain JSON array
    result = marketing_agent._decode_json_payload('[{"key": "value"}]')
    assert result == [{"key": "value"}]

    # Plain JSON object
    result = marketing_agent._decode_json_payload('{"key": "value"}')
    assert result == {"key": "value"}

    # JSON in markdown fence
    result = marketing_agent._decode_json_payload('```json\n[{"key": "value"}]\n```')
    assert result == [{"key": "value"}]

    # JSON embedded in text
    result = marketing_agent._decode_json_payload('Here is the data: [{"key": "value"}] above.')
    assert result == [{"key": "value"}]


def test_decode_json_payload_invalid(marketing_agent):
    """_decode_json_payload returns None for invalid JSON."""
    assert marketing_agent._decode_json_payload("") is None
    assert marketing_agent._decode_json_payload("not json") is None
    assert marketing_agent._decode_json_payload("[][]") is None


def test_fallback_content_text_twitter(marketing_agent):
    """_fallback_content_text generates Twitter-specific fallback with authority voice."""
    decision = ContentDecision(
        product="pilaster",
        platform=Platform.TWITTER,
        content_type=ContentType.TIPS,
        topic="AI image tips",
        reasoning="Test",
    )

    text = marketing_agent._fallback_content_text(decision)

    assert "pilaster" in text
    assert "I learned" in text or "AI image tips" in text  # authority voice
    assert len(text) <= 280  # Twitter limit


def test_fallback_content_text_linkedin(marketing_agent):
    """_fallback_content_text generates LinkedIn-specific fallback with authority voice."""
    decision = ContentDecision(
        product="genpeli",
        platform=Platform.LINKEDIN,
        content_type=ContentType.TUTORIAL,
        topic="Video editing workflow",
        hook="I automated my video editing pipeline.",
        reasoning="Test",
    )

    text = marketing_agent._fallback_content_text(decision)

    assert "genpeli" in text
    assert "I built" in text or "I automated" in text  # first person builder voice
    assert len(text) > 100  # LinkedIn allows longer content


def test_enforce_platform_limit(marketing_agent):
    """_enforce_platform_limit truncates text to platform limits."""
    long_text = "A" * 500

    # Twitter limit (280)
    result = marketing_agent._enforce_platform_limit(long_text, Platform.TWITTER)
    assert len(result) <= 280
    assert result.endswith("...")

    # LinkedIn limit (3000)
    result = marketing_agent._enforce_platform_limit(long_text, Platform.LINKEDIN)
    assert len(result) == 500  # Not truncated

    # No limit for TikTok
    result = marketing_agent._enforce_platform_limit(long_text, Platform.TIKTOK)
    assert len(result) == 500  # Not truncated


def test_product_info_extraction():
    """format_product_info extracts relevant product details with authority framing."""
    from holus.agents.marketing.prompts import format_product_info

    products = {
        "pilaster": {
            "name": "Pilaster.ai",
            "tagline": "AI images made easy",
            "description": "Generate stunning AI images",
            "audience": "Content creators",
            "pain_point": "Complex AI tools",
        }
    }

    info = format_product_info("pilaster", products)

    assert "Pilaster" in info
    assert "proof point" in info  # authority framing
    assert "AI images made easy" in info
    assert "Content creators" in info
    assert "Complex AI tools" in info


def test_product_info_missing_product():
    """format_product_info handles missing product gracefully."""
    from holus.agents.marketing.prompts import format_product_info

    info = format_product_info("nonexistent", {})

    # Should show N/A for missing fields (capitalized product name)
    assert "Nonexistent" in info
    assert "N/A" in info


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_marketing_cycle(marketing_agent, temp_config_files):
    """Test complete observe -> reason -> act -> evaluate cycle."""
    # Mock Claude responses
    decisions_json = json.dumps(
        [
            {
                "product": "pilaster",
                "platform": "linkedin",
                "content_type": "tutorial",
                "topic": "AI image generation 101",
                "reasoning": "Educational content for LinkedIn",
                "priority": 1,
                "estimated_engagement": "high",
            }
        ]
    )

    content_text = "Here's everything you need to know about AI image generation..."

    call_count = [0]

    def mock_call(**kwargs):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"

        # First call: reason stage (decisions)
        # Second call: act stage (content)
        if call_count[0] == 0:
            text_block.text = decisions_json
        else:
            text_block.text = content_text

        call_count[0] += 1
        response.content = [text_block]
        return response

    marketing_agent.claude.call = mock_call

    # Run full cycle
    state = marketing_agent.default_state()

    # Observe (skip niche research — it uses claude.call and would interfere with mock_call counter)
    marketing_agent._niche_research = AsyncMock(return_value={})  # type: ignore[method-assign]
    state.update(await marketing_agent.observe(state))
    assert "products" in state["product_updates"]

    # Reason
    state.update(await marketing_agent.reason(state))
    assert len(state["content_decisions"]) == 1

    # Act
    state.update(await marketing_agent.act(state))
    assert len(state["generated_content"]) == 1
    assert state["generated_content"][0]["text"] == content_text

    # Evaluate
    state.update(await marketing_agent.evaluate(state))
    assert state["evaluation"]["logged"] is True
    assert state["evaluation"]["pieces_created"] == 1

    # Verify queue file created (YAML format)
    queue_files = list(temp_config_files["queue_dir"].glob("*.yaml"))
    assert len(queue_files) == 1

    # Verify trajectory logged
    trajectory_path = temp_config_files["trajectory_path"]
    content = trajectory_path.read_text()
    assert len(content.strip()) > 0


# ---------------------------------------------------------------------------
# Test Brand Identity Loading
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observe_loads_brand_identity(marketing_agent, temp_config_files):
    """Observe stage loads and validates brand identity from brand.yaml."""
    state = marketing_agent.default_state()

    result = await marketing_agent.observe(state)

    assert "brand_identity" in result
    brand = result["brand_identity"]

    # Positioning validated through Pydantic model
    assert (
        brand["positioning"]["one_liner"] == "I build AI systems that actually work in production."
    )
    assert brand["positioning"]["category"] == "AI implementation consultant"
    assert "Builder, not advisor" in brand["positioning"]["differentiation"]

    # Voice validated
    assert brand["voice"]["archetype"] == "Builder-philosopher"
    assert "First person always" in brand["voice"]["tone"]
    assert brand["voice"]["hooks"]["contrarian"] == "Most people are playing with AI."

    # Content pillars validated
    assert len(brand["content_pillars"]) == 1
    assert brand["content_pillars"][0]["id"] == "builder_stories"

    # Anti-patterns loaded
    assert "leverage synergies" in brand["anti_patterns"]["language"]

    # Platform strategy loaded
    assert brand["platform_strategy"]["primary"] == "linkedin"


@pytest.mark.asyncio
async def test_observe_handles_missing_brand_yaml(marketing_agent, monkeypatch):
    """Observe stage returns empty brand_identity when brand.yaml is missing."""
    monkeypatch.setattr(MarketingAgent, "_BRAND_PATH", Path("/nonexistent/brand.yaml"))

    state = marketing_agent.default_state()
    result = await marketing_agent.observe(state)

    assert result["brand_identity"] == {}


@pytest.mark.asyncio
async def test_observe_handles_invalid_brand_yaml(marketing_agent, temp_config_files):
    """Observe stage falls back to raw dict when brand.yaml has invalid structure."""
    # Write invalid YAML that is valid YAML but fails Pydantic validation
    brand_path = temp_config_files["brand_path"]
    brand_path.write_text(
        yaml.dump(
            {
                "content_pillars": [
                    {"missing_required": "id field"}  # ContentPillar requires id, name, description
                ]
            }
        )
    )

    state = marketing_agent.default_state()
    result = await marketing_agent.observe(state)

    # Should fall back to the raw dict (not crash)
    assert isinstance(result["brand_identity"], dict)
    assert "content_pillars" in result["brand_identity"]


@pytest.mark.asyncio
async def test_observe_handles_empty_brand_yaml(marketing_agent, temp_config_files):
    """Observe stage returns empty dict for empty brand.yaml."""
    brand_path = temp_config_files["brand_path"]
    brand_path.write_text("")

    state = marketing_agent.default_state()
    result = await marketing_agent.observe(state)

    assert result["brand_identity"] == {}


def test_load_brand_identity_validates_structure(marketing_agent, temp_config_files):
    """_load_brand_identity validates brand.yaml through Pydantic model."""
    brand = marketing_agent._load_brand_identity()

    assert isinstance(brand, dict)
    # All top-level BrandIdentity fields present
    assert "positioning" in brand
    assert "voice" in brand
    assert "content_pillars" in brand
    assert "anti_patterns" in brand
    assert "platform_strategy" in brand
    assert "story" in brand


def test_default_state_includes_brand_identity(marketing_agent):
    """default_state includes brand_identity key."""
    state = marketing_agent.default_state()

    assert "brand_identity" in state
    assert state["brand_identity"] == {}


# ---------------------------------------------------------------------------
# Test Authority Engine Fields
# ---------------------------------------------------------------------------


def test_coerce_decision_with_authority_fields(marketing_agent):
    """_coerce_decision handles new authority-engine fields."""
    payload = {
        "product": "pilaster",
        "platform": "linkedin",
        "content_type": "tutorial",
        "content_pillar": "builder_stories",
        "topic": "What I learned building Pilaster",
        "hook": "I built an AI image platform from scratch.",
        "framework": "builder_journey",
        "reasoning": "Builder stories resonate with consulting prospects",
        "priority": 1,
        "estimated_engagement": "high",
        "repurpose_notes": "Good for Twitter thread too",
    }

    decision = marketing_agent._coerce_decision(payload)

    assert decision is not None
    assert decision.content_pillar == "builder_stories"
    assert decision.hook == "I built an AI image platform from scratch."
    assert decision.framework == "builder_journey"
    assert decision.repurpose_notes == "Good for Twitter thread too"


def test_coerce_decision_authority_defaults(marketing_agent):
    """_coerce_decision uses defaults for missing authority fields (backward compat)."""
    payload = {
        "product": "pilaster",
        "platform": "linkedin",
        "content_type": "tutorial",
        "topic": "Old-style decision without new fields",
        "reasoning": "Test",
    }

    decision = marketing_agent._coerce_decision(payload)

    assert decision is not None
    assert decision.content_pillar == "builder_stories"  # default
    assert decision.hook == ""  # default
    assert decision.framework == "original"  # default
    assert decision.repurpose_notes == ""  # default


def test_fallback_decisions_use_authority_framing(marketing_agent):
    """Fallback decisions use builder stories pillar and authority voice."""
    products_data = {
        "products": {
            "pilaster": {"name": "Pilaster", "platforms": ["linkedin"]},
        }
    }

    decisions = marketing_agent._fallback_decisions(products_data)

    assert len(decisions) >= 1
    decision = decisions[0]
    assert decision.content_pillar == "builder_stories"
    assert decision.platform == Platform.LINKEDIN
    assert "learned" in decision.topic.lower() or "building" in decision.topic.lower()
    assert decision.hook != ""  # hook is populated


def test_fallback_decisions_cold_start_authority(marketing_agent):
    """Cold-start fallback uses authority framing."""
    decisions = marketing_agent._fallback_decisions({})

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.content_pillar == "builder_stories"
    assert decision.hook != ""
    assert "built" in decision.hook.lower() or "build" in decision.hook.lower()


# ---------------------------------------------------------------------------
# Test Prompt Formatting Helpers
# ---------------------------------------------------------------------------


def test_format_brand_identity():
    """format_brand_identity renders brand into readable text."""
    from holus.agents.marketing.prompts import format_brand_identity

    brand = {
        "story": {
            "origin": "Colombian AI engineer in NYC",
            "journey": ["Built Pilaster", "Built genpeli"],
        },
        "positioning": {
            "one_liner": "I build AI systems that work.",
            "category": "AI consultant",
            "differentiation": ["Builder, not advisor"],
        },
        "products_as_proof": {
            "framing": "Products are evidence of expertise.",
            "pilaster": {"proof_narrative": "I built an AI image platform."},
        },
    }

    text = format_brand_identity(brand)

    assert "Colombian AI engineer" in text
    assert "I build AI systems" in text
    assert "Builder, not advisor" in text
    assert "Products are evidence" in text
    assert "I built an AI image platform" in text


def test_format_brand_identity_empty():
    """format_brand_identity handles empty brand gracefully."""
    from holus.agents.marketing.prompts import format_brand_identity

    text = format_brand_identity({})
    assert "No brand identity" in text


def test_format_voice():
    """format_voice renders voice profile."""
    from holus.agents.marketing.prompts import format_voice

    brand = {
        "voice": {
            "archetype": "Builder-philosopher",
            "summary": "Direct and honest",
            "tone": ["First person always", "Short paragraphs"],
            "hooks": {"contrarian": "Most people are playing with AI."},
            "closers": {"question": "What would you build?"},
        }
    }

    text = format_voice(brand)

    assert "Builder-philosopher" in text
    assert "First person always" in text
    assert "Most people are playing" in text
    assert "What would you build" in text


def test_format_anti_patterns():
    """format_anti_patterns renders anti-pattern rules."""
    from holus.agents.marketing.prompts import format_anti_patterns

    brand = {
        "anti_patterns": {
            "language": ["leverage synergies", "game-changing"],
            "style": ["Walls of text"],
        }
    }

    text = format_anti_patterns(brand)

    assert "leverage synergies" in text
    assert "game-changing" in text
    assert "Walls of text" in text


def test_format_content_pillars():
    """format_content_pillars renders pillar list."""
    from holus.agents.marketing.prompts import format_content_pillars

    brand = {
        "content_pillars": [
            {
                "id": "builder_stories",
                "name": "Builder Stories",
                "description": "I built X, here's what I learned",
                "frequency": "2x/week",
                "goal": "Demonstrate expertise",
            },
            {
                "id": "ai_frameworks",
                "name": "AI Frameworks",
                "description": "How to deploy AI",
                "frequency": "1x/week",
            },
        ]
    }

    text = format_content_pillars(brand)

    assert "Builder Stories" in text
    assert "builder_stories" in text
    assert "2x/week" in text
    assert "AI Frameworks" in text


def test_format_niche_research(marketing_agent):
    """_format_niche_research renders research results."""
    niche = {
        "trending_topics": ["AI agents", "Claude MCP integration"],
        "recommended_angles": ["Builder perspective on AI agents"],
        "insights": [{"topic": "AI agent hype"}],
    }

    text = marketing_agent._format_niche_research(niche)

    assert "AI agents" in text
    assert "Builder perspective" in text
    assert "1 insights extracted" in text


def test_format_niche_research_empty(marketing_agent):
    """_format_niche_research handles empty research."""
    text = marketing_agent._format_niche_research({})
    assert "No niche research" in text
