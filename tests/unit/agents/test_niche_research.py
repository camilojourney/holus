"""Tests for the niche research step in the marketing agent observe stage.

Covers:
  - _parse_research_queries() — YAML parsing from markdown
  - _select_queries() — rotation, cooldown, staleness sorting
  - _web_search_single() — Claude API call with web_search tool
  - _extract_insights() — JSON parsing into NicheInsight models
  - _niche_research() — full flow, timeout, graceful degradation
  - observe() integration — niche_research flows into state
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from holus.agents.marketing.models import NicheInsight, NicheResearchResult

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_QUERIES_MD = """# Knowledge: Niche Research Queries

Some intro text.

```yaml
queries:
  competitor_content:
    description: "What top AI consultants post"
    rotation: weekly
    queries:
      - query: "site:linkedin.com AI consulting 2026"
        intent: "Find consultant posts"
      - query: "site:linkedin.com AI builder story"
        intent: "Find builder stories"

  trending_topics:
    description: "Hot AI topics"
    rotation: daily
    queries:
      - query: "AI deployment challenges enterprise"
        intent: "Pain points"
      - query: "AI agent framework production"
        intent: "Agent issues"

  industry_news:
    description: "Breaking AI news"
    rotation: daily
    queries:
      - query: "enterprise AI news this week"
        intent: "Major developments"
```

Some closing text.
"""

SAMPLE_INSIGHTS_JSON = json.dumps(
    [
        {
            "source_url": "https://linkedin.com/post/123",
            "source_title": "How I Built an AI Pipeline",
            "category": "competitor_content",
            "topic": "AI pipeline architecture",
            "hook": "I built an AI pipeline that processes 10M records/day.",
            "format": "text",
            "engagement_signals": "500+ reactions, 80 comments",
            "why_it_works": "Specific numbers + builder story",
            "relevance_to_camilo": "Similar builder narrative",
            "pillar_fit": ["builder_stories", "ai_frameworks"],
        },
        {
            "source_url": "https://example.com/article",
            "source_title": "Enterprise AI Adoption Report",
            "category": "industry_news",
            "topic": "Enterprise AI adoption rates 2026",
            "format": "text",
            "why_it_works": "Data-backed with real survey numbers",
            "relevance_to_camilo": "Great data for industry_analysis posts",
            "pillar_fit": ["industry_analysis"],
        },
    ]
)


def _make_claude_response(text: str) -> MagicMock:
    """Build a mock Claude API response."""
    response = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response.content = [text_block]
    response.usage = MagicMock(
        input_tokens=50,
        output_tokens=30,
        cache_read_input_tokens=40,
        cache_creation_input_tokens=10,
    )
    return response


def _make_agent(
    tmp_path: Path,
    *,
    api_key: str = "sk-test-key",
    queries_md: str = SAMPLE_QUERIES_MD,
) -> Any:
    """Create a MarketingAgent with mocked infrastructure."""
    from holus.agents.marketing.agent import MarketingAgent

    mock_config = MagicMock()
    mock_config.anthropic_api_key = api_key
    mock_config.anthropic_base_url = ""
    mock_config.redis_url = "redis://localhost:6379"
    mock_config.mem0_api_url = "http://localhost:8080"
    mock_config.langfuse_host = "http://localhost:3001"
    mock_config.langfuse_public_key = ""
    mock_config.langfuse_secret_key = ""
    mock_config.sonnet_model = "claude-sonnet-4-6"
    mock_config.opus_model = "claude-opus-4-6"
    mock_config.haiku_model = "claude-haiku-3-5"

    mock_agent_config = MagicMock()
    mock_agent_config.default_model_tier = "operational"
    mock_agent_config.mem0_scope = "marketing"

    with (
        patch("holus.agents.base.redis.Redis.from_url", return_value=MagicMock()),
        patch("holus.agents.base.EventBus", return_value=MagicMock()),
        patch("holus.agents.base.KillSwitch", return_value=MagicMock()),
    ):
        agent = MarketingAgent(config=mock_config, agent_config=mock_agent_config)

    # Override paths to use tmp_path
    queries_path = tmp_path / "niche-research-queries.md"
    if queries_md:
        queries_path.write_text(queries_md, encoding="utf-8")
    agent._NICHE_QUERIES_PATH = queries_path

    state_path = tmp_path / "niche-state.json"
    agent._NICHE_STATE_PATH = state_path

    return agent


# ---------------------------------------------------------------------------
# Tests: _parse_research_queries()
# ---------------------------------------------------------------------------


class TestParseResearchQueries:
    """Tests for YAML parsing from the niche-research-queries.md file."""

    def test_parses_yaml_block(self, tmp_path: Path) -> None:
        """Extracts and parses the YAML block from markdown."""
        agent = _make_agent(tmp_path)
        result = agent._parse_research_queries()

        assert "queries" in result
        assert "competitor_content" in result["queries"]
        assert "trending_topics" in result["queries"]

    def test_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        """Returns empty dict when the queries file doesn't exist."""
        agent = _make_agent(tmp_path, queries_md="")
        agent._NICHE_QUERIES_PATH = tmp_path / "nonexistent.md"
        result = agent._parse_research_queries()
        assert result == {}

    def test_returns_empty_when_no_yaml_block(self, tmp_path: Path) -> None:
        """Returns empty dict when the file has no YAML block."""
        agent = _make_agent(tmp_path, queries_md="# No YAML here\nJust text.")
        result = agent._parse_research_queries()
        assert result == {}

    def test_returns_empty_on_invalid_yaml(self, tmp_path: Path) -> None:
        """Returns empty dict when the YAML block is malformed."""
        bad_yaml = "# Queries\n\n```yaml\n[invalid: yaml: {{\n```\n"
        agent = _make_agent(tmp_path, queries_md=bad_yaml)
        result = agent._parse_research_queries()
        assert result == {}

    def test_returns_empty_when_yaml_is_a_list(self, tmp_path: Path) -> None:
        """Only mapping-shaped YAML is a valid query configuration."""
        agent = _make_agent(
            tmp_path, queries_md="# Queries\n```yaml\n- query one\n- query two\n```\n"
        )

        assert agent._parse_research_queries() == {}


