# Spec 012: Knowledge & Learning System

**Status:** implemented
**Phase:** Phase 1
**Author:** Camilo Martinez
**Created:** 2026-02-26
**Updated:** 2026-02-26

## Problem

The marketing agent makes decisions in a vacuum. There is no persistent knowledge base it can consult before choosing what to post, no structured log of past decisions and outcomes, and no automated loop that extracts patterns from results. Without these, the agent cannot learn from experience -- it repeats mistakes, misses trends, and cannot improve its strategy over time. The founder has no visibility into what the agent has learned or why it makes the decisions it does.

## Goals

- Marketing agent reads domain knowledge (platform best practices, audience profiles, content formats) before making decisions
- Every agent decision and outcome is logged to an append-only trajectory for future analysis
- Weekly learning loop extracts patterns from trajectories and real analytics, updating the knowledge base and MEMORY.md
- Agents can file knowledge gap requests when they encounter decisions where information is insufficient
- Founder can review what the agent has learned by reading MEMORY.md (committed to git)
- Learning flywheel: post content, track results, extract patterns, improve decisions, post better content

## Non-Goals

- Mem0 vector memory integration -- future Phase 2 feature, not needed for initial learning loop
- Cross-agent knowledge sharing -- deferred to coordinator spec, single-agent focus first
- External knowledge sources (web scraping, competitor analysis) -- adds complexity without proven value yet

## Solution

Three interconnected systems create a learning flywheel:

1. **Knowledge Base** (`agentic/memory/knowledge/current/`) -- Structured markdown files with metadata headers that agents read before making decisions. Files cover platform best practices, audience profiles, content formats, and performance patterns. Old versions are archived automatically when updated.

2. **Trajectory Logging** (`.self-improvement/memory/trajectory.jsonl`) -- Append-only JSONL log of every agent decision and outcome. Entries include agent_id, timestamp, task_type, status, cost, and rich metadata. Supports filtered reads and time-based summaries.

3. **Weekly Learning Loop** -- The manager agent runs weekly (via `just improve`), reads trajectory data and real analytics from social-media MCP, uses Opus to extract patterns, and updates MEMORY.md and knowledge files with new insights. Requires a minimum of 5 data points before extracting patterns to avoid premature conclusions.

Additionally, a **Knowledge Gap Detection** system lets agents file requests when they need information they do not have, which the manager agent prioritizes during the weekly cycle.

## Implementation Notes

### SPEC-001: Knowledge Base

| Field | Value |
|-------|-------|
| Description | Structured markdown files in `agentic/memory/knowledge/current/` that agents read before making decisions |
| Trigger | Read at the start of every marketing cycle (observe stage) |
| Input | Knowledge files written by humans, research agents, or the learning loop |
| Output | Loaded into agent context as part of the system prompt |
| Validation | Each file must have metadata header (last updated, confidence, affects) |
| Auth Required | No |

Knowledge file structure:

```
agentic/memory/knowledge/
├── README.md              # Index of all topics
├── current/               # Active knowledge files
│   ├── platforms.md       # Social media platform knowledge
│   ├── audience-profiles.md  # Target audience details
│   ├── content-formats.md # Content templates and best practices
│   ├── content-marketing-strategy.md  # Strategy insights
│   └── performance-patterns.md  # Learned from analytics (auto-updated)
├── archive/               # Previous versions (auto-rotated)
│   └── .gitkeep
└── requests/              # Knowledge gap requests from agents
    └── README.md
```

Knowledge file metadata header:

```markdown
# Knowledge: Topic Name

**Last updated:** YYYY-MM-DD
**Updated by:** agent_name | human
**Confidence:** preliminary | medium | high | validated
**Affects:** which agents/decisions this knowledge impacts
**Research cadence:** daily | weekly | monthly
```

### SPEC-002: Trajectory Logging

| Field | Value |
|-------|-------|
| Description | Append-only JSONL log of every agent decision and outcome |
| Trigger | End of every agent action (marketing cycle, content generation, etc.) |
| Input | Decision details, outcome, cost, metadata |
| Output | One JSON line appended to `.self-improvement/memory/trajectory.jsonl` |
| Validation | Each entry must have agent_id, timestamp, task_type, status |
| Auth Required | No |

