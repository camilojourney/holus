# Spec 017: Authority Engine Agent Update

**Status:** Implemented
**Phase:** Sprint 2
**Author:** Builder Agent (cycle 30)
**Created:** 2026-03-01
**Updated:** 2026-03-02

## Problem

The marketing agent (Spec 010) was built to promote products. The strategy has shifted:
Holus is now an **authority-building engine** that positions Camilo as an AI consulting
expert. The agent code still uses product-promotion framing — prompts say "promote the
products", decisions focus on product rotation, and content is generated one piece at a
time per platform with no repurposing.

Specific gaps:
1. `config/brand.yaml` exists but the agent never loads it — so content has no identity anchor
2. Niche research (SPEC-006 in Spec 010) is designed but not implemented — the agent creates
   content in a vacuum without checking what's trending
3. The Opus strategy prompt (reason stage) frames decisions as "what to promote" instead of
   "what builds authority" — producing generic product content instead of consulting-grade thought leadership
4. Each content piece targets one platform — there's no repurposing pipeline
   (LinkedIn post → Twitter condensed → Instagram visual → Threads conversational → Facebook bilingual)

## Goals

- Agent loads brand identity from `config/brand.yaml` every cycle and uses it in all prompts
- Agent performs niche research during observe (web search for trending AI consulting content)
- Reason stage uses authority-building framing: content pillars, consulting signals, builder voice
- Act stage creates one LinkedIn-first post, then automatically repurposes for 4 secondary platforms
- All changes are backward-compatible: fallback paths work when brand.yaml missing or web search unavailable
- Existing 247+ tests continue passing; new tests cover all new code paths

## Non-Goals

- Auto-publishing (still Phase 1 — human approval required)
- Image/video generation in repurposing (text-only repurposing for now)
- Carousel generation (future spec)
- MCP server changes (social-media, genpeli, pilaster MCPs unchanged)
- Bilingual content generation (Facebook Spanish is future — just mark it in the repurposing output)

## Solution

Four focused changes to the existing marketing agent, each independently implementable:

```
SPEC-001: Brand Config Loader     (observe stage)
SPEC-002: Niche Research Step     (observe stage — implements Spec 010 SPEC-006)
SPEC-003: Authority Prompts       (reason + act stage prompts)
SPEC-004: Content Repurposing     (act stage — new module)
```

The agent's 4-stage LangGraph architecture (observe → reason → act → evaluate) stays the same.
No new graph nodes. Changes happen within existing stages.

```
observe
  ├── load products.yaml              (existing, unchanged)
  ├── load knowledge base             (existing, unchanged)
  ├── load MEMORY.md                  (existing, unchanged)
  ├── load brand.yaml  ← NEW         (SPEC-001)
  └── niche research   ← NEW         (SPEC-002)

reason
  └── authority-framing prompts ← REWRITTEN  (SPEC-003)

act
  ├── generate LinkedIn post          (existing, prompt updated by SPEC-003)
  └── repurpose to 4 platforms ← NEW (SPEC-004)

evaluate
  └── log all pieces                  (existing, unchanged — handles more pieces automatically)
```

---

## Implementation Notes

### SPEC-001: Brand Config Loader

| Field | Value |
|-------|-------|
| Description | Load and validate `config/brand.yaml` during observe, inject into state |
| Trigger | Every marketing cycle, as part of observe |
| Input | `config/brand.yaml` file |
| Output | `brand_identity` dict in MarketingState |
| Validation | Pydantic model validates required sections; graceful fallback if missing |
| Auth Required | None |

#### Pydantic Model

