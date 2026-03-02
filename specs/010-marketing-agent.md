# Spec 010: Marketing Agent

**Status:** implemented
**Phase:** Phase 1
**Author:** Camilo Martinez
**Created:** 2026-02-26
**Updated:** 2026-02-26

## Problem

There is no automated system to promote the product portfolio (Pilaster, genpeli, invoz). Content strategy decisions are made manually, content is created ad-hoc, and there is no feedback loop between what gets posted and what performs well. The founder must handle all marketing decisions, content creation, and scheduling, which does not scale and leaves analytics data unused.

## Goals

- Marketing agent runs a full ReAct loop (observe, reason, act, evaluate) every 30 minutes via cron or manual trigger
- Agent reads social media analytics to inform content decisions (data-driven strategy)
- Agent decides what content to create, for which product, on which platform, with explicit reasoning
- Agent generates platform-specific text content optimized for each platform's format and audience
- Agent logs every decision and outcome to trajectory.jsonl for future learning
- Content quality improves over time as the agent learns from results via MEMORY.md

## Non-Goals

- Image generation -- handled by Pilaster integration (future spec)
- Video generation -- handled by genpeli integration (future spec)
- Social media posting mechanics -- handled by social-media MCP (Spec 016)
- Self-improvement / prompt optimization -- handled by knowledge & learning system (Spec 012)
- Content never contains financial advice or internal metrics -- enforced via system prompt hard rules
- Auto-posting in Phase 1 -- human approval required before publishing; auto-post deferred to Phase 2+

## Solution

The marketing agent is the brain of Holus. It runs as an episodic LangGraph state machine triggered every 30 minutes by cron or manually via `just run-marketing`. The agent executes a four-stage ReAct loop:

1. **Observe** -- Read analytics from social-media MCP, product state from `config/products.yaml`, knowledge from `.self-improvement/knowledge/`, and memory from `.self-improvement/MEMORY.md`
2. **Reason** -- Use Claude Opus to analyze all context and decide what 1-3 content pieces to create this cycle, with explicit reasoning
3. **Act** -- Use Claude Sonnet to generate platform-specific text content. In Phase 1, save to `data/content-queue/` for human review. In Phase 2+, publish via social-media MCP
4. **Evaluate** -- Log all decisions and outcomes to trajectory.jsonl. Update MEMORY.md when significant patterns emerge (Phase 2+)

The agent starts simple (text posts to LinkedIn and Twitter) and gains capabilities over time (images, video, more platforms). Kill switch is checked before every stage. Human approval is required for all publishing in Phase 1.

## Implementation Notes

### SPEC-001: Marketing Agent ReAct Loop

| Field | Value |
|-------|-------|
| Description | LangGraph state machine with 4 stages: observe, reason, act, evaluate |
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

### SPEC-002: Observe Stage

| Field | Value |
|-------|-------|
| Description | Collects all context the agent needs to make decisions |
| Trigger | Start of each marketing cycle |
| Input | Product config, knowledge files, memory, analytics from social-media MCP |
| Output | Populated state with analytics, product_updates, memory_context, knowledge |
| Validation | Must complete within 30 seconds |
| Auth Required | No for local files. Social-media MCP connection for analytics. |

```python
async def observe(self, state: MarketingState) -> dict:
    """Read analytics from social-media MCP, product state, knowledge, and memory."""
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

    # Read analytics from social-media MCP
    analytics = await self.call_mcp("social-media", "get_analytics", days=7)
    top_posts = await self.call_mcp("social-media", "get_top_posts", limit=10)

    return {
        "analytics": {"summary": analytics, "top_posts": top_posts},
        "product_updates": products,
        "memory_context": memory,
        "knowledge": knowledge,
    }
```

### SPEC-003: Reason Stage

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

### SPEC-004: Act Stage

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

        # Phase 2+: Auto-post via social-media MCP
        # result = await self.call_mcp("social-media", "schedule_post",
        #     text=content["text"], platforms=content["platform"])
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

### SPEC-005: Evaluate Stage

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

### Security Notes

