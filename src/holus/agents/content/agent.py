"""Content pipeline agent with LangGraph.

Four-stage pipeline:
  1. text_generator   -- Sonnet produces article/post text.
  2. image_generator  -- ComfyUI or Replicate generates visuals.
  3. video_generator  -- Kling AI + ElevenLabs + Creatomate for video.
  4. distributor      -- Late API publishes to 13+ platforms.

Performance feedback is stored in Mem0 and feeds back into strategy.
"""

from __future__ import annotations

import json
import logging
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from holus.agents.base import BaseAgent
from holus.core.events import EventType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ContentState(TypedDict):
    """State flowing through the content LangGraph pipeline."""

    # Inputs
    content_brief: dict  # topic, platforms, keywords, type, voice
    strategy_context: dict  # from Mem0: what worked before

    # Pipeline outputs
    text_output: str | None
    image_urls: list[str]
    video_url: str | None
    distribution_result: dict | None

    # Performance tracking
    post_ids: list[str]
    performance_metrics: dict | None

    # Observability
    messages: Annotated[list, operator.add]
    error: str | None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

TEXT_GENERATOR_PROMPT = """You are the Content Generator for Holus.
Write high-quality content based on the brief provided.

## Guidelines
- Match the specified brand voice (professional/casual/technical)
- Optimize for the target platforms
- Include SEO keywords naturally
- Keep content actionable and mechanism-focused
- Adapt length to platform: Twitter (280 chars), LinkedIn (1300 chars), Blog (1500+ words)

## Output
Return JSON: {"text": "...", "headline": "...", "hashtags": ["..."], "meta_description": "..."}
"""


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def text_generator(state: ContentState) -> dict[str, Any]:
    """Generate text content using Sonnet."""
    from langchain_anthropic import ChatAnthropic

    sonnet = ChatAnthropic(model="claude-sonnet-4-5-20250514", temperature=0.3, max_tokens=4096)

    brief = state["content_brief"]
    strategy = state.get("strategy_context", {})

    response = sonnet.invoke(
        [
            {"role": "system", "content": TEXT_GENERATOR_PROMPT},
            {
                "role": "user",
                "content": (
                    f"## Content Brief\n{json.dumps(brief)}\n\n"
                    f"## What Worked Before (from memory)\n{json.dumps(strategy)}\n\n"
                    "Generate the content piece. Return JSON."
                ),
            },
        ]
    )

    try:
        result = json.loads(response.content)
        text_output = result.get("text", response.content)
    except (json.JSONDecodeError, TypeError):
        text_output = (
            response.content if isinstance(response.content, str) else str(response.content)
        )

    return {
        "text_output": text_output,
        "messages": [{"node": "text_generator", "output": text_output[:200]}],
    }


def image_generator(state: ContentState) -> dict[str, Any]:
    """Generate images via ComfyUI (local) or Replicate (cloud).

    For now, returns a placeholder.  The actual ComfyUI integration
    queues a workflow and polls for completion.
    """
    brief = state["content_brief"]
    content_type = brief.get("type", "article")

    if content_type in ("social", "video"):
        # Queue ComfyUI workflow for image generation
        logger.info("Image generation requested for %s", brief.get("topic", ""))
        # In production: self.comfyui.queue_workflow(...)
        image_urls = []  # Populated by ComfyUI callback
    else:
        image_urls = []

    return {
        "image_urls": image_urls,
        "messages": [{"node": "image_generator", "output": f"{len(image_urls)} images"}],
    }


def video_generator(state: ContentState) -> dict[str, Any]:
    """Generate video content (Kling AI + ElevenLabs + Creatomate).

    Triggered only for video content types.
    """
    brief = state["content_brief"]
    content_type = brief.get("type", "article")

    if content_type != "video":
        return {
            "video_url": None,
            "messages": [{"node": "video_generator", "output": "Skipped (not video type)"}],
        }

    # In production: call Kling AI for video, ElevenLabs for voiceover,
    # Creatomate for assembly
    logger.info("Video generation requested for %s", brief.get("topic", ""))

    return {
        "video_url": None,  # Populated by video pipeline callback
        "messages": [{"node": "video_generator", "output": "Video pipeline triggered"}],
    }


def distributor(state: ContentState) -> dict[str, Any]:
    """Distribute content to platforms via Late API."""

    brief = state["content_brief"]
    text = state.get("text_output", "")
    platforms = brief.get("platforms", [])

    if not text or not platforms:
        return {
            "distribution_result": {"status": "skipped", "reason": "No text or platforms"},
            "messages": [{"node": "distributor", "output": "Skipped"}],
        }

    # In production, this calls the Late API client
    # For now, log the distribution intent
    result = {
        "status": "queued",
        "platforms": platforms,
        "text_length": len(text),
        "image_count": len(state.get("image_urls", [])),
        "has_video": state.get("video_url") is not None,
    }

    logger.info("Content distributed to %s platforms", len(platforms))

    return {
        "distribution_result": result,
        "post_ids": [],  # Populated by Late API response
        "messages": [{"node": "distributor", "output": result}],
    }


def performance_tracker(state: ContentState) -> dict[str, Any]:
    """Collect initial performance metrics (scheduled for later follow-up)."""
    return {
        "performance_metrics": {"status": "tracking_initiated"},
        "messages": [{"node": "performance_tracker", "output": "Tracking initiated"}],
    }


# ---------------------------------------------------------------------------
# ContentAgent
# ---------------------------------------------------------------------------


class ContentAgent(BaseAgent):
    """LangGraph-based content pipeline agent."""

    agent_name = "content-agent"

    @property
    def system_prompt(self) -> str:
        return TEXT_GENERATOR_PROMPT

    @property
    def model_tier(self):
        return "operational"

    def build_graph(self) -> StateGraph:
        """Construct the content pipeline graph."""
        graph = StateGraph(ContentState)

        graph.add_node("text_generator", text_generator)
        graph.add_node("image_generator", image_generator)
        graph.add_node("video_generator", video_generator)
        graph.add_node("distributor", distributor)
        graph.add_node("performance_tracker", performance_tracker)

        # Linear pipeline: text -> image -> video -> distribute -> track
        graph.add_edge(START, "text_generator")
        graph.add_edge("text_generator", "image_generator")
        graph.add_edge("image_generator", "video_generator")
        graph.add_edge("video_generator", "distributor")
        graph.add_edge("distributor", "performance_tracker")
        graph.add_edge("performance_tracker", END)

        return graph

    def default_state(self) -> dict[str, Any]:
        return {
            "content_brief": {},
            "strategy_context": {},
            "text_output": None,
            "image_urls": [],
            "video_url": None,
            "distribution_result": None,
            "post_ids": [],
            "performance_metrics": None,
            "messages": [],
            "error": None,
        }

    async def run_content_pipeline(
        self,
        content_brief: dict[str, Any],
        strategy_context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the full content pipeline.

        Args:
            content_brief: Topic, platforms, keywords, type, voice.
            strategy_context: What worked before (from Mem0).
        """
        self.check_kill_switch()

        state = self.default_state()
        state["content_brief"] = content_brief
        state["strategy_context"] = strategy_context or {}

        result = await self.run(state, **kwargs)

        # Publish event
        if result.get("distribution_result", {}).get("status") == "queued":
            self.publish_event(
                "holus.content.performance",
                EventType.CONTENT_PUBLISHED,
                payload={
                    "topic": content_brief.get("topic"),
                    "platforms": content_brief.get("platforms", []),
                },
            )

        return result