```python
# src/holus/core/config.py (or src/holus/agents/marketing/models.py)

class BrandVoice(BaseModel):
    """Voice configuration from brand.yaml."""
    archetype: str = ""
    summary: str = ""
    tone: list[str] = Field(default_factory=list)

class BrandPositioning(BaseModel):
    """Positioning from brand.yaml."""
    one_liner: str = ""
    category: str = ""
    differentiation: list[str] = Field(default_factory=list)

class ProductProof(BaseModel):
    """Product-as-proof from brand.yaml."""
    proof_narrative: str = ""
    consulting_angle: str = ""
    key_stories: list[str] = Field(default_factory=list)

class ContentPillar(BaseModel):
    """Content pillar from brand.yaml."""
    id: str
    name: str
    description: str
    frequency: str = ""
    products: list[str] = Field(default_factory=list)
    goal: str = ""

class BrandIdentity(BaseModel):
    """Full brand identity loaded from config/brand.yaml."""
    story: dict[str, Any] = Field(default_factory=dict)
    positioning: BrandPositioning = Field(default_factory=BrandPositioning)
    voice: BrandVoice = Field(default_factory=BrandVoice)
    products_as_proof: dict[str, Any] = Field(default_factory=dict)
    content_pillars: list[ContentPillar] = Field(default_factory=list)
    anti_patterns: dict[str, list[str]] = Field(default_factory=dict)
    platform_strategy: dict[str, Any] = Field(default_factory=dict)
    target_client: dict[str, Any] = Field(default_factory=dict)
    offer: dict[str, Any] = Field(default_factory=dict)
```

#### Agent Changes

```python
# agent.py — new class attribute
_BRAND_PATH = Path("config/brand.yaml")

# agent.py — observe method update
async def observe(self, state: MarketingState) -> dict[str, Any]:
    self.check_kill_switch()
    products = self._read_yaml(self._PRODUCTS_PATH)
    knowledge = self._read_knowledge_files(self._KNOWLEDGE_DIR)
    memory_context = self._read_text(self._MEMORY_PATH)

    # NEW: Load brand identity
    brand_identity = self._load_brand_identity()

    return {
        "product_updates": products,
        "knowledge": knowledge,
        "memory_context": memory_context,
        "analytics": state.get("analytics", {}),
        "queue_size_before": len(self._queue_files()),
        "brand_identity": brand_identity,  # NEW
    }

def _load_brand_identity(self) -> dict[str, Any]:
    """Load and validate config/brand.yaml."""
    raw = self._read_yaml(self._BRAND_PATH)
    if not raw:
        logger.warning("brand.yaml not found or empty; using empty brand identity")
        return {}
    try:
        brand = BrandIdentity(**raw)
        return brand.model_dump(mode="json")
    except ValidationError:
        logger.warning("brand.yaml validation failed; using raw dict")
        return raw
```

#### State Change

```python
class MarketingState(TypedDict):
    # ... existing fields ...
    brand_identity: dict[str, Any]  # NEW — from config/brand.yaml
```

#### File Locations

| File | Change | Description |
|------|--------|-------------|
| `src/holus/agents/marketing/models.py` | Modified | Add `BrandIdentity` and sub-models |
| `src/holus/agents/marketing/agent.py` | Modified | Add `_BRAND_PATH`, `_load_brand_identity()`, update `observe()`, update `default_state()` |
| `tests/unit/agents/test_marketing.py` | Modified | Tests for brand loading, missing file, invalid YAML |

---

### SPEC-002: Niche Research Step

| Field | Value |
|-------|-------|
| Description | Web search sub-step in observe that finds trending AI consulting content |
| Trigger | Every marketing cycle, after loading brand + knowledge |
| Input | Queries from `niche-research-queries.md`, rotation state from `data/.niche-research-state.json` |
| Output | `niche_research` dict in MarketingState |
| Validation | Max 5 queries per cycle, 30-second total timeout, graceful degradation |
| Auth Required | `ANTHROPIC_API_KEY` (Claude API with `web_search_20250305` tool) |

This implements the design from Spec 010 SPEC-006. The design is already written there —
this spec only adds implementation details not covered by SPEC-006.

#### Models