- Content never contains financial advice (hard rule in system prompt)
- Content never exposes internal metrics or revenue numbers
- Human approval required before posting in Phase 1
- Kill switch stops all content creation immediately

### Dependencies

- Depends on: [Spec 009](./009-autonomous-build-system.md) — the builder will implement this agent
- Depends on: [Spec 012](./012-knowledge-learning.md) — the knowledge system the agent reads from
- Depended on by: [Spec 016](./016-social-media-integration-v2.md) — posting and analytics via social-media MCP
- Related: [Spec 014](./014-genpeli-integration.md) — video creation via genpeli MCP
- Related: [Spec 015](./015-pilaster-integration.md) — image generation via Pilaster MCP

## Edge Cases & Failure Modes

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
- Recovery: Automatic -- system prompts guide towards evergreen content when no news exists.

**EDGE-004: Generated content is too long for platform**
- Scenario: LinkedIn post exceeds 3,000 characters
- Expected behavior: Auto-truncate and regenerate with explicit length constraint. If still too long, truncate with "..." and post.
- Recovery: Automatic.

## Observability

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Full cycle time | < 5 min | trajectory.jsonl duration |
| Observe stage | < 10s | Stage timing |
| Reason stage (Opus) | < 30s | Claude API latency |
| Content generation (Sonnet) | < 15s per piece | Claude API latency |
| Cost per cycle | < $0.50 | Langfuse cost tracking |
| Cost per day (48 cycles) | < $10 | Aggregated |

## Acceptance Criteria

- [ ] `MarketingAgent` inherits from `BaseAgent` and implements `build_graph()`
- [ ] LangGraph state machine has 4 stages: observe, reason, act, evaluate
- [ ] Kill switch is checked before each stage
- [ ] Agent reads `config/products.yaml` during observe stage
- [ ] Agent reads `.self-improvement/knowledge/` during observe stage
- [ ] Agent reads `.self-improvement/MEMORY.md` during observe stage
- [ ] Agent uses Opus for strategy reasoning (model routing)
- [ ] Agent uses Sonnet for content generation
- [ ] Agent logs every decision to trajectory.jsonl
- [ ] `just run-marketing` triggers the agent manually
- [ ] Products loaded from `config/products.yaml`
- [ ] Knowledge loaded from all files in `.self-improvement/knowledge/current/`
- [ ] Memory loaded from `.self-improvement/MEMORY.md`
- [ ] Observe stage completes within 30 seconds
- [ ] Graceful handling if files are missing
- [ ] Reason stage uses Opus (via `task_type="strategic_planning"`)
- [ ] Prompt includes all context from observe stage
- [ ] Output is a structured list of `ContentDecision` objects
- [ ] Each decision includes reasoning (not just "what" but "why")
- [ ] 1-3 decisions per cycle
- [ ] Text content generated using Sonnet for each decision
- [ ] Content respects platform character limits
- [ ] Phase 1: Content saved to `data/content-queue/` for human review
- [ ] Phase 2+: Content published via social-media MCP
- [ ] Generated content includes platform-specific formatting
- [ ] Each piece logged with decision context
- [ ] Every content decision logged to trajectory.jsonl
- [ ] Metadata includes product, platform, content_type, and reasoning
- [ ] Failed generations logged with error details
- [ ] MEMORY.md updated when significant patterns emerge (Phase 2+)

---

### SPEC-006: Niche Research Step (Observe Sub-Step)

| Field | Value |
|-------|-------|
| Description | Web search sub-step inside observe that finds trending AI consulting content on LinkedIn |
| Trigger | Every marketing cycle, as part of observe (before reason) |
| Input | Curated search queries from `niche-research-queries.md`, previous research from knowledge base |
| Output | `niche_research` dict added to MarketingState: trending topics, competitor hooks, engagement patterns |
| Validation | Must complete within 30 seconds. Max 5 search queries per cycle. |
| Auth Required | `ANTHROPIC_API_KEY` (for Claude tool_use with web_search) |

#### Problem

