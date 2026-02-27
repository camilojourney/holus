# Spec 010: Marketing Agent

## Feature: AI marketing strategist agent that observes analytics, decides strategy, creates content, and posts to social media

### Overview

The marketing agent is the brain of Holus. It runs as an episodic agent (triggered every 30 minutes by cron or manually) and executes a ReAct loop: Observe (read analytics and product state), Reason (decide what content to create), Act (generate text/images and post), Evaluate (log decisions and results). It starts simple — text posts to LinkedIn and Twitter — and gains capabilities over time (images, video, more platforms). This spec defines the Phase 1 minimum: a working agent that can create and post text content.

### User Stories

- As a founder, I want the agent to read my social media analytics so that it knows what content performs well.
- As a founder, I want the agent to decide what to post about so that content strategy is data-informed.
- As a founder, I want the agent to create platform-specific content so that each post is optimized for its platform.
- As a founder, I want the agent to learn from results so that content quality improves over time.

---

### Core Specifications

**SPEC-001: Marketing Agent ReAct Loop**

| Field | Value |
|-------|-------|
| Description | LangGraph state machine with 4 stages: observe → reason → act → evaluate |
| Trigger | Cron (every 30 min) or manual (`just run-marketing`) |
| Input | Product state (`config/products.yaml`), knowledge base (`.self-improvement/knowledge/`), memory (`.self-improvement/MEMORY.md`) |
| Output | Published content, updated trajectory log, updated memory |
| Validation | Kill switch checked before every stage. Content reviewed before posting (Phase 1: human approval required). |
| Auth Required | `ANTHROPIC_API_KEY` |

```python
# src/holus/agents/marketing/agent.py

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, END

from holus.agents.base import BaseAgent


class MarketingState(TypedDict):
    # Observe stage outputs
    analytics: dict          # Latest engagement data from social media
    product_updates: dict    # What's new in each product
    memory_context: str      # Lessons learned from MEMORY.md
    knowledge: dict          # Platform best practices, audience profiles

    # Reason stage outputs
    content_decisions: list[dict]  # What to create and why
    strategy_reasoning: str        # Opus reasoning about strategy

    # Act stage outputs
    generated_content: list[dict]  # Created content pieces
    post_results: list[dict]       # Publishing results per platform

    # Evaluate stage outputs
    evaluation: dict         # What worked, what to remember


class MarketingAgent(BaseAgent):
    AGENT_NAME = "marketing-agent"
    DOMAIN = "marketing"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(MarketingState)

        graph.add_node("observe", self.observe)
        graph.add_node("reason", self.reason)
        graph.add_node("act", self.act)
        graph.add_node("evaluate", self.evaluate)

        graph.set_entry_point("observe")
        graph.add_edge("observe", "reason")
        graph.add_edge("reason", "act")
        graph.add_edge("act", "evaluate")
        graph.add_edge("evaluate", END)

        return graph

    async def observe(self, state: MarketingState) -> dict:
        """Read analytics, product state, knowledge, and memory."""
        ...

    async def reason(self, state: MarketingState) -> dict:
        """Use Opus to decide what content to create and why."""
        ...

    async def act(self, state: MarketingState) -> dict:
        """Generate content and post to platforms."""
        ...

    async def evaluate(self, state: MarketingState) -> dict:
        """Log decisions, update memory with lessons learned."""
        ...
```

Acceptance Criteria:
- [ ] `MarketingAgent` inherits from `BaseAgent` and implements `build_graph()`
- [ ] LangGraph state machine has 4 stages: observe → reason → act → evaluate
- [ ] Kill switch is checked before each stage
- [ ] Agent reads `config/products.yaml` during observe stage
- [ ] Agent reads `.self-improvement/knowledge/` during observe stage
- [ ] Agent reads `.self-improvement/MEMORY.md` during observe stage
- [ ] Agent uses Opus for strategy reasoning (model routing)
- [ ] Agent uses Sonnet for content generation
- [ ] Agent logs every decision to trajectory.jsonl
- [ ] `just run-marketing` triggers the agent manually