```python
# src/holus/agents/marketing/models.py

class NicheInsight(BaseModel):
    """A single insight extracted from niche research."""
    source_url: str = ""
    source_title: str = ""
    category: str  # competitor_content | trending_topic | viral_pattern | industry_news
    hook: str | None = None
    topic: str
    format: str = "text"  # text | carousel | video | document | image
    engagement_signals: str = ""
    why_it_works: str = ""
    relevance_to_camilo: str = ""
    pillar_fit: list[str] = Field(default_factory=list)
    extracted_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class NicheResearchResult(BaseModel):
    """Complete niche research output for one cycle."""
    queries_run: list[str] = Field(default_factory=list)
    insights: list[NicheInsight] = Field(default_factory=list)
    trending_topics: list[str] = Field(default_factory=list)
    recommended_angles: list[str] = Field(default_factory=list)
    research_duration_ms: int = 0
```

#### Query Selection Algorithm

```python
def _select_queries(self, query_config: dict, max_queries: int = 5) -> list[str]:
    """Pick queries for this cycle, rotating across categories."""
    state_path = Path("data/.niche-research-state.json")
    state = self._read_json(state_path) if state_path.exists() else {}
    query_history = state.get("query_history", {})
    now = datetime.now(UTC)

    # Sort categories by staleness (least recently used first)
    categories = list(query_config.get("queries", {}).keys())
    categories.sort(key=lambda c: state.get("category_last_used", {}).get(c, ""))

    selected = []
    for category in categories:
        cat_data = query_config["queries"][category]
        rotation = cat_data.get("rotation", "daily")
        cooldown_hours = 24 if rotation == "daily" else 168  # weekly = 7 days

        for query in cat_data.get("queries", []):
            last_run = query_history.get(query, "")
            if last_run:
                elapsed = (now - datetime.fromisoformat(last_run)).total_seconds() / 3600
                if elapsed < cooldown_hours:
                    continue
            selected.append(query)
            if len(selected) >= max_queries:
                break
        if len(selected) >= max_queries:
            break

    # Update state
    for q in selected:
        query_history[q] = now.isoformat()
    state["query_history"] = query_history
    state["last_run"] = now.isoformat()
    self._write_json(state_path, state)

    return selected
```

#### Web Search via Claude tool_use

```python
async def _web_search(self, query: str) -> list[dict[str, Any]]:
    """Execute a single web search via Claude tool_use."""
    response = self.claude.call(
        cached_prompt=CachedPrompt(
            system_prompt="Search the web and return relevant results as JSON."
        ),
        messages=[{"role": "user", "content": f"Search for: {query}"}],
        tier="operational",  # Sonnet — mechanical task
        max_tokens=2048,
        tools=[{"type": "web_search_20250305"}],
        agent_id=self.agent_name,
    )
    return self._extract_search_results(response)
```

#### Integration with Observe

```python
async def observe(self, state: MarketingState) -> dict[str, Any]:
    # ... existing + brand loading ...

    # Niche research (graceful degradation)
    niche_research = {}
    try:
        niche_research = await self._niche_research()
    except Exception:
        logger.warning("Niche research failed; continuing without it")

    return {
        # ... existing fields ...
        "brand_identity": brand_identity,
        "niche_research": niche_research,
    }
```

#### State Change

```python
class MarketingState(TypedDict):
    # ... existing fields ...
    niche_research: dict[str, Any]  # NEW — from web search
```

#### File Locations

| File | Change | Description |
|------|--------|-------------|
| `src/holus/agents/marketing/models.py` | Modified | Add `NicheInsight`, `NicheResearchResult` |
| `src/holus/agents/marketing/agent.py` | Modified | Add `_niche_research()`, `_select_queries()`, `_web_search()`, `_extract_insights()`, `_parse_research_queries()`, update `observe()` |
| `src/holus/agents/marketing/prompts.py` | Modified | Add `NICHE_EXTRACTION_PROMPT` |
| `data/.niche-research-state.json` | New (gitignored) | Query rotation cache |
| `tests/unit/agents/test_marketing.py` | Modified | Tests for query selection, search fallback, insight extraction |