The marketing agent creates content in a vacuum. It reads the knowledge base (static files
written by humans) but never checks **what's trending right now** in the AI consulting niche.
Top performers in this space study what's working before creating — the agent should too.

Without niche research, the agent:
- Misses trending topics that consulting prospects are engaging with
- Can't detect new viral patterns or formats
- Creates content based on stale frameworks instead of current momentum
- Falls behind competitors who react to industry news in real-time

#### Design

Niche research is a **sub-step of observe**, not a new graph node. This keeps the
4-stage ReAct architecture intact while adding real-time intelligence.

```
observe
  ├── read products.yaml           (existing — SPEC-002)
  ├── read knowledge base          (existing — SPEC-002)
  ├── read MEMORY.md               (existing — SPEC-002)
  ├── read analytics via MCP       (existing — SPEC-002)
  └── niche research (NEW)         ← SPEC-006
        ├── load search queries from niche-research-queries.md
        ├── select 3-5 queries for this cycle (rotate, don't repeat)
        ├── execute web searches via Claude tool_use
        ├── extract: hooks, topics, engagement signals, formats
        ├── deduplicate against viral-frameworks.md (don't re-extract known patterns)
        └── return NicheResearchResult → state["niche_research"]
```

#### Search Query Design

Queries live in `.self-improvement/knowledge/current/niche-research-queries.md` as a
machine-readable YAML block. Categories:

```yaml
queries:
  competitor_content:
    description: "What top AI consultants are posting on LinkedIn"
    queries:
      - "site:linkedin.com AI consulting thought leadership 2026"
      - "site:linkedin.com AI implementation strategy CTO"
      - "site:linkedin.com AI transformation consultant results"
    rotation: weekly  # cycle through, don't repeat same query within a week

  trending_topics:
    description: "What AI topics are getting engagement right now"
    queries:
      - "LinkedIn trending AI enterprise 2026"
      - "AI deployment challenges enterprise this week"
      - "AI consulting demand trends 2026"
    rotation: daily

  viral_patterns:
    description: "High-performing post structures in the niche"
    queries:
      - "site:linkedin.com viral AI post builder story"
      - "LinkedIn AI consultant post went viral"
      - "best LinkedIn posts AI implementation case study"
    rotation: weekly

  industry_news:
    description: "Breaking AI news that consulting prospects care about"
    queries:
      - "enterprise AI news this week"
      - "AI regulation enterprise impact 2026"
      - "AI vendor landscape changes 2026"
    rotation: daily
```

**Query selection per cycle:** Pick 3-5 queries, rotating across categories.
Never run the same query twice in 24 hours. Track last-run timestamps in state
or a lightweight cache file (`data/.niche-research-state.json`).

#### Extraction Patterns

For each search result, Claude extracts structured data:

```python
class NicheInsight(BaseModel):
    """A single insight extracted from niche research."""
    source_url: str
    source_title: str
    category: str  # "competitor_content" | "trending_topic" | "viral_pattern" | "industry_news"
    hook: str | None  # The opening line if it's a post
    topic: str  # What the content is about
    format: str  # "text" | "carousel" | "video" | "document" | "image"
    engagement_signals: str  # Description of engagement (likes, comments, shares if visible)
    why_it_works: str  # Brief analysis of why this content performed
    relevance_to_camilo: str  # How Camilo could create similar content with his angle
    pillar_fit: list[str]  # Which content pillars this maps to
    extracted_at: str  # ISO timestamp

class NicheResearchResult(BaseModel):
    """Complete niche research output for one cycle."""
    queries_run: list[str]
    insights: list[NicheInsight]
    trending_topics: list[str]  # Top 3-5 trending topics distilled from all results
    recommended_angles: list[str]  # Suggested content angles for this cycle
    research_duration_ms: int
```

**Extraction prompt for Claude:**

