"""Holus coordinator agent (Phase 3): lightweight daily synthesis.

The coordinator is NOT a real-time router.  It is a daily intelligence
synthesis agent that reads cross-project events and identifies optimization
opportunities.  Making it real-time would introduce the coordination overhead
and compound error problems the federated architecture avoids.

Schedule: daily at 9 PM (configurable via n8n cron trigger).
Model: always Opus 4 (strategic reasoning).

Inputs:
  - Redis Streams (last 24h events from all channels)
  - Agent reports (from .self-improvement/reports/)

Outputs:
  - Daily report (Slack/email to founder)
  - Advisory directives (published to event bus -- agents can ignore)
  - Cross-project knowledge graph updates
"""

from __future__ import annotations

import json
import logging
import operator
from datetime import UTC, datetime
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from holus.agents.base import BaseAgent
from holus.core.events import EventType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class CoordinatorState(TypedDict):
    """State for the Holus coordinator graph."""

    # Daily inputs
    trading_summary: dict
    content_summary: dict
    coding_summary: dict
    pilaster_summary: dict

    # Cross-project outputs
    insights: Annotated[list[str], operator.add]
    directives: Annotated[list[dict], operator.add]
    daily_report: str | None

    # Observability
    messages: Annotated[list, operator.add]
    error: str | None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

COORDINATOR_PROMPT = """You are Holus, the cross-project intelligence coordinator.
You review daily summaries from 4 domain agents and identify:

1. Cross-domain patterns (content engagement predicts market moves?)
2. Resource allocation opportunities (which project needs more attention?)
3. Risk factors (trading agent underperforming? content pipeline blocked?)
4. Action items for each domain agent

## Rules
- You NEVER execute trades, write content, or commit code directly.
- Your job is SYNTHESIS and DELEGATION only.
- Directives are ADVISORY -- agents can ignore them.
- Flag anything requiring human attention.

## Output Format
Return JSON:
{
  "insights": ["insight 1", "insight 2", ...],
  "directives": [
    {"agent": "trading", "action": "...", "priority": "high/medium/low"},
    ...
  ],
  "risk_flags": ["..."],
  "report_summary": "..."
}
"""

# Channels the coordinator reads from daily
CONSUMED_CHANNELS = [
    "holus.trading.signals",
    "holus.content.performance",
    "holus.coding.deploys",
    "holus.pilaster.workflows",
    "holus.system.alerts",
]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def gather_events(state: CoordinatorState) -> dict[str, Any]:
    """Read last 24h of events from Redis Streams.

    This populates the domain summaries from the event bus.
    """
    from holus.core.config import HolusConfig
    from holus.core.events import EventBus

    config = HolusConfig.load()
    bus = EventBus(redis_url=config.redis_url)

    try:
        all_events = bus.read_streams_since(CONSUMED_CHANNELS, since_hours=24)
    except Exception as exc:
        logger.warning("Failed to read event streams: %s", exc)
        all_events = {}
    finally:
        bus.close()

    # Build per-domain summaries from events
    trading_events = all_events.get("holus.trading.signals", [])
    content_events = all_events.get("holus.content.performance", [])
    coding_events = all_events.get("holus.coding.deploys", [])
    pilaster_events = all_events.get("holus.pilaster.workflows", [])

    return {
        "trading_summary": {
            "event_count": len(trading_events),
            "events": [e.payload for e in trading_events[:20]],
        },
        "content_summary": {
            "event_count": len(content_events),
            "events": [e.payload for e in content_events[:20]],
        },
        "coding_summary": {
            "event_count": len(coding_events),
            "events": [e.payload for e in coding_events[:20]],
        },
        "pilaster_summary": {
            "event_count": len(pilaster_events),
            "events": [e.payload for e in pilaster_events[:20]],
        },
        "messages": [{"node": "gather_events", "output": "Events gathered"}],
    }