---

### SPEC-003: Authority Prompts

| Field | Value |
|-------|-------|
| Description | Rewrite strategy + content prompts for authority-building framing |
| Trigger | Used by reason and act stages every cycle |
| Input | Brand identity, knowledge, niche research, analytics |
| Output | Updated `OPUS_STRATEGY_PROMPT` and `SONNET_CONTENT_PROMPT` |
| Validation | Prompts reference brand.yaml, content pillars, voice profile, anti-patterns |
| Auth Required | None (prompt changes only) |

#### New OPUS_STRATEGY_PROMPT

```python
OPUS_STRATEGY_PROMPT = """You are Holus, an AI authority-building engine.

Your mission: Build Camilo's reputation as the go-to AI transition consultant
by creating content that demonstrates builder expertise, targets consulting
prospects, and drives inbound leads.

## Brand Identity

{brand_identity}

## Content Pillars

{content_pillars}

## Target Audience

{audience_knowledge}

## Platform Strategy

{platform_knowledge}

## What's Trending in the Niche Right Now

{niche_research}

Use this to:
- Pick topics that have momentum (trending topics get more initial engagement)
- Use hook patterns that are working right now
- React to industry news before competitors do
- Avoid oversaturated topics

## Content Frameworks That Work

{content_formats}

## Viral Frameworks (Proven Patterns)

{viral_frameworks}

## Lessons Learned So Far

{memory}

## Recent Analytics

{analytics}

---

## Your Task

Decide what LinkedIn post to create this cycle. You are creating ONE authority-building
post for LinkedIn. It will be automatically repurposed to secondary platforms.

Make a decision that:
1. **Maps to a content pillar** — builder_stories, ai_frameworks, industry_analysis, results_proof, or contrarian_takes
2. **Targets consulting prospects** — CTOs, VPs Eng, founders at 50-500 employee companies
3. **Uses a proven framework** — pick from viral frameworks or content frameworks
4. **Sounds like Camilo** — builder-philosopher voice, first person, shows the work
5. **Reacts to what's trending** — if niche research found momentum, ride it

## Decision Rules

1. **Authority over promotion:** Content that positions Camilo as expert > content that promotes products
2. **Pillar rotation:** Follow the weekly cadence (builder_stories 2x, ai_frameworks 1x, industry_analysis 1x, results_proof 0.5x, contrarian_takes 0.5x)
3. **LinkedIn-first:** Optimize for LinkedIn algorithm (dwell time, comments, shares)
4. **Products are proof:** Reference Pilaster/genpeli/invoz as evidence of expertise, not as the pitch
5. **Hook matters most:** First line determines engagement — use a proven hook pattern
6. **Data-informed:** If analytics show what works, do more of that

## Anti-Patterns (NEVER do these)

{anti_patterns}

## Output Format

Return a JSON object (not array) with ONE content decision:

```json
{{
  "product": "pilaster" | "genpeli" | "invoz" | "none",
  "platform": "linkedin",
  "content_type": "tutorial" | "tips" | "case_study" | "thread" | "carousel" | "educational",
  "content_pillar": "builder_stories" | "ai_frameworks" | "industry_analysis" | "results_proof" | "contrarian_takes",
  "topic": "Clear description of what the content is about",
  "hook": "The exact opening line of the post",
  "framework": "Which viral/content framework to use (or 'original')",
  "reasoning": "Why this content, why now, why this pillar",
  "priority": 1,
  "estimated_engagement": "low" | "medium" | "high",
  "repurpose_notes": "Any platform-specific adaptation notes for repurposing"
}}
```

Think like a consulting marketer. Your decision builds Camilo's authority.
"""
```

#### New SONNET_CONTENT_PROMPT