---

**SPEC-002: Observe Stage**

| Field | Value |
|-------|-------|
| Description | Collects all context the agent needs to make decisions |
| Trigger | Start of each marketing cycle |
| Input | Product config, knowledge files, memory, analytics (when available) |
| Output | Populated state with analytics, product_updates, memory_context, knowledge |
| Validation | Must complete within 30 seconds |
| Auth Required | No (reads local files). Analytics via MCP when available. |

Phase 1 observe (no MCP yet — read local files only):

```python
async def observe(self, state: MarketingState) -> dict:
    """Phase 1: Read local context. Phase 2+: Add MCP analytics."""
    import yaml
    from pathlib import Path

    # Read product state
    products = yaml.safe_load(Path("config/products.yaml").read_text())

    # Read knowledge base
    knowledge_dir = Path(".self-improvement/knowledge/current")
    knowledge = {}
    for f in knowledge_dir.glob("*.md"):
        knowledge[f.stem] = f.read_text()

    # Read memory
    memory = Path(".self-improvement/MEMORY.md").read_text()

    # Phase 2+: Read analytics from social-media MCP
    # analytics = await self.call_mcp("social-media", "get_analytics", days=7)
    analytics = {}  # No analytics in Phase 1

    return {
        "analytics": analytics,
        "product_updates": products,
        "memory_context": memory,
        "knowledge": knowledge,
    }
```

Acceptance Criteria:
- [ ] Products loaded from `config/products.yaml`
- [ ] Knowledge loaded from all files in `.self-improvement/knowledge/current/`
- [ ] Memory loaded from `.self-improvement/MEMORY.md`
- [ ] Completes within 30 seconds
- [ ] Graceful handling if files are missing

---

**SPEC-003: Reason Stage**

| Field | Value |
|-------|-------|
| Description | Opus analyzes context and decides what content to create |
| Trigger | After observe stage completes |
| Input | Full state from observe (analytics, products, knowledge, memory) |
| Output | `content_decisions`: list of what to create, for which product, on which platform, and why |
| Validation | Each decision must specify product, platform, content_type, topic, and reasoning |
| Auth Required | `ANTHROPIC_API_KEY` |

```python
async def reason(self, state: MarketingState) -> dict:
    """Use Opus to decide content strategy."""
    system_prompt = """You are Holus, an AI marketing strategist.

Your job: Decide what content to create for the product portfolio.

Products you promote:
{products}

What you know about platforms:
{platform_knowledge}

What you know about audiences:
{audience_knowledge}

Content formats that work:
{content_formats}

Lessons learned so far:
{memory}

Recent analytics:
{analytics}

RULES:
- Pick 1-3 content pieces to create this cycle
- Each piece must specify: product, platform, content_type, topic, reasoning
- Prioritize what has worked before (if analytics available)
- Rotate products so no product is neglected
- Tutorial/educational content > promotional content
- Return JSON array of decisions
"""

    # Use Opus for strategy (routed via task_type)
    response = await self.claude.create_cached_message(
        task_type="strategic_planning",
        system_prompt=system_prompt.format(
            products=state["product_updates"],
            platform_knowledge=state["knowledge"].get("platforms", ""),
            audience_knowledge=state["knowledge"].get("audience-profiles", ""),
            content_formats=state["knowledge"].get("content-formats", ""),
            memory=state["memory_context"],
            analytics=state["analytics"] or "No analytics yet (first cycles)",
        ),
        messages=[{"role": "user", "content": "What content should we create this cycle?"}],
    )

    return {
        "content_decisions": parse_decisions(response),
        "strategy_reasoning": extract_reasoning(response),
    }
```

Decision schema:

```python
class ContentDecision(BaseModel):
    product: str           # "pilaster" | "genpeli" | "invoz"
    platform: str          # "linkedin" | "twitter" | "tiktok" etc
    content_type: str      # "tutorial" | "demo" | "tips" | "thread" | "case_study"
    topic: str             # What the content is about
    reasoning: str         # Why this content, why now
    priority: int          # 1 = highest
    estimated_engagement: str  # "low" | "medium" | "high"
```

