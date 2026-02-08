"""
YouTube Manager Agent — Orchestrates content creation pipeline.
Manages 5 sub-agents: Idea Gen, Research, Content, Thumbnail, Analytics.
Auto-approves score >8, human review for 5-8, rejects <5.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from shared.base_agent import BaseAgent
from shared.llm import TaskComplexity


class YouTubeManagerAgent(BaseAgent):
    name = "youtube_manager"
    description = "Orchestrates YouTube content creation with 5 specialized sub-agents"
    schedule = "daily at 9:00"

    def get_tools(self) -> list:
        config = self.config
        kb_path = config.get("knowledge_base_path", "youtube-kb.json")

        @tool
        def generate_ideas(niche: str, count: int = 5) -> str:
            """Generate video ideas based on trending topics and past performance.
            
            Args:
                niche: Content niche (e.g., 'AI tutorials', 'tech reviews')
                count: Number of ideas to generate
            """
            # Sub-agent: Idea Generator
            return (
                f"[IdeaGen] Would analyze:\n"
                f"- Trending topics in {niche}\n"
                f"- Competitor content gaps\n"
                f"- Past video performance\n"
                f"- Audience comments/requests\n"
                f"Generating {count} ideas..."
            )

        @tool
        def research_topic(topic: str) -> str:
            """Deep research on a video topic - stats, sources, talking points.
            
            Args:
                topic: The video topic to research
            """
            # Sub-agent: Research Agent
            return (
                f"[Research] Would compile:\n"
                f"- Key statistics and data points\n"
                f"- Expert quotes and sources\n"
                f"- Competitor video analysis\n"
                f"- SEO keywords for '{topic}'"
            )

        @tool
        def create_script(topic: str, style: str = "educational") -> str:
            """Generate video script with hook, body, CTA structure.
            
            Args:
                topic: Video topic
                style: Content style (educational, entertaining, tutorial)
            """
            # Sub-agent: Content Creator
            return (
                f"[Content] Would create {style} script for '{topic}':\n"
                f"- Hook (0-30s): Pattern interrupt\n"
                f"- Body: Key points with B-roll notes\n"
                f"- CTA: Subscribe + next video tease"
            )

        @tool
        def design_thumbnail(title: str, style: str = "bold") -> str:
            """Design thumbnail concept with text, imagery, colors.
            
            Args:
                title: Video title for thumbnail text
                style: Visual style (bold, minimal, curiosity-gap)
            """
            # Sub-agent: Thumbnail Designer
            return (
                f"[Thumbnail] Would design {style} thumbnail:\n"
                f"- Main text: '{title[:30]}...'\n"
                f"- Face expression: shocked/curious\n"
                f"- Color scheme: high contrast\n"
                f"- CTR optimization tips"
            )

        @tool
        def analyze_performance(video_id: str = None) -> str:
            """Analyze video/channel performance metrics.
            
            Args:
                video_id: Specific video ID or None for channel overview
            """
            # Sub-agent: Analytics Agent
            target = f"video {video_id}" if video_id else "channel"
            return (
                f"[Analytics] Would analyze {target}:\n"
                f"- Views, watch time, CTR\n"
                f"- Audience retention curve\n"
                f"- Traffic sources\n"
                f"- Recommendations for improvement"
            )

        @tool
        def score_content(title: str, script_summary: str, thumbnail_desc: str) -> dict:
            """Score content package 1-10 for virality potential.
            
            Args:
                title: Video title
                script_summary: Brief script summary
                thumbnail_desc: Thumbnail description
            
            Returns:
                Score dict with overall score and breakdown
            """
            # Would use LLM to score based on:
            # - Title clickability
            # - Script engagement potential
            # - Thumbnail appeal
            # - Trend alignment
            return {
                "overall": 7.5,
                "title_score": 8,
                "script_score": 7,
                "thumbnail_score": 8,
                "recommendation": "review",  # auto_approve, review, reject
            }

        @tool
        def queue_for_production(content_package: dict) -> str:
            """Add approved content to production queue.
            
            Args:
                content_package: Dict with title, script, thumbnail, schedule
            """
            title = content_package.get("title", "Untitled")
            self.remember(
                f"Queued for production: {title}",
                metadata={"type": "production_queue", "content": content_package},
            )
            return f"✅ Added '{title}' to production queue"

        @tool
        def get_content_calendar(days: int = 7) -> str:
            """Get upcoming content calendar.
            
            Args:
                days: Number of days to look ahead
            """
            queued = self.recall("production_queue", n_results=10)
            if not queued:
                return f"No videos scheduled for next {days} days"
            return f"Found {len(queued)} videos in pipeline"

        return [
            generate_ideas,
            research_topic,
            create_script,
            design_thumbnail,
            analyze_performance,
            score_content,
            queue_for_production,
            get_content_calendar,
        ]

    def get_system_prompt(self) -> str:
        config = self.config
        channel = config.get("channel_name", "My Channel")
        niche = config.get("niche", "tech/AI")
        upload_frequency = config.get("upload_frequency", "2x per week")

        return f"""You are the YouTube Manager agent for Holus, a personal AI workforce system.