```python
SONNET_CONTENT_PROMPT = """You are writing a LinkedIn post as Camilo, an AI builder-consultant.

## The Post to Write

**Topic:** {topic}
**Content Pillar:** {content_pillar}
**Hook (use this opening):** {hook}
**Framework:** {framework}
**Reasoning:** {reasoning}

## Camilo's Voice

{voice}

## Brand Positioning

{positioning}

## Product Context (use as proof, not as pitch)

{product_info}

## Anti-Patterns (NEVER use these)

{anti_patterns}

## LinkedIn Rules

- Max 3,000 characters
- Short paragraphs (1-3 sentences)
- Use line breaks liberally (LinkedIn rewards dwell time)
- Arrow bullets (→) for lists
- No heavy emoji usage
- End with a question or forward-looking statement
- 3-5 relevant hashtags at the end
- First person always ("I built", "I learned", "I realized")
- Contractions always (don't, won't, that's)
- Ground claims in evidence

## Output

Return ONLY the post text. No preamble, no meta-commentary. Ready to publish.
"""
```

#### Prompt for Repurposing (new)

```python
REPURPOSE_PROMPT = """You are adapting a LinkedIn post for {target_platform}.

## Original LinkedIn Post

{original_text}

## Adaptation Rules for {target_platform}

{platform_rules}

## Voice (maintain across platforms)

{voice}

## Output

Return ONLY the adapted post text. No preamble. Ready to publish.
"""
```

#### Changes to reason()

The reason stage now:
1. Formats brand identity into the prompt (positioning, pillars, voice, anti-patterns)
2. Injects niche research results
3. Injects viral frameworks from knowledge base
4. Returns a single LinkedIn-focused decision (not 1-3 multi-platform decisions)
5. The decision includes `content_pillar`, `hook`, and `framework` fields

#### Changes to ContentDecision model

```python
class ContentDecision(BaseModel):
    product: str = Field(description="Product used as proof (or 'none')")
    platform: Platform = Field(default=Platform.LINKEDIN)
    content_type: ContentType = Field(description="Type of content")
    content_pillar: str = Field(
        default="builder_stories",
        description="Which authority pillar: builder_stories, ai_frameworks, industry_analysis, results_proof, contrarian_takes"
    )
    topic: str = Field(description="What the content is about")
    hook: str = Field(default="", description="Opening line of the post")
    framework: str = Field(default="original", description="Viral/content framework used")
    reasoning: str = Field(description="Why this content, why now")
    priority: int = Field(default=1, ge=1, le=3)
    estimated_engagement: str = Field(default="medium", pattern="^(low|medium|high)$")
    repurpose_notes: str = Field(default="", description="Adaptation notes for repurposing")
```

**Backward compatibility:** New fields have defaults, so existing fallback decisions still work.

#### File Locations

| File | Change | Description |
|------|--------|-------------|
| `src/holus/agents/marketing/prompts.py` | Rewritten | New authority prompts, repurpose prompt |
| `src/holus/agents/marketing/models.py` | Modified | Add `content_pillar`, `hook`, `framework`, `repurpose_notes` to `ContentDecision` |
| `src/holus/agents/marketing/agent.py` | Modified | Update `reason()` to format brand + niche into prompt; update `_generate_text_for_decision()` to use new prompt fields |
| `tests/unit/agents/test_marketing.py` | Modified | Update prompt formatting tests, decision parsing tests |

---

### SPEC-004: Content Repurposing

| Field | Value |
|-------|-------|
| Description | New module that takes a LinkedIn post and adapts it for secondary platforms |
| Trigger | After LinkedIn post is generated in act stage |
| Input | LinkedIn post text, `ContentDecision`, platform rules from knowledge base |
| Output | List of `GeneratedPiece` objects (one per secondary platform) |
| Validation | Each repurposed piece respects platform character limits |
| Auth Required | `ANTHROPIC_API_KEY` (Sonnet for adaptation) |

#### Architecture