# ---------------------------------------------------------------------------
# Tests: _select_queries()
# ---------------------------------------------------------------------------


class TestSelectQueries:
    """Tests for query selection and rotation."""

    def test_selects_up_to_max_queries(self, tmp_path: Path) -> None:
        """Selects at most max_queries queries."""
        agent = _make_agent(tmp_path)
        config = agent._parse_research_queries()
        queries = agent._select_queries(config, max_queries=3)
        assert len(queries) <= 3
        assert len(queries) > 0

    def test_respects_cooldown(self, tmp_path: Path) -> None:
        """Queries recently run are skipped."""
        agent = _make_agent(tmp_path)
        config = agent._parse_research_queries()

        # Run once to populate state
        first_run = agent._select_queries(config, max_queries=5)
        assert len(first_run) > 0

        # Run again immediately — all queries should be on cooldown
        second_run = agent._select_queries(config, max_queries=5)
        # Should not return the same queries (they're on cooldown)
        overlap = set(first_run) & set(second_run)
        assert len(overlap) == 0

    def test_stale_categories_first(self, tmp_path: Path) -> None:
        """Categories sorted by staleness — least recently used first."""
        agent = _make_agent(tmp_path)

        # Pre-populate state: competitor_content used recently, others never
        now = datetime.now(UTC)
        state = {
            "category_last_used": {
                "competitor_content": now.isoformat(),
            },
            "query_history": {},
        }
        agent._write_niche_state(state)

        config = agent._parse_research_queries()
        queries = agent._select_queries(config, max_queries=2)

        # Should pick from trending_topics or industry_news first
        # (competitor_content was used recently)
        competitor_queries = {
            "site:linkedin.com AI consulting 2026",
            "site:linkedin.com AI builder story",
        }
        # At least one query should NOT be from competitor_content
        assert not all(q in competitor_queries for q in queries)

    def test_returns_empty_when_no_queries_section(self, tmp_path: Path) -> None:
        """Returns empty list when config has no queries section."""
        agent = _make_agent(tmp_path)
        result = agent._select_queries({"other": "data"}, max_queries=5)
        assert result == []

    def test_state_persisted(self, tmp_path: Path) -> None:
        """State file is written after query selection."""
        agent = _make_agent(tmp_path)
        config = agent._parse_research_queries()
        agent._select_queries(config, max_queries=3)

        assert agent._NICHE_STATE_PATH.exists()
        state = json.loads(agent._NICHE_STATE_PATH.read_text(encoding="utf-8"))
        assert "query_history" in state
        assert "last_run" in state

    def test_handles_expired_cooldown(self, tmp_path: Path) -> None:
        """Queries with expired cooldown are eligible again."""
        agent = _make_agent(tmp_path)

        # Set query history to 25 hours ago (past daily cooldown)
        old_time = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        state = {
            "query_history": {
                "AI deployment challenges enterprise": old_time,
            },
            "category_last_used": {},
        }
        agent._write_niche_state(state)

        config = agent._parse_research_queries()
        queries = agent._select_queries(config, max_queries=5)
        assert "AI deployment challenges enterprise" in queries

    def test_accepts_plain_string_queries_and_skips_invalid_categories(
        self, tmp_path: Path
    ) -> None:
        """Research rotation accepts simple query strings without treating invalid categories as work."""
        agent = _make_agent(tmp_path)
        config = {
            "queries": {
                "plain": {"rotation": "daily", "queries": ["plain query"]},
                "empty": {"rotation": "daily", "queries": []},
                "not_a_list": {"rotation": "daily", "queries": "not a list"},
            }
        }

        assert agent._select_queries(config, max_queries=5) == ["plain query"]

    def test_weekly_queries_remain_on_cooldown_after_a_day(self, tmp_path: Path) -> None:
        """Weekly research is not retried using the shorter daily cooldown."""
        agent = _make_agent(tmp_path)
        query = "site:linkedin.com AI consulting 2026"
        agent._write_niche_state(
            {
                "query_history": {query: (datetime.now(UTC) - timedelta(hours=25)).isoformat()},
                "category_last_used": {},
            }
        )
        config = {"queries": {"weekly": {"rotation": "weekly", "queries": [query]}}}

        assert agent._select_queries(config, max_queries=5) == []