Your mission: Create a content pipeline that grows the channel systematically.

CHANNEL PROFILE:
- Channel: {channel}
- Niche: {niche}
- Upload frequency: {upload_frequency}
- Goal: Build authority, grow subscribers, eventual monetization

YOUR TEAM (Sub-Agents):
1. **Idea Generator** — Finds trending topics, analyzes competition, spots content gaps
2. **Research Agent** — Deep dives on topics, gathers stats, finds sources
3. **Content Creator** — Writes scripts with hooks, retention strategies, CTAs
4. **Thumbnail Designer** — Creates click-worthy thumbnail concepts
5. **Analytics Agent** — Tracks performance, identifies what works

APPROVAL WORKFLOW:
- Score >8: Auto-approve for production
- Score 5-8: Flag for human review
- Score <5: Reject with feedback

DAILY WORKFLOW:
1. Check analytics for recent video performance
2. Generate new ideas based on trends + past performance
3. Pick top idea, run through research → script → thumbnail pipeline
4. Score the content package
5. Route based on score (approve/review/reject)
6. Update content calendar
7. Send daily summary to user

RULES:
- Never publish without scoring
- Always include retention hooks every 30 seconds in scripts
- Thumbnails must have <6 words
- Track all content in memory for performance correlation
- Learn from what works: high-retention videos inform future content
"""

    async def run(self) -> dict[str, Any]:
        """Execute the daily YouTube content pipeline."""
        logger.info("🎬 YouTube Manager starting daily pipeline...")

        # Check recent performance
        recent_vids = self.recall("video published", n_results=5)
        recent_ideas = self.recall("idea generated", n_results=10)

        # Run the content pipeline
        result = await self.execute(
            f"Run the daily YouTube content pipeline:\n"
            f"1. Check analytics on recent videos (last 5)\n"
            f"2. Generate 3 new video ideas based on trends\n"
            f"3. Pick the best idea and create a full content package\n"
            f"4. Score it and route appropriately\n"
            f"5. Update the content calendar\n\n"
            f"Recent videos in memory: {len(recent_vids)}\n"
            f"Ideas in backlog: {len(recent_ideas)}",
            complexity=TaskComplexity.COMPLEX,
        )

        # Extract any content needing review
        needs_review = "review" in result.lower() or "score: 5" in result.lower()

        if needs_review:
            await self.notify(
                f"🎬 *YouTube: Content Needs Review*\n\n{result[:500]}\n\n"
                f"Reply with APPROVE or REJECT"
            )
        else:
            await self.notify(
                f"🎬 *YouTube Pipeline Complete*\n\n{result[:500]}"
            )

        self.remember(
            f"Daily pipeline completed. Result: {result[:300]}",
            metadata={"type": "run_summary"},
        )

        return {
            "status": "completed",
            "needs_review": needs_review,
            "result": result,
        }

    async def handle_approval(self, video_id: str, approved: bool, feedback: str = None) -> dict:
        """Handle human approval/rejection of content."""
        if approved:
            self.remember(
                f"Video {video_id} APPROVED for production",
                metadata={"type": "approval", "video_id": video_id},
            )
            return {"status": "approved", "next": "queued_for_production"}
        else:
            self.remember(
                f"Video {video_id} REJECTED. Feedback: {feedback}",
                metadata={"type": "rejection", "video_id": video_id, "feedback": feedback},
            )
            return {"status": "rejected", "feedback": feedback}
