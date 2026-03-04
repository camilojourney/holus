"""Tests for the NicheResearcher extracted module.

Covers:
  - parse_research_queries() — YAML parsing from markdown
  - select_queries() — rotation, cooldown, staleness sorting
  - web_search_single() — Claude API call with web_search tool
  - extract_insights() — JSON parsing into NicheInsight models
  - research() — full flow, timeout, graceful degradation
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from holus.agents.marketing.models import NicheInsight, NicheResearchResult
from holus.agents.marketing.niche_research import NicheResearcher

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


def _make_researcher(
    tmp_path: Path,
    *,
    api_key: str = "sk-test-key",
    queries_md: str = SAMPLE_QUERIES_MD,
) -> NicheResearcher:
    """Create a NicheResearcher with mocked claude client and temp paths."""
    mock_claude = MagicMock()

    queries_path = tmp_path / "niche-research-queries.md"
    if queries_md:
        queries_path.write_text(queries_md, encoding="utf-8")
    else:
        queries_path = tmp_path / "nonexistent.md"

    state_path = tmp_path / "niche-state.json"

    return NicheResearcher(
        claude_client=mock_claude,
        api_key=api_key,
        agent_name="test-agent",
        queries_path=queries_path,
        state_path=state_path,
    )


# ---------------------------------------------------------------------------
# Tests: parse_research_queries()
# ---------------------------------------------------------------------------


class TestParseResearchQueries:
    """Tests for YAML parsing from the niche-research-queries.md file."""

    def test_parses_yaml_block(self, tmp_path: Path) -> None:
        """Extracts and parses the YAML block from markdown."""
        researcher = _make_researcher(tmp_path)
        result = researcher.parse_research_queries()

        assert "queries" in result
        assert "competitor_content" in result["queries"]
        assert "trending_topics" in result["queries"]

    def test_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        """Returns empty dict when the queries file doesn't exist."""
        researcher = _make_researcher(tmp_path, queries_md="")
        result = researcher.parse_research_queries()
        assert result == {}

    def test_returns_empty_when_no_yaml_block(self, tmp_path: Path) -> None:
        """Returns empty dict when the file has no YAML block."""
        researcher = _make_researcher(tmp_path, queries_md="# No YAML here\nJust text.")
        result = researcher.parse_research_queries()
        assert result == {}

    def test_returns_empty_on_invalid_yaml(self, tmp_path: Path) -> None:
        """Returns empty dict when the YAML block is malformed."""
        bad_yaml = "# Queries\n\n```yaml\n[invalid: yaml: {{\n```\n"
        researcher = _make_researcher(tmp_path, queries_md=bad_yaml)
        result = researcher.parse_research_queries()
        assert result == {}

    def test_returns_empty_when_yaml_parses_to_list(self, tmp_path: Path) -> None:
        """YAML block that parses to a list instead of dict returns {}."""
        list_yaml = "# Queries\n\n```yaml\n- item1\n- item2\n```\n"
        researcher = _make_researcher(tmp_path, queries_md=list_yaml)
        result = researcher.parse_research_queries()
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: select_queries()
# ---------------------------------------------------------------------------