def synthesize(state: CoordinatorState) -> dict[str, Any]:
    """Cross-project synthesis using Opus 4.

    This is the core intelligence of the coordinator:  it reads all domain
    summaries and generates cross-project insights and advisory directives.
    """
    from langchain_anthropic import ChatAnthropic

    opus = ChatAnthropic(
        model="claude-opus-4-20250514",
        temperature=0.1,  # Slight creativity for synthesis
        max_tokens=8192,
    )

    response = opus.invoke(
        [
            {"role": "system", "content": COORDINATOR_PROMPT},
            {
                "role": "user",
                "content": (
                    f"## Daily Domain Summaries ({datetime.now(UTC).strftime('%Y-%m-%d')})\n\n"
                    f"### Trading\n{json.dumps(state['trading_summary'], indent=2)}\n\n"
                    f"### Content/Media\n{json.dumps(state['content_summary'], indent=2)}\n\n"
                    f"### Coding Infrastructure\n{json.dumps(state['coding_summary'], indent=2)}\n\n"
                    f"### Pilaster.ai\n{json.dumps(state['pilaster_summary'], indent=2)}\n\n"
                    "Analyze these summaries. Return JSON with insights, directives, "
                    "risk_flags, and report_summary."
                ),
            },
        ]
    )

    try:
        content = response.content if isinstance(response.content, str) else str(response.content)
        result = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        content = response.content if isinstance(response.content, str) else str(response.content)
        result = {
            "insights": [content[:500]],
            "directives": [],
            "risk_flags": [],
            "report_summary": content[:1000],
        }

    return {
        "insights": result.get("insights", []),
        "directives": result.get("directives", []),
        "daily_report": result.get("report_summary", ""),
        "messages": [{"node": "synthesize", "output": "Synthesis complete"}],
    }


def publish_directives(state: CoordinatorState) -> dict[str, Any]:
    """Publish advisory directives to the event bus."""
    from holus.core.config import HolusConfig
    from holus.core.events import EventBus, HolusEvent

    config = HolusConfig.load()
    bus = EventBus(redis_url=config.redis_url)

    try:
        for directive in state.get("directives", []):
            event = HolusEvent(
                source_agent="holus-coordinator",
                event_type=EventType.CROSS_PROJECT_INSIGHT,
                payload=directive,
            )
            bus.publish("holus.coordinator.directives", event)
    finally:
        bus.close()

    return {
        "messages": [
            {
                "node": "publish_directives",
                "output": f"Published {len(state.get('directives', []))} directives",
            }
        ],
    }


# ---------------------------------------------------------------------------
# CoordinatorAgent
# ---------------------------------------------------------------------------


class CoordinatorAgent(BaseAgent):
    """Daily cross-project intelligence coordinator (Phase 3)."""

    agent_name = "holus-coordinator"

    @property
    def system_prompt(self) -> str:
        return COORDINATOR_PROMPT

    @property
    def model_tier(self):
        return "strategic"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(CoordinatorState)

        graph.add_node("gather_events", gather_events)
        graph.add_node("synthesize", synthesize)
        graph.add_node("publish_directives", publish_directives)

        graph.add_edge(START, "gather_events")
        graph.add_edge("gather_events", "synthesize")
        graph.add_edge("synthesize", "publish_directives")
        graph.add_edge("publish_directives", END)

        return graph

    def default_state(self) -> dict[str, Any]:
        return {
            "trading_summary": {},
            "content_summary": {},
            "coding_summary": {},
            "pilaster_summary": {},
            "insights": [],
            "directives": [],
            "daily_report": None,
            "messages": [],
            "error": None,
        }

    async def run_daily_synthesis(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the daily synthesis cycle.

        Called by n8n on a cron schedule (9 PM daily).
        """
        self.check_kill_switch()
        result = await self.run(**kwargs)

        # Publish the weekly synthesis event if it is Sunday
        weekday = datetime.now(UTC).weekday()
        if weekday == 6:  # Sunday
            self.publish_event(
                "holus.coordinator.directives",
                EventType.WEEKLY_SYNTHESIS,
                payload={
                    "insights": result.get("insights", []),
                    "report": result.get("daily_report", ""),
                },
            )

        return result