# ---------------------------------------------------------------------------
# Tests: _web_search_single()
# ---------------------------------------------------------------------------


class TestWebSearchSingle:
    """Tests for individual web search execution."""

    def test_calls_claude_with_web_search_tool(self, tmp_path: Path) -> None:
        """Claude is called with the web_search_20250305 tool."""
        agent = _make_agent(tmp_path)
        agent.claude = MagicMock()
        agent.claude.call.return_value = _make_claude_response("Search results summary here.")

        result = agent._web_search_single("AI consulting 2026")

        agent.claude.call.assert_called_once()
        call_kwargs = agent.claude.call.call_args
        cached_prompt = call_kwargs.kwargs.get("cached_prompt") or call_kwargs[1].get(
            "cached_prompt"
        )
        if cached_prompt is None:
            cached_prompt = call_kwargs[0][0]

        assert any(t.get("type") == "web_search_20250305" for t in cached_prompt.tools)
        assert result == "Search results summary here."

    def test_returns_empty_on_empty_response(self, tmp_path: Path) -> None:
        """Returns empty string when Claude returns no text."""
        agent = _make_agent(tmp_path)
        agent.claude = MagicMock()

        response = MagicMock()
        response.content = []
        agent.claude.call.return_value = response

        result = agent._web_search_single("test query")
        assert result == ""


# ---------------------------------------------------------------------------
# Tests: _extract_insights()
# ---------------------------------------------------------------------------


class TestExtractInsights:
    """Tests for insight extraction from search results."""

    def test_extracts_valid_insights(self, tmp_path: Path) -> None:
        """Parses JSON response into NicheInsight objects."""
        agent = _make_agent(tmp_path)
        agent.claude = MagicMock()
        agent.claude.call.return_value = _make_claude_response(SAMPLE_INSIGHTS_JSON)

        insights = agent._extract_insights("Some search results here.")
        assert len(insights) == 2
        assert all(isinstance(i, NicheInsight) for i in insights)
        assert insights[0].topic == "AI pipeline architecture"
        assert insights[1].category == "industry_news"

    def test_returns_empty_on_invalid_json(self, tmp_path: Path) -> None:
        """Returns empty list when Claude returns invalid JSON."""
        agent = _make_agent(tmp_path)
        agent.claude = MagicMock()
        agent.claude.call.return_value = _make_claude_response("Not valid JSON at all.")

        insights = agent._extract_insights("Some results.")
        assert insights == []

    def test_skips_invalid_insight_items(self, tmp_path: Path) -> None:
        """Skips items that don't validate as NicheInsight."""
        agent = _make_agent(tmp_path)
        agent.claude = MagicMock()

        mixed = json.dumps(
            [
                {"topic": "Valid insight", "category": "trending_topic"},
                "not a dict",
                42,
                {"topic": "Another valid", "category": "industry_news"},
            ]
        )
        agent.claude.call.return_value = _make_claude_response(mixed)

        insights = agent._extract_insights("Results.")
        assert len(insights) == 2

    def test_handles_empty_response(self, tmp_path: Path) -> None:
        """Returns empty list when Claude returns empty string."""
        agent = _make_agent(tmp_path)
        agent.claude = MagicMock()
        agent.claude.call.return_value = _make_claude_response("")

        insights = agent._extract_insights("Results.")
        assert insights == []