class TestSelectQueries:
    """Tests for query selection and rotation."""

    def test_selects_up_to_max_queries(self, tmp_path: Path) -> None:
        """Selects at most max_queries queries."""
        researcher = _make_researcher(tmp_path)
        config = researcher.parse_research_queries()
        queries = researcher.select_queries(config, max_queries=3)
        assert len(queries) <= 3
        assert len(queries) > 0

    def test_respects_cooldown(self, tmp_path: Path) -> None:
        """Queries recently run are skipped."""
        researcher = _make_researcher(tmp_path)
        config = researcher.parse_research_queries()

        # Run once to populate state
        first_run = researcher.select_queries(config, max_queries=5)
        assert len(first_run) > 0

        # Run again immediately — all queries should be on cooldown
        second_run = researcher.select_queries(config, max_queries=5)
        # Should not return the same queries (they're on cooldown)
        overlap = set(first_run) & set(second_run)
        assert len(overlap) == 0

    def test_stale_categories_first(self, tmp_path: Path) -> None:
        """Categories sorted by staleness — least recently used first."""
        researcher = _make_researcher(tmp_path)

        # Pre-populate state: competitor_content used recently, others never
        now = datetime.now(UTC)
        state = {
            "category_last_used": {
                "competitor_content": now.isoformat(),
            },
            "query_history": {},
        }
        researcher.write_niche_state(state)

        config = researcher.parse_research_queries()
        queries = researcher.select_queries(config, max_queries=2)

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
        researcher = _make_researcher(tmp_path)
        result = researcher.select_queries({"other": "data"}, max_queries=5)
        assert result == []

    def test_state_persisted(self, tmp_path: Path) -> None:
        """State file is written after query selection."""
        researcher = _make_researcher(tmp_path)
        config = researcher.parse_research_queries()
        researcher.select_queries(config, max_queries=3)

        assert researcher.state_path.exists()
        state = json.loads(researcher.state_path.read_text(encoding="utf-8"))
        assert "query_history" in state
        assert "last_run" in state

    def test_handles_expired_cooldown(self, tmp_path: Path) -> None:
        """Queries with expired cooldown are eligible again."""
        researcher = _make_researcher(tmp_path)

        # Set query history to 25 hours ago (past daily cooldown)
        old_time = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        state = {
            "query_history": {
                "AI deployment challenges enterprise": old_time,
            },
            "category_last_used": {},
        }
        researcher.write_niche_state(state)

        config = researcher.parse_research_queries()
        queries = researcher.select_queries(config, max_queries=5)
        assert "AI deployment challenges enterprise" in queries

    def test_queries_as_plain_strings(self, tmp_path: Path) -> None:
        """Query items that are plain strings (not dicts) are handled."""
        researcher = _make_researcher(tmp_path)
        config = {
            "queries": {
                "plain_category": {
                    "rotation": "daily",
                    "queries": ["plain query one", "plain query two"],
                }
            }
        }
        queries = researcher.select_queries(config, max_queries=5)
        assert "plain query one" in queries
        assert "plain query two" in queries

    def test_weekly_cooldown_respected(self, tmp_path: Path) -> None:
        """Weekly rotation uses 168h cooldown, not 24h."""
        researcher = _make_researcher(tmp_path)

        # 25h has elapsed — past daily cooldown but still within weekly (168h)
        old_time = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        state = {
            "query_history": {
                "site:linkedin.com AI consulting 2026": old_time,
            },
            "category_last_used": {},
        }
        researcher.write_niche_state(state)

        config = {
            "queries": {
                "competitor_content": {
                    "rotation": "weekly",
                    "queries": [
                        {"query": "site:linkedin.com AI consulting 2026", "intent": "test"}
                    ],
                }
            }
        }
        queries = researcher.select_queries(config, max_queries=5)
        assert "site:linkedin.com AI consulting 2026" not in queries

    def test_empty_categories_skipped(self, tmp_path: Path) -> None:
        """Category with empty or non-list queries field is skipped."""
        researcher = _make_researcher(tmp_path)
        config = {
            "queries": {
                "empty_category": {
                    "rotation": "daily",
                    "queries": [],
                },
                "non_list_category": {
                    "rotation": "daily",
                    "queries": "not a list",
                },
                "valid_category": {
                    "rotation": "daily",
                    "queries": [{"query": "valid query", "intent": "test"}],
                },
            }
        }
        queries = researcher.select_queries(config, max_queries=5)
        assert "valid query" in queries
        assert len(queries) == 1


# ---------------------------------------------------------------------------
# Tests: web_search_single()
# ---------------------------------------------------------------------------


class TestWebSearchSingle:
    """Tests for individual web search execution."""

    def test_calls_claude_with_web_search_tool(self, tmp_path: Path) -> None:
        """Claude is called with the web_search_20250305 tool."""
        researcher = _make_researcher(tmp_path)
        researcher.claude = MagicMock()
        researcher.claude.call.return_value = _make_claude_response("Search results summary here.")

        result = researcher.web_search_single("AI consulting 2026")

        researcher.claude.call.assert_called_once()
        call_kwargs = researcher.claude.call.call_args
        cached_prompt = call_kwargs.kwargs.get("cached_prompt") or call_kwargs[1].get(
            "cached_prompt"
        )
        if cached_prompt is None:
            cached_prompt = call_kwargs[0][0]

        assert any(t.get("type") == "web_search_20250305" for t in cached_prompt.tools)
        assert result == "Search results summary here."

    def test_returns_empty_on_empty_response(self, tmp_path: Path) -> None:
        """Returns empty string when Claude returns no text."""
        researcher = _make_researcher(tmp_path)
        researcher.claude = MagicMock()

        response = MagicMock()
        response.content = []
        researcher.claude.call.return_value = response

        result = researcher.web_search_single("test query")
        assert result == ""

    def test_raises_on_claude_error(self, tmp_path: Path) -> None:
        """When claude.call raises, the exception propagates."""
        researcher = _make_researcher(tmp_path)
        researcher.claude.call = MagicMock(side_effect=RuntimeError("API error"))

        with pytest.raises(RuntimeError, match="API error"):
            researcher.web_search_single("test query")