```
act stage
  └── for each decision:
        1. Generate LinkedIn post (existing, with new prompt)
        2. Repurpose LinkedIn → Twitter     (condensed, more direct)
        3. Repurpose LinkedIn → Instagram   (visual-friendly caption)
        4. Repurpose LinkedIn → Threads     (conversational version)
        5. Repurpose LinkedIn → Facebook    (mark for bilingual ES, Phase 2)
        6. Queue all 5 pieces for review
```

#### New Module: `repurpose.py`

```python
# src/holus/agents/marketing/repurpose.py

from __future__ import annotations

from holus.agents.marketing.models import ContentDecision, GeneratedPiece, Platform

PLATFORM_RULES: dict[Platform, dict[str, Any]] = {
    Platform.TWITTER: {
        "max_chars": 280,
        "style": "Condensed, punchy. One key insight. No hashtags unless viral.",
        "format": "Single tweet or 3-5 tweet thread for longer content.",
        "adapt": "Extract the core insight. Lead with the hook. Cut all filler.",
    },
    Platform.INSTAGRAM: {
        "max_chars": 2200,
        "style": "Visual-friendly caption. Hook in first line (shows in feed preview).",
        "format": "Shorter paragraphs. Strategic line breaks. 10-15 hashtags at end.",
        "adapt": "Keep the story but shorten. Add a clear CTA. Emojis sparingly.",
    },
    Platform.THREADS: {
        "max_chars": 500,
        "style": "Conversational, informal. Like talking to a friend who works in tech.",
        "format": "Short post or 3-4 part thread. No hashtags.",
        "adapt": "More casual tone. Ask a question. Invite replies.",
    },
    Platform.FACEBOOK: {
        "max_chars": 5000,
        "style": "Similar to LinkedIn but slightly more personal.",
        "format": "Can be longer. Include context for non-tech audience.",
        "adapt": "Keep full content. Mark for bilingual ES translation (Phase 2).",
        "bilingual_note": "TODO: Auto-translate to Spanish in Phase 2.",
    },
}

async def repurpose_content(
    *,
    original_text: str,
    decision: ContentDecision,
    claude_client: Any,
    voice: str,
    agent_id: str,
    cycle_id: str,
    piece_index: int,
) -> list[GeneratedPiece]:
    """Take a LinkedIn post and adapt it for secondary platforms."""
    pieces: list[GeneratedPiece] = []
    targets = [Platform.TWITTER, Platform.INSTAGRAM, Platform.THREADS, Platform.FACEBOOK]

    for target in targets:
        rules = PLATFORM_RULES.get(target, {})
        # ... generate adapted text via Claude Sonnet or fallback ...
        # ... create GeneratedPiece with platform-specific text ...
        pieces.append(piece)

    return pieces
```

#### Fallback

If Claude is unavailable for repurposing:
- **Twitter:** Truncate LinkedIn post to 280 chars with "..."
- **Instagram:** Use LinkedIn text as-is (within 2200 limit)
- **Threads:** Use first paragraph of LinkedIn post
- **Facebook:** Use LinkedIn text as-is

#### Platform Selection

Not every post needs all 5 platforms. The repurposing respects `config/brand.yaml`
platform_strategy cadence:
- LinkedIn: 5x/week (every post)
- Twitter: 3x/week (60% of posts)
- Instagram: 2x/week (40% of posts)
- Threads: 2x/week (40% of posts)
- Facebook: 1x/week (20% of posts, bilingual ES)

The selection is based on a rotating counter tracked in `data/.repurpose-state.json`
(gitignored). This ensures even distribution across the week.

#### Act Stage Update

```python
async def act(self, state: MarketingState) -> dict[str, Any]:
    # ... generate LinkedIn post (existing) ...

    # NEW: Repurpose to secondary platforms
    if generated_text:
        repurposed = await repurpose_content(
            original_text=generated_text,
            decision=decision,
            claude_client=self.claude,
            voice=brand_voice_summary,
            agent_id=self.agent_name,
            cycle_id=state.get("cycle_id", ""),
            piece_index=index,
        )
        for piece in repurposed:
            self._write_queue_item(piece, queue_dir)
            generated_content.append(piece.model_dump(mode="json"))
```