Acceptance Criteria:
- [ ] Reason stage uses Opus (via `task_type="strategic_planning"`)
- [ ] Prompt includes all context from observe stage
- [ ] Output is a structured list of `ContentDecision` objects
- [ ] Each decision includes reasoning (not just "what" but "why")
- [ ] 1-3 decisions per cycle

---

**SPEC-004: Act Stage**

| Field | Value |
|-------|-------|
| Description | Generates content based on decisions and posts to platforms |
| Trigger | After reason stage completes |
| Input | `content_decisions` from reason stage |
| Output | Generated content + publishing results |
| Validation | Content meets platform limits. Human approval required in Phase 1. |
| Auth Required | `ANTHROPIC_API_KEY`, platform API keys when posting |

Phase 1 act (text-only, save to file for human review):

```python
async def act(self, state: MarketingState) -> dict:
    """Generate content and prepare for publishing."""
    generated = []
    post_results = []

    for decision in state["content_decisions"]:
        # Generate text content using Sonnet
        content = await self.generate_text_content(decision)
        generated.append(content)

        # Phase 1: Save for human review (don't auto-post yet)
        await self.save_for_review(content)

        # Phase 2+: Auto-post via Late API or MCP
        # result = await self.publish(content)
        # post_results.append(result)

    return {
        "generated_content": generated,
        "post_results": post_results,
    }

async def generate_text_content(self, decision: dict) -> dict:
    """Generate platform-specific text content using Sonnet."""
    platform_templates = load_knowledge("content-formats")

    response = await self.claude.create_cached_message(
        task_type="content_generation",  # Routes to Sonnet
        system_prompt=CONTENT_GEN_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Create {decision['content_type']} content.
Product: {decision['product']}
Platform: {decision['platform']}
Topic: {decision['topic']}
Reasoning: {decision['reasoning']}
""",
        }],
    )

    return {
        "decision": decision,
        "text": response.content[0].text,
        "platform": decision["platform"],
        "status": "pending_review",
    }
```

Acceptance Criteria:
- [ ] Text content generated using Sonnet for each decision
- [ ] Content respects platform character limits
- [ ] Phase 1: Content saved to `data/content-queue/` for human review
- [ ] Phase 2+: Content published via Late API or social-media MCP
- [ ] Generated content includes platform-specific formatting
- [ ] Each piece logged with decision context

---

**SPEC-005: Evaluate Stage**

| Field | Value |
|-------|-------|
| Description | Logs what was done, updates memory with any insights |
| Trigger | After act stage completes |
| Input | All state (decisions, generated content, results) |
| Output | Trajectory entry, optional MEMORY.md update |
| Validation | Trajectory entry must be valid JSON |
| Auth Required | No |

```python
async def evaluate(self, state: MarketingState) -> dict:
    """Log decisions and update memory."""
    from holus.memory.trajectory import TrajectoryLogger

    tl = TrajectoryLogger()

    for content in state["generated_content"]:
        tl.append({
            "agent_id": self.AGENT_NAME,
            "task_type": "content_creation",
            "task_summary": f"{content['decision']['content_type']} about "
                           f"{content['decision']['topic']} for {content['decision']['platform']}",
            "status": content.get("status", "success"),
            "metadata": {
                "product": content["decision"]["product"],
                "platform": content["decision"]["platform"],
                "content_type": content["decision"]["content_type"],
                "reasoning": content["decision"]["reasoning"],
                "strategy_context": state["strategy_reasoning"],
            },
        })

    return {"evaluation": {"logged": True, "pieces_created": len(state["generated_content"])}}
```

Acceptance Criteria:
- [ ] Every content decision logged to trajectory.jsonl
- [ ] Metadata includes product, platform, content_type, and reasoning
- [ ] Failed generations logged with error details
- [ ] MEMORY.md updated when significant patterns emerge (Phase 2+)

---

### Data Structures