```python
# src/holus/memory/trajectory.py

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel


class TrajectoryEntry(BaseModel):
    agent_id: str
    timestamp: datetime = None
    task_type: str
    task_summary: str
    status: str  # "success" | "error" | "skipped"
    duration_seconds: float | None = None
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    metadata: dict = {}
    error_message: str | None = None

    def model_post_init(self, __context: object) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class TrajectoryLogger:
    def __init__(
        self, path: Path = Path(".self-improvement/memory/trajectory.jsonl")
    ):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: TrajectoryEntry | dict) -> None:
        if isinstance(entry, dict):
            entry = TrajectoryEntry(**entry)
        with open(self.path, "a") as f:
            f.write(entry.model_dump_json() + "\n")

    def read_all(self) -> list[TrajectoryEntry]:
        if not self.path.exists():
            return []
        entries = []
        for line in self.path.read_text().strip().split("\n"):
            if line:
                entries.append(TrajectoryEntry.model_validate_json(line))
        return entries

    def read_filtered(
        self,
        agent_id: str | None = None,
        task_type: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[TrajectoryEntry]:
        entries = self.read_all()
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        if task_type:
            entries = [e for e in entries if e.task_type == task_type]
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        return entries[-limit:]

    def summary(self, days: int = 7) -> dict:
        """Generate a summary of recent activity."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [
            e for e in self.read_all() if e.timestamp >= cutoff
        ]
        return {
            "total_entries": len(recent),
            "successes": sum(1 for e in recent if e.status == "success"),
            "errors": sum(1 for e in recent if e.status == "error"),
            "total_cost_usd": sum(
                e.cost_usd for e in recent if e.cost_usd
            ),
            "agents_active": list(
                set(e.agent_id for e in recent)
            ),
            "task_types": list(set(e.task_type for e in recent)),
        }
```

### SPEC-003: Weekly Learning Loop

| Field | Value |
|-------|-------|
| Description | Manager agent analyzes trajectory data + social-media analytics weekly, extracts patterns, updates knowledge base and MEMORY.md |
| Trigger | Weekly via `just improve` or launchd (Sunday 7am) |
| Input | trajectory.jsonl, analytics from social-media MCP, current knowledge files, MEMORY.md |
| Output | Updated MEMORY.md, updated knowledge files, insights logged |
| Validation | New insights must have sample_size >= 5 and confidence level |
| Auth Required | `ANTHROPIC_API_KEY` |

```python
# Learning loop (run by manager agent)

async def weekly_learning_cycle(self):
    """Extract patterns from recent trajectories and update knowledge."""

    tl = TrajectoryLogger()
    recent = tl.read_filtered(agent_id="marketing-agent", limit=100)

    if len(recent) < 5:
        logger.info("Not enough data for pattern extraction", count=len(recent))
        return

    # Fetch real analytics from social-media MCP
    analytics = await self.call_mcp("social-media", "get_analytics", days=7)
    top_posts = await self.call_mcp("social-media", "get_top_posts", limit=10)

    # Group by content_type + platform
    patterns = {}
    for entry in recent:
        meta = entry.metadata
        key = f"{meta.get('content_type', 'unknown')}_{meta.get('platform', 'unknown')}"
        if key not in patterns:
            patterns[key] = {"count": 0, "statuses": []}
        patterns[key]["count"] += 1
        patterns[key]["statuses"].append(entry.status)

    # Use Opus to analyze patterns + real analytics
    response = await self.claude.create_cached_message(
        task_type="strategic_planning",
        system_prompt=LEARNING_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Analyze these marketing patterns and extract insights:

Trajectory data (last 7 days):
{json.dumps([e.model_dump() for e in recent], default=str)}

Real platform analytics (last 7 days):
{json.dumps(analytics, default=str)}

Top performing posts:
{json.dumps(top_posts, default=str)}

Current MEMORY.md:
{Path('agentic/memory/MEMORY.md').read_text()}

Return:
1. New insights to add to MEMORY.md
2. Knowledge files to update
3. Strategy adjustments for next week (based on real engagement data)
""",
        }],
    )

    # Update MEMORY.md with new insights
    await self.update_memory(response)

    # Update knowledge files if needed
    await self.update_knowledge(response)
```

### SPEC-004: Knowledge Gap Detection

| Field | Value |
|-------|-------|
| Description | Agents can file "knowledge gap requests" when they need information they don't have |
| Trigger | Agent encounters a decision where knowledge is insufficient |
| Input | Gap description, priority, related topic |
| Output | Request file in `agentic/memory/knowledge/requests/` |
| Validation | Must specify what's needed and why |
| Auth Required | No |

```python
# src/holus/memory/knowledge_gaps.py

from pathlib import Path
from datetime import date

def file_knowledge_gap(
    filed_by: str,
    what_i_need: str,
    why_i_need_it: str,
    priority: str = "medium",
    related_topic: str = "",
) -> Path:
    """File a knowledge gap request for expert agents to resolve."""
    requests_dir = Path("agentic/memory/knowledge/requests")
    requests_dir.mkdir(parents=True, exist_ok=True)

    slug = what_i_need[:50].lower().replace(" ", "-")
    filename = f"{date.today().isoformat()}-{slug}.md"
    path = requests_dir / filename

    content = f"""# Knowledge Gap Request

**Filed by:** {filed_by}
**Priority:** {priority}
**Related topic:** {related_topic}
**Filed on:** {date.today().isoformat()}

## What I Need to Know

{what_i_need}

## Why I Need It

{why_i_need_it}

## Status

- [ ] Researched
- [ ] Written to knowledge file
- [ ] Request closed
"""
    path.write_text(content)
    return path
```

