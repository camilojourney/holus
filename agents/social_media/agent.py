"""
Social Media Agent — Manages online presence.
Drafts posts, monitors engagement, curates content.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from core.base_agent import BaseAgent
from core.llm import TaskComplexity


class SocialMediaAgent(BaseAgent):
    name = "social_media"
    description = "Manages social media presence — drafts, posts, monitors"
    schedule = "3x daily"

    def get_tools(self) -> list:

        @tool
        def draft_post(topic: str, platform: str = "twitter") -> str:
            """Draft a social media post on a given topic."""
            return f"[Placeholder] Would draft {platform} post about: {topic}"

        @tool
        def search_trending_topics(niche: str = "AI") -> str:
            """Find trending topics in the AI/tech niche for content ideas."""
            return f"[Placeholder] Would search trending topics in {niche}"

        @tool
        def schedule_post(content: str, platform: str, time: str = "next_slot") -> str:
            """Schedule a post for publishing. Requires approval."""
            return f"[Placeholder] Would schedule post on {platform} at {time}"

        @tool
        def check_engagement() -> str:
            """Check recent engagement metrics (likes, replies, follows)."""
            return "[Placeholder] Would fetch engagement metrics from Twitter/LinkedIn API"

        @tool
        def find_relevant_content(topic: str) -> str:
            """Find relevant content to engage with or share."""
            return f"[Placeholder] Would search for shareable content about {topic}"

        return [draft_post, search_trending_topics, schedule_post, check_engagement, find_relevant_content]

    def get_system_prompt(self) -> str:
        topics = self.config.get("topics", ["AI/ML", "startups", "data science"])
        tone = self.config.get("tone", "insightful, concise, technical but accessible")
        return f"""You are the Social Media agent for Holus.

Your mission: Build and maintain a strong professional presence on social media.

CONTENT TOPICS: {', '.join(topics)}
TONE: {tone}
MAX POSTS PER DAY: {self.config.get('max_posts_per_day', 3)}

WORKFLOW:
1. Check trending topics in AI/tech
2. Review recent research and news (check shared memory from Research Scout)
3. Draft 1-2 posts with unique insights
4. Send drafts for approval before posting
5. Check engagement on recent posts and note what works

RULES:
- Be authentic — don't sound like a generic AI bot
- Add original insights, not just reshares
- Engage with replies/comments when found
- Track what content performs best in memory
- Never post without approval if configured
"""

    async def run(self) -> dict[str, Any]:
        logger.info("📱 Social Media agent creating content...")

        # Check shared memory for research scout findings
        research = self.recall("AI trends news", n_results=3, shared=True)
        context = "\n".join([r["content"] for r in research]) if research else "No recent research available."

        result = await self.execute(
            f"Create social media content for today. "
            f"Recent research context:\n{context[:500]}\n\n"
            f"Draft posts and send for approval.",
            complexity=TaskComplexity.COMPLEX,
        )

        if self.config.get("require_approval", True):
            await self.notify(f"📱 *Social Media Drafts*\n\n{result[:500]}\n\nReply ✅ to approve.")

        return {"status": "completed", "result": result}