# ---------------------------------------------------------------------------
# Tests: read_niche_state() / write_niche_state()
# ---------------------------------------------------------------------------


class TestReadWriteNicheState:
    """Tests for read_niche_state() and write_niche_state()."""

    def test_read_returns_empty_on_missing_file(self, tmp_path: Path) -> None:
        """Non-existent state file returns {}."""
        researcher = _make_researcher(tmp_path)
        # state_path points to a file that does not exist yet
        result = researcher.read_niche_state()
        assert result == {}

    def test_read_returns_empty_on_malformed_json(self, tmp_path: Path) -> None:
        """Malformed JSON in state file returns {}."""
        researcher = _make_researcher(tmp_path)
        researcher.state_path.parent.mkdir(parents=True, exist_ok=True)
        researcher.state_path.write_text("{ invalid json }", encoding="utf-8")
        result = researcher.read_niche_state()
        assert result == {}

    def test_read_returns_empty_on_non_dict_json(self, tmp_path: Path) -> None:
        """JSON that parses to a list returns {}."""
        researcher = _make_researcher(tmp_path)
        researcher.state_path.parent.mkdir(parents=True, exist_ok=True)
        researcher.state_path.write_text('["item1", "item2"]', encoding="utf-8")
        result = researcher.read_niche_state()
        assert result == {}

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Writing state creates parent directories."""
        researcher = _make_researcher(tmp_path)
        researcher.state_path = tmp_path / "deep" / "nested" / "state.json"
        researcher.write_niche_state({"key": "value"})
        assert researcher.state_path.exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Write then read returns same data."""
        researcher = _make_researcher(tmp_path)
        state = {
            "query_history": {"q1": "2026-03-01T00:00:00+00:00"},
            "last_run": "2026-03-01T00:00:00+00:00",
        }
        researcher.write_niche_state(state)
        result = researcher.read_niche_state()
        assert result == state


# ---------------------------------------------------------------------------
# Tests: extract_insights()
# ---------------------------------------------------------------------------


class TestExtractInsights:
    """Tests for insight extraction from search results."""

    def test_extracts_valid_insights(self, tmp_path: Path) -> None:
        """Parses JSON response into NicheInsight objects."""
        researcher = _make_researcher(tmp_path)
        researcher.claude = MagicMock()
        researcher.claude.call.return_value = _make_claude_response(SAMPLE_INSIGHTS_JSON)

        insights = researcher.extract_insights("Some search results here.")
        assert len(insights) == 2
        assert all(isinstance(i, NicheInsight) for i in insights)
        assert insights[0].topic == "AI pipeline architecture"
        assert insights[1].category == "industry_news"

    def test_returns_empty_on_invalid_json(self, tmp_path: Path) -> None:
        """Returns empty list when Claude returns invalid JSON."""
        researcher = _make_researcher(tmp_path)
        researcher.claude = MagicMock()
        researcher.claude.call.return_value = _make_claude_response("Not valid JSON at all.")

        insights = researcher.extract_insights("Some results.")
        assert insights == []

    def test_skips_invalid_insight_items(self, tmp_path: Path) -> None:
        """Skips items that don't validate as NicheInsight."""
        researcher = _make_researcher(tmp_path)
        researcher.claude = MagicMock()

        mixed = json.dumps(
            [
                {"topic": "Valid insight", "category": "trending_topic"},
                "not a dict",
                42,
                {"topic": "Another valid", "category": "industry_news"},
            ]
        )
        researcher.claude.call.return_value = _make_claude_response(mixed)

        insights = researcher.extract_insights("Results.")
        assert len(insights) == 2

    def test_handles_empty_response(self, tmp_path: Path) -> None:
        """Returns empty list when Claude returns empty string."""
        researcher = _make_researcher(tmp_path)
        researcher.claude = MagicMock()
        researcher.claude.call.return_value = _make_claude_response("")

        insights = researcher.extract_insights("Results.")
        assert insights == []

    def test_json_in_code_fences(self, tmp_path: Path) -> None:
        """JSON wrapped in ```json ... ``` is extracted correctly."""
        researcher = _make_researcher(tmp_path)
        researcher.claude = MagicMock()
        fenced_json = f"```json\n{SAMPLE_INSIGHTS_JSON}\n```"
        researcher.claude.call.return_value = _make_claude_response(fenced_json)

        insights = researcher.extract_insights("Some results.")
        assert len(insights) == 2
        assert all(isinstance(i, NicheInsight) for i in insights)