### Data Structures

Knowledge update event (published to event bus):

```json
{
  "source_agent": "manager",
  "event_type": "knowledge_updated",
  "timestamp": "2026-03-02T07:15:00Z",
  "payload": {
    "topic": "performance-patterns",
    "file": "agentic/memory/knowledge/current/performance-patterns.md",
    "confidence": "medium",
    "insights_count": 3,
    "sample_size": 28,
    "key_insight": "Tutorial posts get 2.3x engagement vs promotional posts on LinkedIn"
  }
}
```

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/memory/trajectory.py` | Modified | TrajectoryLogger with filtering and summary |
| `src/holus/memory/knowledge_gaps.py` | New | Knowledge gap request system |
| `src/holus/memory/__init__.py` | Modified | Export TrajectoryLogger, file_knowledge_gap |
| `agentic/memory/knowledge/current/performance-patterns.md` | New (auto-generated) | Patterns learned from analytics |
| `tests/unit/memory/test_trajectory.py` | New | Trajectory logger tests |
| `tests/unit/memory/test_knowledge_gaps.py` | New | Knowledge gap tests |

### Security Notes

- Trajectory files may contain content decisions but no secrets
- Knowledge files are committed to git (public, no secrets)
- MEMORY.md is committed to git (public, no secrets)
- trajectory.jsonl is gitignored (may contain detailed agent reasoning)

### Dependencies

- Depends on: [Spec 010](./010-marketing-agent.md) — the marketing agent that reads knowledge and writes trajectories
- Depends on: [Spec 009](./009-autonomous-build-system.md) — the builder also logs to trajectory
- Depended on by: [Spec 016](./016-social-media-integration-v2.md) — analytics data feeds into the learning loop

## Edge Cases & Failure Modes

**EDGE-001: Trajectory file is empty (cold start)**
- Scenario: First week, no trajectory data
- Expected behavior: Learning loop skips pattern extraction, logs "not enough data"
- Recovery: Data accumulates naturally over cycles.

**EDGE-002: Conflicting patterns in trajectory**
- Scenario: Some cycles show tutorials work best, others show demos work best
- Expected behavior: Opus analyzes both patterns and reports with confidence levels. Low-confidence insights are marked as "preliminary".
- Recovery: More data resolves the conflict over time.

**EDGE-003: Knowledge file corruption**
- Scenario: Knowledge file has invalid markdown or missing metadata
- Expected behavior: Agent logs warning and skips the file. Other knowledge files still loaded.
- Recovery: Human or manager agent fixes the file.

**EDGE-004: Trajectory file grows too large**
- Scenario: After months of operation, trajectory.jsonl is hundreds of MB
- Expected behavior: Learning loop only reads last N entries (configurable, default 1000). Older entries remain for archival.
- Recovery: Periodic manual or automated archiving of old entries.

## Observability

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Knowledge loading (all files) | < 5s | Time to read all current/ files |
| Trajectory append | < 10ms | File write latency |
| Trajectory read (1000 entries) | < 2s | File read + parse time |
| Weekly learning cycle | < 5 min | Opus analysis + file updates |
| Learning cycle cost | < $2 | Langfuse cost per cycle |

## Acceptance Criteria

- [ ] All knowledge files have the required metadata header
- [ ] Knowledge is loaded during marketing agent observe stage
- [ ] Knowledge directory is indexed in README.md
- [ ] Archive rotation works (old version moved to archive/ when updated)
- [ ] Agents can file knowledge gap requests in requests/
- [ ] `TrajectoryLogger.append()` adds one JSON line to trajectory.jsonl
- [ ] Entries include timestamp, agent_id, task_type, status, and metadata
- [ ] `read_filtered()` supports filtering by agent, task type, and time
- [ ] `summary()` returns aggregate stats for a time period
- [ ] Trajectory file is append-only (never edited or truncated)
- [ ] trajectory.jsonl is gitignored
- [ ] Learning loop runs weekly via `just improve`
- [ ] Analyzes trajectory.jsonl entries from the past 7 days
- [ ] Fetches real analytics from social-media MCP (`get_analytics`, `get_top_posts`)
- [ ] Requires minimum 5 data points before extracting patterns
- [ ] Uses Opus for pattern analysis
- [ ] Updates MEMORY.md with new insights (appends, doesn't overwrite)
- [ ] Updates knowledge files when significant patterns emerge
- [ ] Archives old knowledge versions before updating
- [ ] Logs the learning cycle itself to trajectory.jsonl
- [ ] Agents can file knowledge gaps via `file_knowledge_gap()`
- [ ] Gap requests are saved as markdown files in requests/
- [ ] Manager agent reads and prioritizes gap requests during weekly cycle
- [ ] Resolved gaps are deleted after knowledge is written