```
You are analyzing search results about AI consulting content on LinkedIn.

For each relevant result, extract:
1. The hook or opening line (if visible)
2. The topic it covers
3. The format (text post, carousel, video, etc.)
4. Why it likely performed well (engagement psychology)
5. How Camilo (an AI builder-consultant) could create similar content with his unique angle
6. Which content pillar it maps to: builder_stories, ai_frameworks, industry_analysis, results_proof, contrarian_takes

Only extract results that are:
- Relevant to AI consulting/implementation/deployment
- Posted by builders, consultants, or thought leaders (not news aggregators)
- From LinkedIn or about LinkedIn content strategies

Skip: generic AI news, product announcements, academic papers, job postings.

Return structured JSON.
```

#### Integration with Reason Stage

The `niche_research` dict flows into the reason stage alongside existing context.
The Opus strategy prompt gains a new section:

```
## What's Trending in the Niche Right Now

{niche_research}

Use this to:
- Pick topics that have momentum (trending topics get more initial engagement)
- Use hook patterns that are working right now (not just historical patterns)
- React to industry news before competitors do
- Avoid topics that are oversaturated (everyone's posting about it = noise)
```

The reason stage uses niche research as **input signal**, not as a directive.
The agent still makes autonomous strategy decisions — niche research informs,
it doesn't dictate.

#### State Changes

New fields in `MarketingState`:

```python
class MarketingState(TypedDict):
    # ... existing fields ...

    # Niche Research (new — SPEC-006)
    niche_research: dict[str, Any]  # NicheResearchResult as dict
```

#### Implementation Approach

```python
async def _niche_research(self) -> dict[str, Any]:
    """Sub-step of observe: search for trending AI consulting content."""
    import time

    start_ms = int(time.time() * 1000)

    # 1. Load query config
    queries_path = self._KNOWLEDGE_DIR / "niche-research-queries.md"
    query_config = self._parse_research_queries(queries_path)

    # 2. Select queries for this cycle (rotate, deduplicate)
    selected = self._select_queries(query_config, max_queries=5)

    # 3. Execute searches via Claude tool_use with web_search
    raw_results = []
    for query in selected:
        try:
            result = await self._web_search(query)
            raw_results.append({"query": query, "results": result})
        except Exception:
            logger.warning("Niche research query failed: %s", query)

    # 4. Extract insights using Claude
    insights = await self._extract_insights(raw_results)

    # 5. Deduplicate against known frameworks
    known = self._read_text(self._KNOWLEDGE_DIR / "viral-frameworks.md")
    insights = self._deduplicate_insights(insights, known)

    # 6. Distill trending topics and recommended angles
    trending = self._distill_trending(insights)

    duration_ms = int(time.time() * 1000) - start_ms

    return {
        "queries_run": selected,
        "insights": [i.model_dump(mode="json") for i in insights],
        "trending_topics": trending["topics"],
        "recommended_angles": trending["angles"],
        "research_duration_ms": duration_ms,
    }

async def _web_search(self, query: str) -> list[dict[str, Any]]:
    """Execute a single web search via Claude tool_use."""
    response = self.claude.call(
        cached_prompt=CachedPrompt(
            system_prompt="Search the web and return relevant results."
        ),
        messages=[{"role": "user", "content": f"Search for: {query}"}],
        tier="operational",  # Sonnet — mechanical task
        max_tokens=2048,
        tools=[{"type": "web_search_20250305"}],
        agent_id=self.agent_name,
    )
    return self._extract_search_results(response)
```

#### Observe Phase Update

```python
async def observe(self, state: MarketingState) -> dict[str, Any]:
    """Observe phase: load context + niche research."""
    self.check_kill_switch()

    # Existing (SPEC-002)
    products = self._read_yaml(self._PRODUCTS_PATH)
    knowledge = self._read_knowledge_files(self._KNOWLEDGE_DIR)
    memory_context = self._read_text(self._MEMORY_PATH)

    # New (SPEC-006) — niche research
    niche_research = {}
    try:
        niche_research = await self._niche_research()
    except Exception:
        logger.warning("Niche research failed; continuing without it")

    return {
        "product_updates": products,
        "knowledge": knowledge,
        "memory_context": memory_context,
        "analytics": state.get("analytics", {}),
        "queue_size_before": len(self._queue_files()),
        "niche_research": niche_research,
    }
```

#### Failure Modes