# ---------------------------------------------------------------------------
# Tests: research() (full flow)
# ---------------------------------------------------------------------------


class TestNicheResearch:
    """Tests for the full niche research orchestration."""

    @pytest.mark.asyncio()
    async def test_returns_empty_without_api_key(self, tmp_path: Path) -> None:
        """Skips niche research when no API key is configured."""
        researcher = _make_researcher(tmp_path, api_key="")
        result = await researcher.research()
        assert result == {}

    @pytest.mark.asyncio()
    async def test_returns_empty_without_queries_file(self, tmp_path: Path) -> None:
        """Returns empty when queries file is missing."""
        researcher = _make_researcher(tmp_path, queries_md="")
        result = await researcher.research()
        assert result == {}

    @pytest.mark.asyncio()
    async def test_full_flow_returns_result(self, tmp_path: Path) -> None:
        """Full flow: parse queries, search, extract, return result."""
        researcher = _make_researcher(tmp_path)

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

        researcher.claude.call = MagicMock(side_effect=_side_effect)

        result = await researcher.research()

        assert "queries_run" in result
        assert len(result["queries_run"]) > 0
        assert "insights" in result
        assert "trending_topics" in result
        assert "recommended_angles" in result

    @pytest.mark.asyncio()
    async def test_graceful_on_search_failure(self, tmp_path: Path) -> None:
        """Returns result with queries_run but empty insights on failure."""
        researcher = _make_researcher(tmp_path)
        researcher.claude.call = MagicMock(side_effect=RuntimeError("API unavailable"))

        result = await researcher.research()

        # Should still return a valid result dict with queries_run
        assert "queries_run" in result
        assert result.get("insights", []) == []

    @pytest.mark.asyncio()
    async def test_returns_empty_when_all_queries_on_cooldown(self, tmp_path: Path) -> None:
        """Returns empty when all queries were recently run."""
        researcher = _make_researcher(tmp_path)

        # Run once to exhaust all queries
        config = researcher.parse_research_queries()
        researcher.select_queries(config, max_queries=100)

        # Now niche research should find no eligible queries
        result = await researcher.research()
        assert result == {}

    @pytest.mark.asyncio()
    async def test_research_none_api_key(self, tmp_path: Path) -> None:
        """api_key=None (not just empty string) also returns {}."""
        mock_claude = MagicMock()
        queries_path = tmp_path / "niche-research-queries.md"
        queries_path.write_text(SAMPLE_QUERIES_MD, encoding="utf-8")
        state_path = tmp_path / "niche-state.json"
        researcher = NicheResearcher(
            claude_client=mock_claude,
            api_key=None,
            agent_name="test-agent",
            queries_path=queries_path,
            state_path=state_path,
        )
        result = await researcher.research()
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


# ---------------------------------------------------------------------------
# Tests: format_niche_research() static method
# ---------------------------------------------------------------------------


class TestFormatNicheResearch:
    """Tests for NicheResearcher.format_niche_research()."""

    def test_empty_input(self) -> None:
        assert (
            NicheResearcher.format_niche_research({}) == "No niche research available this cycle."
        )

    def test_trending_topics(self) -> None:
        result = NicheResearcher.format_niche_research(
            {"trending_topics": ["AI agents", "RAG pipelines"]}
        )
        assert "AI agents" in result
        assert "RAG pipelines" in result

    def test_recommended_angles(self) -> None:
        result = NicheResearcher.format_niche_research(
            {"recommended_angles": ["Builder story angle"]}
        )
        assert "Builder story angle" in result

    def test_insights_count(self) -> None:
        result = NicheResearcher.format_niche_research(
            {"insights": [{"topic": "a"}, {"topic": "b"}]}
        )
        assert "2 insights" in result

    def test_truncates_at_five_topics(self) -> None:
        """More than 5 topics are truncated to 5."""
        result = NicheResearcher.format_niche_research(
            {"trending_topics": ["t1", "t2", "t3", "t4", "t5", "t6", "t7"]}
        )
        assert "t5" in result
        assert "t6" not in result
        assert "t7" not in result

    def test_combined_sections(self) -> None:
        """Result with topics + angles + insights shows all sections."""
        result = NicheResearcher.format_niche_research(
            {
                "trending_topics": ["AI agents"],
                "recommended_angles": ["Builder story"],
                "insights": [{"topic": "test"}],
            }
        )
        assert "AI agents" in result
        assert "Builder story" in result
        assert "1 insights" in result
