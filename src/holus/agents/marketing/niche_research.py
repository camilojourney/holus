"""Niche research: web search, query rotation, insight extraction.

Extracted from agent.py to reduce module size and improve testability.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from holus.agents.marketing.models import NicheInsight, NicheResearchResult
from holus.agents.marketing.prompts import NICHE_EXTRACTION_PROMPT
from holus.integrations.claude_api.client import CachedPrompt, HolusClaudeClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utility helpers (pure functions, no instance state)
# ---------------------------------------------------------------------------


def extract_response_text(response: Any) -> str:
    """Extract text content from a Claude API response."""
    blocks = getattr(response, "content", [])
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts).strip()


def decode_json_payload(text: str) -> Any | None:
    """Extract a JSON object or array from LLM response text.

    Tries in order: direct parse, fenced code blocks, bare ``[...]`` / ``{...}``.
    """
    stripped = text.strip()
    if not stripped:
        return None

    direct = _try_json_loads(stripped)
    if direct is not None:
        return direct

    fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL)
    for block in fenced_blocks:
        parsed = _try_json_loads(block.strip())
        if parsed is not None:
            return parsed

    left = stripped.find("[")
    right = stripped.rfind("]")
    if left != -1 and right != -1 and right > left:
        parsed = _try_json_loads(stripped[left : right + 1])
        if parsed is not None:
            return parsed

    left = stripped.find("{")
    right = stripped.rfind("}")
    if left != -1 and right != -1 and right > left:
        parsed = _try_json_loads(stripped[left : right + 1])
        if parsed is not None:
            return parsed

    return None


def _try_json_loads(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# NicheResearcher
# ---------------------------------------------------------------------------

QUERIES_PATH = Path(".self-improvement/knowledge/current/niche-research-queries.md")
STATE_PATH = Path("data/.niche-research-state.json")
MAX_QUERIES = 5
TIMEOUT_SECONDS = 30


class NicheResearcher:
    """Niche research: web search, query rotation, insight extraction."""

    def __init__(
        self,
        claude_client: HolusClaudeClient,
        api_key: str | None,
        agent_name: str,
        *,
        queries_path: Path = QUERIES_PATH,
        state_path: Path = STATE_PATH,
        max_queries: int = MAX_QUERIES,
        timeout_seconds: int = TIMEOUT_SECONDS,
    ) -> None:
        self.claude = claude_client
        self.api_key = api_key
        self.agent_name = agent_name
        self.queries_path = queries_path
        self.state_path = state_path
        self.max_queries = max_queries
        self.timeout_seconds = timeout_seconds

    async def research(self) -> dict[str, Any]:
        """Run niche research: select queries, search web, extract insights.

        Gracefully degrades: returns empty dict if anything fails.
        Respects ``timeout_seconds`` total timeout.
        """
        if not self.api_key:
            logger.info("Niche research skipped: no API key")
            return {}

        start_ms = int(time.monotonic() * 1000)
        deadline = time.monotonic() + self.timeout_seconds

        query_config = self.parse_research_queries()
        if not query_config:
            logger.warning("No niche research queries found")
            return {}

        queries = self.select_queries(query_config, max_queries=self.max_queries)
        if not queries:
            logger.info("No queries eligible this cycle (all recently run)")
            return {}

        # Execute searches
        all_results: list[str] = []
        for query in queries:
            if time.monotonic() >= deadline:
                logger.warning(
                    "Niche research timeout; stopping with %d results",
                    len(all_results),
                )
                break
            try:
                result = self.web_search_single(query)
                if result:
                    all_results.append(f"## Query: {query}\n\n{result}")
            except Exception:
                logger.warning("Web search failed for query: %s", query, exc_info=True)

        if not all_results:
            logger.info("No search results obtained")
            return NicheResearchResult(queries_run=queries).model_dump(mode="json")

        # Extract insights
        try:
            insights = self.extract_insights("\n\n---\n\n".join(all_results))
        except Exception:
            logger.warning("Insight extraction failed", exc_info=True)
            insights = []

        elapsed_ms = int(time.monotonic() * 1000) - start_ms

        trending = [i.topic for i in insights if i.topic][:5]
        angles = [i.relevance_to_camilo for i in insights if i.relevance_to_camilo][:5]

        research_result = NicheResearchResult(
            queries_run=queries,
            insights=insights,
            trending_topics=trending,
            recommended_angles=angles,
            research_duration_ms=elapsed_ms,
        )
        return research_result.model_dump(mode="json")

    def parse_research_queries(self) -> dict[str, Any]:
        """Parse the YAML block from niche-research-queries.md."""
        if not self.queries_path.exists():
            return {}

        try:
            content = self.queries_path.read_text(encoding="utf-8")
        except Exception:
            logger.warning("Failed to read niche research queries file", exc_info=True)
            return {}

        yaml_match = re.search(r"```yaml\s*\n(.*?)```", content, re.DOTALL)
        if not yaml_match:
            return {}

        try:
            parsed = yaml.safe_load(yaml_match.group(1))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            logger.warning("Failed to parse YAML from niche queries file", exc_info=True)
            return {}

    def select_queries(
        self, query_config: dict[str, Any], *, max_queries: int = 5
    ) -> list[str]:
        """Pick queries for this cycle, rotating across categories.

        Categories are sorted by staleness (least recently used first).
        Each query respects its rotation cooldown (daily=24h, weekly=168h).
        State is persisted to ``state_path``.
        """
        state = self.read_niche_state()
        query_history: dict[str, str] = state.get("query_history", {})
        category_last_used: dict[str, str] = state.get("category_last_used", {})
        now = datetime.now(UTC)

        queries_section = query_config.get("queries", {})
        if not isinstance(queries_section, dict):
            return []

        categories = list(queries_section.keys())
        categories.sort(key=lambda c: category_last_used.get(c, ""))

        selected: list[str] = []
        used_categories: set[str] = set()

        for category in categories:
            cat_data = queries_section.get(category, {})
            if not isinstance(cat_data, dict):
                continue

            rotation = cat_data.get("rotation", "daily")
            cooldown_hours = 24 if rotation == "daily" else 168

            cat_queries = cat_data.get("queries", [])
            if not isinstance(cat_queries, list):
                continue

            for q_item in cat_queries:
                query_text = (
                    q_item.get("query", "") if isinstance(q_item, dict) else str(q_item)
                )
                if not query_text:
                    continue

                last_run = query_history.get(query_text, "")
                if last_run:
                    try:
                        elapsed_hours = (
                            now - datetime.fromisoformat(last_run)
                        ).total_seconds() / 3600
                        if elapsed_hours < cooldown_hours:
                            continue
                    except (ValueError, TypeError):
                        pass

                selected.append(query_text)
                used_categories.add(category)
                if len(selected) >= max_queries:
                    break

            if len(selected) >= max_queries:
                break

        for q in selected:
            query_history[q] = now.isoformat()
        for cat in used_categories:
            category_last_used[cat] = now.isoformat()

        state["query_history"] = query_history
        state["category_last_used"] = category_last_used
        state["last_run"] = now.isoformat()
        self.write_niche_state(state)

        return selected

    def read_niche_state(self) -> dict[str, Any]:
        """Read niche research rotation state from disk."""
        if not self.state_path.exists():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def write_niche_state(self, state: dict[str, Any]) -> None:
        """Write niche research rotation state to disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.state_path.write_text(
                json.dumps(state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.warning("Failed to write niche research state", exc_info=True)

    def web_search_single(self, query: str) -> str:
        """Execute a single web search via Claude with the web_search tool."""
        response = self.claude.call(
            cached_prompt=CachedPrompt(
                system_prompt=(
                    "You are a research assistant. Search the web for the "
                    "given query and return a summary of the most relevant "
                    "results. Focus on: AI consulting, LinkedIn thought "
                    "leadership, enterprise AI implementation, and "
                    "builder/practitioner content. For each result, include "
                    "the URL, title, and a brief summary of why it is "
                    "relevant."
                ),
                tools=[{"type": "web_search_20250305"}],
            ),
            messages=[{"role": "user", "content": f"Search for: {query}"}],
            tier="operational",
            max_tokens=2048,
            agent_id=self.agent_name,
        )
        return extract_response_text(response)

    def extract_insights(self, aggregated_results: str) -> list[NicheInsight]:
        """Extract structured NicheInsight objects from search results."""
        prompt = NICHE_EXTRACTION_PROMPT.format(search_results=aggregated_results)
        response = self.claude.call(
            cached_prompt=CachedPrompt(system_prompt=prompt),
            messages=[
                {
                    "role": "user",
                    "content": "Extract insights now. Return a JSON array.",
                }
            ],
            tier="operational",
            max_tokens=2048,
            temperature=0.1,
            agent_id=self.agent_name,
        )

        text = extract_response_text(response)
        payload = decode_json_payload(text)
        if not isinstance(payload, list):
            return []

        insights: list[NicheInsight] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                insights.append(NicheInsight(**item))
            except (ValidationError, TypeError):
                logger.debug("Skipping invalid insight: %s", item)

        return insights

    @staticmethod
    def format_niche_research(niche: dict[str, Any]) -> str:
        """Format niche research results for the strategy prompt."""
        if not niche:
            return "No niche research available this cycle."

        parts: list[str] = []
        trending = niche.get("trending_topics", [])
        if trending:
            parts.append("**Trending topics:**")
            for topic in trending[:5]:
                parts.append(f"  - {topic}")

        angles = niche.get("recommended_angles", [])
        if angles:
            parts.append("**Recommended angles:**")
            for angle in angles[:5]:
                parts.append(f"  - {angle}")

        insights = niche.get("insights", [])
        if insights:
            parts.append(f"**{len(insights)} insights extracted from niche research.**")

        return "\n".join(parts) if parts else "No niche research available this cycle."
