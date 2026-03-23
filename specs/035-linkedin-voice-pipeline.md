# Spec 035: LinkedIn Voice Pipeline — Phase 1

**Status:** ready
**Phase:** Phase 1
**CID:** holus-SPECS-20260323-d9d3f3a5
**Author:** specs skill (arch + perf + sec deliberation)
**Created:** 2026-03-23
**Extends:** SPEC-031 (LinkedIn Content Pipeline)

---

## Problem

SPEC-031 wired the observe → reason → act loop but the voice writing step is not reliable:
- `prompts.py` has 390 lines of hardcoded prompts — not improvable without code changes
- No sequential specialist pipeline (hook → story → cta → guard)
- No visual diversity — one static visual per post
- No Telegram approval gate — Juan can't pick variants from Telegram
- No 48h performance loop — system doesn't learn from what works

The result: content can be generated but it's not authentic, not diverse, and not improving.

---

## Goals

1. Voice pipeline produces LinkedIn posts that sound like Juan (builder-philosopher, not corporate)
2. Every post generates 2-3 visual variants via multi-armed bandit diversity algorithm
3. Juan approves via Telegram inline buttons — sees ranked variants with scores
4. 48h read-back updates bandit weights — system learns what works
5. All agent prompts loaded from `.md` files via PromptLoader (not hardcoded Python)

---

## Non-Goals