**EDGE-005: Web search returns no results**
- Scenario: All queries return empty or irrelevant results
- Expected behavior: `niche_research` is empty dict. Reason stage proceeds with
  existing knowledge base only. Logged as warning.
- Recovery: Automatic — next cycle tries different queries from the rotation.

**EDGE-006: Web search times out**
- Scenario: Claude tool_use web search exceeds 30-second budget
- Expected behavior: Cancel remaining queries. Return partial results.
  Log timeout with queries completed vs. skipped.
- Recovery: Automatic — budget enforced per query (10s each), not total.

**EDGE-007: Extraction finds only known patterns**
- Scenario: All extracted insights duplicate content already in viral-frameworks.md
- Expected behavior: `insights` is empty after dedup. Reason stage gets
  `trending_topics` (which may still be novel) but no new frameworks.
- Recovery: This is fine — it means the knowledge base is current.

**EDGE-008: Search results are spam or off-topic**
- Scenario: Results include AI news aggregators, job postings, or product ads
- Expected behavior: Extraction prompt explicitly filters these out. Only
  builder/consultant/thought-leader content passes the filter.
- Recovery: Automatic — extraction prompt is the filter.

#### Query Rotation Cache

To avoid repeating the same searches, maintain a lightweight state file:

```python
# data/.niche-research-state.json
{
  "last_run": "2026-03-01T10:00:00Z",
  "query_history": {
    "site:linkedin.com AI consulting thought leadership 2026": "2026-03-01T10:00:00Z",
    "LinkedIn trending AI enterprise 2026": "2026-03-01T10:00:00Z"
  },
  "category_last_used": {
    "competitor_content": "2026-03-01",
    "trending_topics": "2026-03-01",
    "viral_patterns": "2026-02-28",
    "industry_news": "2026-03-01"
  }
}
```

This file is gitignored (runtime data). The rotation algorithm:
1. Group queries by category
2. Sort categories by staleness (least recently used first)
3. Pick 1-2 queries from the stalest category
4. Fill remaining slots from `trending_topics` and `industry_news` (always fresh)
5. Never repeat a query within its rotation period (daily or weekly)

#### Acceptance Criteria (SPEC-006)

- [ ] `niche-research-queries.md` created with 4 categories, 3+ queries each
- [ ] `NicheInsight` and `NicheResearchResult` Pydantic models in `models.py`
- [ ] `_niche_research()` sub-step called from observe
- [ ] Web search executed via Claude tool_use with `web_search` tool
- [ ] Max 5 queries per cycle, rotated across categories
- [ ] Results extracted using Claude with structured extraction prompt
- [ ] Deduplication against viral-frameworks.md (don't re-extract known patterns)
- [ ] `niche_research` flows into reason stage prompt
- [ ] Graceful degradation: if research fails, observe continues without it
- [ ] Research completes within 30 seconds (timeout enforced)
- [ ] Query rotation state tracked in `data/.niche-research-state.json`
- [ ] All search queries and results logged in trajectory
- [ ] `trending_topics` and `recommended_angles` extracted from raw results

#### File Locations (SPEC-006)

| File | Change Type | Description |
|------|-------------|-------------|
| `.self-improvement/knowledge/current/niche-research-queries.md` | New | Curated search queries by category |
| `src/holus/agents/marketing/models.py` | Modified | Add `NicheInsight`, `NicheResearchResult` |
| `src/holus/agents/marketing/agent.py` | Modified | Add `_niche_research()`, update `observe()` |
| `src/holus/agents/marketing/prompts.py` | Modified | Add niche research extraction prompt, update Opus strategy prompt |
| `data/.niche-research-state.json` | New (gitignored) | Query rotation cache |
| `tests/unit/agents/test_marketing.py` | Modified | Tests for niche research sub-step |

#### Dependencies

- Requires: Claude API with `web_search` tool support (Anthropic API 2025-03+)
- Requires: `niche-research-queries.md` created (separate task in NEXT.md)
- Blocked by: Nothing — can be implemented independently
- Related: SPEC-002 (Observe Stage), SPEC-003 (Reason Stage)
