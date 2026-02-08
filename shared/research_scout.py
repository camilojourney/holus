"""
Research Scout Agent — Monitors GitHub, arxiv, newsletters.
Generates digests and shares findings with other agents.
Directly inspired by AI Jason's GitHub trending report feature.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from shared.base_agent import BaseAgent
from shared.llm import TaskComplexity


class ResearchScoutAgent(BaseAgent):
    name = "research_scout"
    description = "Monitors AI/ML research, GitHub trending, generates digests"
    schedule = "daily at 7am"

    def get_tools(self) -> list:

        @tool
        def scrape_github_trending(language: str = "", since: str = "daily") -> str:
            """Scrape GitHub trending repositories, optionally filtered by language."""
            # TODO: Implement with httpx + BeautifulSoup
            return f"[Placeholder] Would scrape GitHub trending (lang={language}, since={since})"

        @tool
        def search_arxiv(query: str, max_results: int = 10) -> str:
            """Search arxiv for recent papers matching a query."""
            # TODO: Implement with arxiv API
            return f"[Placeholder] Would search arxiv for: {query}, max {max_results} results"

        @tool
        def fetch_rss_feed(url: str) -> str:
            """Fetch and parse an RSS feed for latest entries."""
            # TODO: Implement with feedparser
            return f"[Placeholder] Would fetch RSS feed: {url}"

        @tool
        def summarize_content(content: str) -> str:
            """Summarize a long piece of content into key takeaways."""
            return f"[Placeholder] Would summarize: {content[:100]}..."

        @tool
        def generate_digest(items: str) -> str:
            """Generate a formatted digest report from collected items."""
            return f"[Placeholder] Would generate markdown digest from items"

        return [scrape_github_trending, search_arxiv, fetch_rss_feed, summarize_content, generate_digest]

    def get_system_prompt(self) -> str:
        sources = self.config.get("sources", {})
        return f"""You are the Research Scout agent for Holus.

Your mission: Stay on top of AI/ML research and share findings.

SOURCES:
- GitHub Trending: {sources.get('github_trending', True)}
- arxiv categories: {sources.get('arxiv', {}).get('categories', ['cs.AI', 'cs.LG'])}
- RSS feeds: {sources.get('rss_feeds', [])}

WORKFLOW:
1. Scrape GitHub trending for AI/ML repos
2. Search arxiv for latest papers in target categories
3. Fetch RSS feeds from AI blogs
4. Filter for most relevant/impactful items
5. Generate a daily digest
6. Store key findings in SHARED memory (other agents can use them)
7. Send digest via notification

OUTPUT FORMAT:
## 🔬 Daily AI Research Digest

### 🔥 GitHub Trending
- [repo-name](url) — description (⭐ stars)

### 📄 New Papers
- Title — key finding (1-2 sentences)

### 📰 Blog Posts & News
- Title — key takeaway

### 💡 Takeaway
One paragraph summarizing the most important trend or development.
"""

    async def run(self) -> dict[str, Any]:
        logger.info("🔬 Research Scout scanning sources...")

        result = await self.execute(
            "Run the daily research scan. Check GitHub trending, arxiv, and RSS feeds. "
            "Generate a digest of the most important AI/ML developments.",
            complexity=TaskComplexity.SIMPLE,
        )

        # Store in shared memory so other agents can use it
        self.remember(
            f"Daily digest: {result[:500]}",
            metadata={"type": "daily_digest"},
            shared=True,
        )

        await self.notify(f"🔬 *Research Digest*\n\n{result[:1000]}")

        return {"status": "completed", "result": result}
