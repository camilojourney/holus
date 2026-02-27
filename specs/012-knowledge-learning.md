# Spec 012: Knowledge & Learning System

## Feature: Persistent knowledge base and learning loop that makes the marketing agent smarter over time

### Overview

Holus needs to learn from what it does. This spec defines three systems: (1) the knowledge base (`.self-improvement/knowledge/`) that stores domain expertise the agent reads before making decisions, (2) trajectory logging that records every decision and outcome, and (3) the weekly learning loop that extracts patterns from trajectories and updates the knowledge base and MEMORY.md. Together, these create a flywheel: post content → track results → extract patterns → improve decisions → post better content.

### User Stories

- As the marketing agent, I want to read platform best practices before deciding what to post so that my decisions are informed.
- As the marketing agent, I want to log every decision I make so that patterns can be extracted later.
- As the manager agent, I want to analyze past decisions and results so that I can update the knowledge base with new insights.
- As a founder, I want to see what the agent has learned in MEMORY.md so that I can verify its strategy is sound.

---

### Core Specifications

**SPEC-001: Knowledge Base**

| Field | Value |
|-------|-------|
| Description | Structured markdown files in `.self-improvement/knowledge/current/` that agents read before making decisions |
| Trigger | Read at the start of every marketing cycle (observe stage) |
| Input | Knowledge files written by humans, research agents, or the learning loop |
| Output | Loaded into agent context as part of the system prompt |
| Validation | Each file must have metadata header (last updated, confidence, affects) |
| Auth Required | No |

Knowledge file structure:

```
.self-improvement/knowledge/
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

Acceptance Criteria:
- [ ] All knowledge files have the required metadata header
- [ ] Knowledge is loaded during marketing agent observe stage
- [ ] Knowledge directory is indexed in README.md
- [ ] Archive rotation works (old version moved to archive/ when updated)
- [ ] Agents can file knowledge gap requests in requests/

---

**SPEC-002: Trajectory Logging**

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

Acceptance Criteria:
- [ ] `TrajectoryLogger.append()` adds one JSON line to trajectory.jsonl
- [ ] Entries include timestamp, agent_id, task_type, status, and metadata
- [ ] `read_filtered()` supports filtering by agent, task type, and time
- [ ] `summary()` returns aggregate stats for a time period
- [ ] File is append-only (never edited or truncated)
- [ ] trajectory.jsonl is gitignored

---

**SPEC-003: Weekly Learning Loop**

| Field | Value |
|-------|-------|
| Description | Manager agent analyzes trajectory data weekly, extracts patterns, updates knowledge base and MEMORY.md |
| Trigger | Weekly via `just improve` or launchd (Sunday 7am) |
| Input | trajectory.jsonl, current knowledge files, MEMORY.md |
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

    # Group by content_type + platform
    patterns = {}
    for entry in recent:
        meta = entry.metadata
        key = f"{meta.get('content_type', 'unknown')}_{meta.get('platform', 'unknown')}"
        if key not in patterns:
            patterns[key] = {"count": 0, "statuses": []}
        patterns[key]["count"] += 1
        patterns[key]["statuses"].append(entry.status)

    # Use Opus to analyze patterns
    response = await self.claude.create_cached_message(
        task_type="strategic_planning",
        system_prompt=LEARNING_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Analyze these marketing patterns and extract insights:

Trajectory data (last 7 days):
{json.dumps([e.model_dump() for e in recent], default=str)}

Current MEMORY.md:
{Path('.self-improvement/MEMORY.md').read_text()}

Return:
1. New insights to add to MEMORY.md
2. Knowledge files to update
3. Strategy adjustments for next week
""",
        }],
    )

    # Update MEMORY.md with new insights
    await self.update_memory(response)

    # Update knowledge files if needed
    await self.update_knowledge(response)
```

Acceptance Criteria:
- [ ] Learning loop runs weekly via `just improve`
- [ ] Analyzes trajectory.jsonl entries from the past 7 days
- [ ] Requires minimum 5 data points before extracting patterns
- [ ] Uses Opus for pattern analysis
- [ ] Updates MEMORY.md with new insights (appends, doesn't overwrite)
- [ ] Updates knowledge files when significant patterns emerge
- [ ] Archives old knowledge versions before updating
- [ ] Logs the learning cycle itself to trajectory.jsonl

---

**SPEC-004: Knowledge Gap Detection**

| Field | Value |
|-------|-------|
| Description | Agents can file "knowledge gap requests" when they need information they don't have |
| Trigger | Agent encounters a decision where knowledge is insufficient |
| Input | Gap description, priority, related topic |
| Output | Request file in `.self-improvement/knowledge/requests/` |
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
    requests_dir = Path(".self-improvement/knowledge/requests")
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

Acceptance Criteria:
- [ ] Agents can file knowledge gaps via `file_knowledge_gap()`
- [ ] Gap requests are saved as markdown files in requests/
- [ ] Manager agent reads and prioritizes gap requests during weekly cycle
- [ ] Resolved gaps are deleted after knowledge is written

---

### Data Structures

Knowledge update event (published to event bus):

```json
{
  "source_agent": "manager",
  "event_type": "knowledge_updated",
  "timestamp": "2026-03-02T07:15:00Z",
  "payload": {
    "topic": "performance-patterns",
    "file": ".self-improvement/knowledge/current/performance-patterns.md",
    "confidence": "medium",
    "insights_count": 3,
    "sample_size": 28,
    "key_insight": "Tutorial posts get 2.3x engagement vs promotional posts on LinkedIn"
  }
}
```

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/memory/trajectory.py` | Modified | TrajectoryLogger with filtering and summary |
| `src/holus/memory/knowledge_gaps.py` | New | Knowledge gap request system |
| `src/holus/memory/__init__.py` | Modified | Export TrajectoryLogger, file_knowledge_gap |
| `.self-improvement/knowledge/current/performance-patterns.md` | New (auto-generated) | Patterns learned from analytics |
| `tests/unit/memory/test_trajectory.py` | New | Trajectory logger tests |
| `tests/unit/memory/test_knowledge_gaps.py` | New | Knowledge gap tests |

---

### Edge Cases & Error Handling

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

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Knowledge loading (all files) | < 5s | Time to read all current/ files |
| Trajectory append | < 10ms | File write latency |
| Trajectory read (1000 entries) | < 2s | File read + parse time |
| Weekly learning cycle | < 5 min | Opus analysis + file updates |
| Learning cycle cost | < $2 | Langfuse cost per cycle |

---

### Security Considerations

- Trajectory files may contain content decisions but no secrets
- Knowledge files are committed to git (public, no secrets)
- MEMORY.md is committed to git (public, no secrets)
- trajectory.jsonl is gitignored (may contain detailed agent reasoning)

---

### Out of Scope

- Mem0 vector memory integration (future Phase 2 feature)
- DSPy prompt optimization (spec 003, monthly cycle)
- Cross-agent knowledge sharing (coordinator spec)
- External knowledge sources (web scraping, competitor analysis)

---

### Related Specs

- [010-marketing-agent.md](./010-marketing-agent.md) — the agent that reads knowledge and writes trajectories
- [009-autonomous-build-system.md](./009-autonomous-build-system.md) — the builder also logs to trajectory
- [003-content-pipeline.md](./003-content-pipeline.md) — DSPy optimization reads trajectory data

---

**Last Updated:** 2026-02-26
**Status:** Not Started
**Owner:** Camilo Martinez