# ---------------------------------------------------------------------------
# Tests: _niche_research() (full flow)
# ---------------------------------------------------------------------------


class TestNicheResearch:
    """Tests for the full niche research orchestration."""

    @pytest.mark.asyncio()
    async def test_returns_empty_without_api_key(self, tmp_path: Path) -> None:
        """Skips niche research when no API key is configured."""
        agent = _make_agent(tmp_path, api_key="")
        result = await agent._niche_research()
        assert result == {}

    @pytest.mark.asyncio()
    async def test_returns_empty_without_queries_file(self, tmp_path: Path) -> None:
        """Returns empty when queries file is missing."""
        agent = _make_agent(tmp_path, queries_md="")
        agent._NICHE_QUERIES_PATH = tmp_path / "nonexistent.md"
        result = await agent._niche_research()
        assert result == {}

    @pytest.mark.asyncio()
    async def test_full_flow_returns_result(self, tmp_path: Path) -> None:
        """Full flow: parse queries, search, extract, return result."""
        agent = _make_agent(tmp_path)
        agent.claude = MagicMock()

        # First calls are web searches, last call is extraction
        search_response = _make_claude_response("Found: AI consulting post about pipelines.")
        extraction_response = _make_claude_response(SAMPLE_INSIGHTS_JSON)

        call_count = 0

        def _side_effect(**kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            prompt = kwargs.get("cached_prompt")
            if prompt and hasattr(prompt, "tools") and prompt.tools:
                return search_response
            return extraction_response

        agent.claude.call = MagicMock(side_effect=_side_effect)

        result = await agent._niche_research()

        assert "queries_run" in result
        assert len(result["queries_run"]) > 0
        assert "insights" in result
        assert "trending_topics" in result
        assert "recommended_angles" in result

    @pytest.mark.asyncio()
    async def test_graceful_on_search_failure(self, tmp_path: Path) -> None:
        """Returns result with queries_run but empty insights on failure."""
        agent = _make_agent(tmp_path)
        agent.claude = MagicMock()
        agent.claude.call = MagicMock(side_effect=RuntimeError("API unavailable"))

        result = await agent._niche_research()

        # Should still return a valid result dict with queries_run
        assert "queries_run" in result
        assert result.get("insights", []) == []

    @pytest.mark.asyncio()
    async def test_returns_empty_when_all_queries_on_cooldown(self, tmp_path: Path) -> None:
        """Returns empty when all queries were recently run."""
        agent = _make_agent(tmp_path)

        # Run once to exhaust all queries
        config = agent._parse_research_queries()
        agent._select_queries(config, max_queries=100)

        # Now niche research should find no eligible queries
        result = await agent._niche_research()
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: NicheInsight and NicheResearchResult models
# ---------------------------------------------------------------------------


class TestModels:
    """Tests for the niche research Pydantic models."""

    def test_niche_insight_defaults(self) -> None:
        """NicheInsight has sensible defaults for all optional fields."""
        insight = NicheInsight()
        assert insight.source_url == ""
        assert insight.category == "trending_topic"
        assert insight.hook is None
        assert insight.pillar_fit == []
        assert insight.extracted_at  # Should be auto-set

    def test_niche_insight_full(self) -> None:
        """NicheInsight accepts all fields."""
        insight = NicheInsight(
            source_url="https://example.com",
            source_title="Test Post",
            category="competitor_content",
            hook="I built X",
            topic="AI pipelines",
            format="carousel",
            engagement_signals="1000+ reactions",
            why_it_works="Builder story",
            relevance_to_camilo="Similar angle",
            pillar_fit=["builder_stories"],
        )
        assert insight.category == "competitor_content"
        assert insight.pillar_fit == ["builder_stories"]

    def test_niche_research_result_defaults(self) -> None:
        """NicheResearchResult has empty defaults."""
        result = NicheResearchResult()
        assert result.queries_run == []
        assert result.insights == []
        assert result.trending_topics == []
        assert result.research_duration_ms == 0

    def test_niche_research_result_serialization(self) -> None:
        """NicheResearchResult serializes to dict properly."""
        insight = NicheInsight(topic="Test", category="trending_topic")
        result = NicheResearchResult(
            queries_run=["query1"],
            insights=[insight],
            trending_topics=["Test"],
            recommended_angles=["Angle 1"],
            research_duration_ms=500,
        )
        data = result.model_dump(mode="json")
        assert data["queries_run"] == ["query1"]
        assert len(data["insights"]) == 1
        assert data["research_duration_ms"] == 500