#### File Locations

| File | Change | Description |
|------|--------|-------------|
| `src/holus/agents/marketing/repurpose.py` | New | Content repurposing module |
| `src/holus/agents/marketing/agent.py` | Modified | Call `repurpose_content()` after LinkedIn generation |
| `src/holus/agents/marketing/prompts.py` | Modified | Add `REPURPOSE_PROMPT` |
| `src/holus/agents/marketing/__init__.py` | Modified | Export repurposing functions |
| `data/.repurpose-state.json` | New (gitignored) | Platform rotation counter |
| `tests/unit/agents/test_repurpose.py` | New | Tests for repurposing (fallback, char limits, platform selection) |

---

## Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Max niche research queries per cycle | 5 | Balance freshness vs. API cost |
| Niche research timeout | 30s total | Don't delay the cycle for research |
| Daily query cooldown | 24 hours | Avoid redundant searches |
| Weekly query cooldown | 168 hours | Rotate weekly queries properly |
| LinkedIn post max chars | 3,000 | Platform limit |
| Twitter adaptation max chars | 280 | Platform limit |
| Instagram caption max chars | 2,200 | Platform limit |
| Threads max chars | 500 | Platform limit |
| Facebook max chars | 5,000 | Platform limit |
| Content decisions per cycle | 1 (LinkedIn-first) | Quality > quantity; repurposing creates 4 more |
| Repurpose Sonnet temperature | 0.4 | Consistent voice across platforms |
| Strategy Opus temperature | 0.2 | Focused decisions |

## Dependencies

- **Depends on:** Spec 010 (Marketing Agent) — all changes build on existing agent
- **Depends on:** Spec 012 (Knowledge & Learning) — knowledge files read during observe
- **Depends on:** `config/brand.yaml` — must exist (created in Sprint 2 P0)
- **Depends on:** `agentic/memory/knowledge/current/niche-research-queries.md` — must exist (created in Sprint 2 P2)
- **Related:** Spec 016 (Social Media Integration V2) — posting happens after human approval
- **Blocks:** P4 end-to-end authority engine test

## Alternatives Considered

**A. New graph nodes for repurposing and niche research**
Rejected. Adding nodes changes the graph structure, complicates testing, and breaks
the clean 4-stage pattern. Sub-steps within existing nodes are simpler and keep the
evaluate stage as the single logging point.

**B. Multi-platform decisions from Opus (current behavior)**
Rejected. The strategy shift is LinkedIn-first. Having Opus decide per-platform creates
fragmented content that doesn't build coherent authority. One strong LinkedIn post
repurposed 4 ways > 3 mediocre posts on different platforms.

**C. Separate repurposing agent**
Rejected. Repurposing is mechanical (Sonnet-level) and doesn't need its own agent,
graph, or memory. A single function call per platform is sufficient.

## Edge Cases & Failure Modes

**EDGE-001: brand.yaml missing**
- Observe continues with empty brand_identity dict
- Prompts work but produce generic (non-authority) content
- Logged as warning

**EDGE-002: Niche research returns nothing**
- `niche_research` is empty dict
- Reason stage proceeds with static knowledge only
- This is normal for first runs or when web search is unavailable

**EDGE-003: New ContentDecision fields missing in Opus response**
- `content_pillar`, `hook`, `framework` have defaults
- Parsing gracefully handles missing fields
- Fallback decisions use defaults

**EDGE-004: Repurposing exceeds platform char limit**
- `_enforce_platform_limit()` already exists and truncates
- Applied to all repurposed content

**EDGE-005: Claude unavailable for repurposing**
- Fallback: mechanical truncation/extraction (no API needed)
- Each platform has a fallback rule (see SPEC-004 Fallback section)

**EDGE-006: brand.yaml has TODO sections**
- The current brand.yaml has placeholder TODOs for Camilo's input
- Agent should skip/ignore sections with empty values
- Use the filled sections and log which sections need human input