```python
# src/holus/agents/marketing/models.py

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ContentDecision(BaseModel):
    product: str
    platform: str
    content_type: str
    topic: str
    reasoning: str
    priority: int = 1
    estimated_engagement: str = "medium"


class GeneratedPiece(BaseModel):
    piece_id: str
    decision: ContentDecision
    text: str
    platform: str
    generated_at: datetime
    model_used: str
    status: str  # "pending_review" | "approved" | "published" | "rejected"
    post_url: str | None = None


class MarketingCycleReport(BaseModel):
    cycle_id: str
    started_at: datetime
    completed_at: datetime
    decisions_made: int
    pieces_generated: int
    pieces_published: int
    products_covered: list[str]
    platforms_used: list[str]
    total_cost_usd: float
```

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/agents/marketing/__init__.py` | New | Module init |
| `src/holus/agents/marketing/agent.py` | New | MarketingAgent with ReAct loop |
| `src/holus/agents/marketing/models.py` | New | Pydantic models for decisions and content |
| `src/holus/agents/marketing/prompts.py` | New | System prompts for strategy and content generation |
| `src/holus/agents/marketing/run.py` | New | CLI entrypoint for running the agent |
| `config/marketing_agent.yaml` | New | Marketing agent configuration |
| `data/content-queue/` | New (gitignored) | Content pieces awaiting human review |
| `tests/unit/agents/test_marketing.py` | New | Unit tests for the marketing agent |
| `justfile` | Modified | Add `run-marketing` command |

---

### Edge Cases & Error Handling

**EDGE-001: No analytics available (cold start)**
- Scenario: First run, no social media analytics exist
- Expected behavior: Agent uses knowledge base and product definitions to make initial decisions. Strategy defaults to "tutorial content for the most visual product (Pilaster) on LinkedIn."
- Recovery: Analytics become available once content is posted and tracked.

**EDGE-002: Claude API rate limited during content generation**
- Scenario: Anthropic returns 429 during act stage
- Expected behavior: Agent retries with exponential backoff (SDK handles this). If persistent, skips the piece and logs the failure.
- Recovery: Next cycle retries the content type.

**EDGE-003: Content decision is for a product with no recent updates**
- Scenario: Opus decides to create content for invoz, but invoz hasn't shipped anything new
- Expected behavior: Agent creates evergreen content (tips, tutorials, educational) rather than product announcements.
- Recovery: Automatic — system prompts guide towards evergreen content when no news exists.

**EDGE-004: Generated content is too long for platform**
- Scenario: LinkedIn post exceeds 3,000 characters
- Expected behavior: Auto-truncate and regenerate with explicit length constraint. If still too long, truncate with "..." and post.
- Recovery: Automatic.

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Full cycle time | < 5 min | trajectory.jsonl duration |
| Observe stage | < 10s | Stage timing |
| Reason stage (Opus) | < 30s | Claude API latency |
| Content generation (Sonnet) | < 15s per piece | Claude API latency |
| Cost per cycle | < $0.50 | Langfuse cost tracking |
| Cost per day (48 cycles) | < $10 | Aggregated |

---

### Security Considerations

- Content never contains financial advice (hard rule in system prompt)
- Content never exposes internal metrics or revenue numbers
- Human approval required before posting in Phase 1
- Kill switch stops all content creation immediately

---

### Out of Scope

- Image generation (handled by spec 003, SPEC-002)
- Video generation (handled by spec 003, SPEC-003)
- Distribution via Late API (handled by spec 011)
- Analytics collection (handled by spec 011)
- Self-improvement / prompt optimization (handled by spec 012)

---

### Related Specs

- [009-autonomous-build-system.md](./009-autonomous-build-system.md) — the builder will implement this agent
- [011-social-media-integration.md](./011-social-media-integration.md) — provides the posting and analytics APIs
- [012-knowledge-learning.md](./012-knowledge-learning.md) — the knowledge system the agent reads from
- [003-content-pipeline.md](./003-content-pipeline.md) — the full content pipeline (Phase 2+)

---

**Last Updated:** 2026-02-26
**Status:** Not Started
**Owner:** Camilo Martinez