- Instagram, Twitter, Threads (SPEC-036+)
- Researcher auto-mode (manual idea injection only in Phase 1)
- 3-evaluator creator council (1 judge in Phase 1)
- Auto-publishing without approval
- Full prompt decoupling of `prompts.py` (happens in parallel, doesn't block)

---

## Decisions

### DP1: Agent Orchestration

**Chosen:** Single Opus call with all 4 roles (hook-architect, storyteller, cta-strategist, voice-guardian) inline
**Vote:** arch: C | perf: B | sec: B → **B wins (2-1)**
**Rationale:** Single call achieves ~2-3s latency at 1x API cost vs 4-8s at 4x for sequential on Mac mini. Minimizes prompt injection surface by eliminating inter-agent data handoffs.
**Dissent (arch):** Cached sequential would preserve per-specialist eval scores for the self-improvement loop. Mitigated: voice-guardian gate runs as a second pass if score < 70.
**Hypothesis:** Single Opus call with 4 roles inline produces voice-authentic posts with <3s latency.
Confidence: HIGH | Validation: voice-guardian score ≥ 75/100 on first 10 posts | Timeline: 2 weeks | Fallback: split into sequential if quality drops below 70 avg

### DP2: Prompt Decoupling

**Chosen:** New pipeline uses `.md` files via PromptLoader from day 1; `prompts.py` stays as Layer 3 fallback
**Vote:** arch: C | perf: C | sec: A → **C wins (2-1)**
**Rationale:** PromptLoader 3-layer resolution (`.md` > optimized > Python) enables zero-risk parallel migration. New voice pipeline code never touches `prompts.py`.
**Dissent (sec):** `.md` files are plain text in version control. Mitigated: prompts contain no secrets — only instructions. Sensitive config stays in `config/` with gitignore where needed.
**Hypothesis:** New pipeline using `.md` files from day 1 enables prompt improvement without code changes.
Confidence: HIGH | Validation: voice-guardian score improves run-over-run via Layer 1 updates | Timeline: 4 weeks

### DP3: Visual Bandit State

**Chosen:** Dedicated `data/bandit-state.json` file
**Vote:** arch: C | perf: C | sec: A → **C wins (2-1)**
**Rationale:** O(1) load/update, persistent across restarts, isolated from trajectory.jsonl (state vs logs separation). No DB needed.
**Dissent (sec):** In-memory avoids persisting engagement data. Mitigated: bandit.json stores only arm weights + counts — no PII, no post content, no comments.

### DP4: Telegram Approval Gate

**Chosen:** Inline Telegram buttons with `post_id` only in callback data
**Vote:** sec: A (unanimous — only sec evaluated this)
**Rationale:** Callback data never contains post content — only opaque IDs. Prevents content leakage via Telegram callback payloads.

---

## Solution

### Architecture

```
INPUT (Telegram message from Juan)
    ↓
[idea-injector]           reads raw text, extracts content_pillar + product_angle
    ↓
[context-builder]         web search enrichment, data points, anti-pattern check
    ↓
[voice-writer]            SINGLE Opus call, 4 roles inline:
                            1. hook-architect: first 2 lines (contrarian/confession/bold/observation)
                            2. storyteller: body (personal → insight → pattern)
                            3. cta-strategist: closing line
                            4. voice-guardian: review pass (blocks if anti-pattern found)
    ↓
[format-router]           decides: text_only | text_with_visual | carousel
    ↓                     reads: config/content.yaml, brand.yaml
[visual-generator]        2-3 variants via ε-greedy bandit
                            reads: data/bandit-state.json
                            70% exploit top arm, 30% explore new treatment
    ↓
[written-content-judge]   scores post: hook(30%) + voice(25%) + insight(20%) + readability(15%) + cta(10%)
                            ≥80: publish | 60-79: note fixes | <60: rewrite
    ↓
[telegram-approval-gate]  sends post text + ranked variants (A/B/C) with scores
                            inline buttons: ✅A | ✅B | ✅C | ✏️Edit | 🔄Regen | ❌Reject
    ↓
[publisher]               calls social-media-mcp.schedule_post(post_id, chosen_variant)
    ↓
[performance-loop]        48h later: reads analytics, updates bandit-state.json arm weights
                            logs to trajectory.jsonl
```

### New Files

**Agent prompts (loaded via PromptLoader Layer 2):**
- `agents/specialists/content/voice-writer.md` — single Opus prompt with 4 roles inline
- `agents/specialists/content/context-builder.md` — enrichment instructions
- `agents/specialists/content/idea-injector.md` — intake + content_pillar extraction

**Pipeline modules:**
- `src/holus/agents/marketing/voice_pipeline.py` — orchestrates the full flow
- `src/holus/agents/marketing/bandit.py` — ε-greedy multi-armed bandit
- `src/holus/agents/marketing/performance_loop.py` — 48h read-back
- `src/holus/api/routes/telegram_gate.py` — approval gate handler

**State:**
- `data/bandit-state.json` — arm weights + counts + last_updated

### Voice Writer Prompt Structure

Single Opus call. System prompt loads `agents/specialists/content/voice-writer.md` via PromptLoader.

The prompt instructs Opus to produce output in 4 labeled sections:
```
[HOOK]
{2 lines — one of: contrarian | confession | bold_claim | observation}

[BODY]
{4-8 paragraphs, 1-3 sentences each, first person, short, one paradox}

[CTA]
{1 line — direct question or forward-looking statement}

[VOICE_CHECK]
PASS | FAIL: {specific anti-pattern found if FAIL}
```

If `VOICE_CHECK: FAIL` → retry once with the specific anti-pattern as a constraint.
If second attempt also fails → return to user with note.

### Multi-Armed Bandit

Each "arm" = visual treatment combination:
```python
# arm_id = f"{background}_{typography}_{layout}_{extras}"
arms = {
    "dark_gradient__large_headline__centered__none": {"wins": 0, "trials": 0},
    "light_clean__body_heavy__split__icons": {"wins": 0, "trials": 0},
    ...
}
```

**ε-greedy:** ε=0.3 (explore 30%, exploit 70%)
**Win signal:** engagement_rate > median_engagement_rate for the week
**Phase 1 (< 10 posts):** pure exploration — ε=1.0, random sampling
**Phase 2 (10-30 posts):** standard ε=0.3
**Phase 3 (30+ posts):** ε=0.1, heavily exploit

---

## Acceptance Criteria

```
Given a raw idea from Juan via Telegram
When the voice pipeline runs
Then a post is generated with:
  - Hook in first 2 lines (contrarian | confession | bold_claim | observation)
  - Body in 1-3 sentence paragraphs
  - No anti-patterns from brand.yaml
  - voice-guardian PASS

Given a post passes voice-guardian
When visual-generator runs
Then 2-3 visual variants are produced with different treatment combinations

Given variants are produced
When written-content-judge scores them
Then each variant has a score 0-100 with per-dimension breakdown

Given scored variants
When Telegram approval gate fires
Then Juan receives:
  - Post text
  - Ranked variants with scores (highest first)
  - Inline buttons: ✅A | ✅B | ✅C | ✏️Edit | 🔄Regen | ❌Reject

Given Juan approves variant X
When publisher runs
Then social-media-mcp.schedule_post is called with post_id + chosen variant file

Given a post has been live for 48h
When performance-loop runs
Then:
  - Analytics are read from social-media-mcp
  - bandit-state.json arm weights are updated
  - Result logged to trajectory.jsonl
```

---

## Out of Scope

- Researcher auto-mode (Phase 2)
- 3-evaluator creator council (Phase 2)
- Auto-publishing (Phase 2)
- Decoupling prompts.py (parallel work, tracked separately)
- Instagram / Twitter / Threads (SPEC-036+)

---

## Dependencies

- SPEC-031: social-media-mcp connected ✅
- SPEC-017: authority engine agents exist ✅
- PromptLoader: 3-layer resolution working ✅
- Telegram bot: exists and connected ✅
- visual/engine.py: visual generation working ✅