## Observability

| Metric | Target | How to Measure |
|--------|--------|----------------|
| brand.yaml loaded | true/false per cycle | Log in trajectory metadata |
| Niche research queries run | 3-5 per cycle | trajectory.jsonl |
| Niche insights extracted | 0-10 per cycle | trajectory.jsonl |
| Content pillar distribution | Matches cadence over 5 posts | Aggregate from trajectory |
| Repurposed pieces per cycle | 4-5 (one per secondary platform) | trajectory.jsonl |
| Repurposing cost | < $0.10 per cycle | Langfuse tracking |
| Authority framing compliance | Spot-check in content queue | Human review |

## Rollback Plan

Each SPEC is independently deployable and revertible:
- SPEC-001 (brand loader): Remove `_load_brand_identity()` call from observe. State field ignored.
- SPEC-002 (niche research): Remove `_niche_research()` call from observe. State field ignored.
- SPEC-003 (prompts): Revert prompts.py to previous version. Models still work (new fields have defaults).
- SPEC-004 (repurposing): Remove `repurpose_content()` call from act. Only LinkedIn pieces generated.

## Acceptance Criteria

### SPEC-001: Brand Config Loader
- [x] `BrandIdentity` Pydantic model in models.py validates brand.yaml structure
- [x] `_load_brand_identity()` reads and validates `config/brand.yaml`
- [x] `brand_identity` dict present in MarketingState after observe
- [x] Graceful fallback when brand.yaml is missing (empty dict, warning logged)
- [x] Graceful fallback when brand.yaml has invalid structure
- [x] Tests: brand loaded, missing file, invalid YAML

### SPEC-002: Niche Research Step
- [x] `NicheInsight` and `NicheResearchResult` models in models.py
- [x] `_niche_research()` called from observe stage
- [x] Web search via Claude tool_use with `web_search_20250305`
- [x] Query rotation: max 5 per cycle, respects daily/weekly cooldowns
- [x] Rotation state tracked in `data/.niche-research-state.json`
- [x] Insights extracted with structured Claude prompt
- [x] Deduplication against viral-frameworks.md
- [x] `niche_research` dict flows into reason stage
- [x] Graceful degradation: if research fails, observe continues
- [x] 30-second timeout enforced
- [x] Tests: query selection, rotation, search fallback, extraction

### SPEC-003: Authority Prompts
- [x] `OPUS_STRATEGY_PROMPT` rewritten with authority framing
- [x] Prompt includes brand identity, content pillars, niche research, viral frameworks, anti-patterns
- [x] Decision output is ONE LinkedIn-first post (not 1-3 multi-platform)
- [x] `ContentDecision` has `content_pillar`, `hook`, `framework`, `repurpose_notes` fields
- [x] `SONNET_CONTENT_PROMPT` rewritten with Camilo's voice, anti-patterns, builder framing
- [x] `REPURPOSE_PROMPT` created for platform adaptation
- [x] Reason stage formats all new context into Opus prompt
- [x] Tests: prompt formatting, new field parsing, backward compatibility

### SPEC-004: Content Repurposing
- [x] `repurpose.py` module created with `repurpose_content()` function
- [x] LinkedIn post → Twitter (condensed), Instagram (visual caption), Threads (conversational), Facebook (full)
- [x] Platform-specific adaptation rules applied
- [x] Character limits enforced per platform
- [x] Fallback when Claude unavailable (mechanical truncation)
- [x] Platform rotation respects cadence from brand.yaml
- [x] All repurposed pieces queued for human review
- [x] Evaluate stage logs all pieces (existing code handles this automatically)
- [x] Tests: repurposing per platform, fallback, char limits, rotation

### Integration
- [x] All existing 247+ tests still pass (330 tests passing as of Sprint 2 completion)
- [x] `just check` passes (lint + typecheck + tests)
- [x] Full cycle runs in fallback mode (no API key) without errors
