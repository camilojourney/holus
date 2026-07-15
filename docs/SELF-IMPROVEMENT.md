# How Holus Improves Itself

**Last updated:** 2026-03-26

This document explains how the self-improvement system works — the data flow,
the feedback loops, and how content quality gets better over time.

---

## The Big Picture

```
GENERATE content
     ↓
EVALUATE (7 domain judges + quality gate)
     ↓
DIAGNOSE (System Diagnostician traces failures to code/prompts)
     ↓
LEARN (weekly patterns + bandit rewards + prompt evolution)
     ↓
IMPROVE next generation (feedback injection + few-shot grounding)
     ↓
REPEAT
```

Every cycle, the system:
1. Generates content using the best prompts it has
2. Evaluates content with domain-specific judges
3. Diagnoses what went wrong (if anything)
4. Learns patterns from accumulated data
5. Improves the next cycle using what it learned

---

## Layer 1: Content Generation

**Command:** `just generate`

The marketing agent runs a ReAct loop:

```
OBSERVE → REASON → ACT → EVALUATE
```

**Observe:** Loads brand identity, knowledge files, analytics, niche research,
AND prior judge feedback from the last cycle. Also loads few-shot examples
(top-performing LinkedIn posts from the reference library).

**Reason:** Opus decides what to write — picks product, platform, content type,
pillar, hook, framework. Uses Thompson Sampling bandit to balance exploitation
(repeat what works) vs exploration (try new combos).

**Act:** Sonnet generates the LinkedIn post. Personal context (real anecdotes,
metrics, tool opinions) is injected to make it sound human. Content is
repurposed to Twitter (as numbered thread), Instagram, Threads, Facebook.

**Key files:**
- `src/holus/agents/marketing/agent.py` — the ReAct loop
- `src/holus/agents/marketing/prompts.py` — generation prompts
- `src/holus/agents/marketing/content_generator.py` — calls LLM, injects few-shot + personal context
- `src/holus/agents/marketing/repurpose.py` — LinkedIn → 4 other platforms
- `src/holus/agents/marketing/strategy_bandit.py` — Thompson Sampling

---

## Layer 2: Content Evaluation

**Command:** `just evaluate-content`

Every piece gets TWO evaluation passes:

### Pass 1: Quality Gate (deterministic, $0, instant)

`quality_score.py` starts at 100 and subtracts penalties:

| Check | Penalty | What it catches |
|-------|---------|-----------------|
| Character limits | -30 | Too long for platform |
| AI slop phrases (40+) | -20 each | "delve", "let that sink in", "game-changer", etc. |
| Forbidden topics | -50 | Trading, financial advice |
| Weak hook | -15 | First line < 10 chars |
| Missing pillar | -10 | No content pillar assigned |
| Exclamation density | -10 | Too many ! marks |
| Emoji density | -10 | Too many emojis |
| Readability | -15 | Avg sentence > 25 words (too dense for mobile) |
| Specificity | -20 | Zero numbers AND zero proper nouns (generic) |
| Sentence variance | -15 | Std dev < 4 words (AI-typical uniform length) |
| Short paragraphs | -10 | < 30% single-sentence paragraphs (LinkedIn style) |
| Repetitive openers | -10 | > 50% paragraphs start with I/The/In/It |
| Mechanical rhythm | -10 | 3+ consecutive same-length sentences |

**Threshold:** Score >= 60 passes. Below 60 = auto-rejected.

### Pass 2: Domain Judges (LLM-based, ~$0.004/piece)

7 specialized evaluators, routed by content type:

| Judge | Dimensions | When used |
|-------|-----------|-----------|
| written-content | hook_strength, narrative_arc, voice_fidelity, authority_signal, readability | Text posts, articles |
| visual-content | visual_hierarchy, brand_alignment, info_clarity, scroll_stop_power, slide_pacing | Carousels, infographics |
| video-content | hook_timing, pacing_score, retention_prediction, caption_quality, cta_strength | Video scripts |
| brand-safety | voice_deviation, anti_pattern_count, reputation_risk, forbidden_content | **ALL content** (gate) |
| engagement | conversion_potential, authenticity_score, brand_safety, audience_match, frequency | Text + visual |
| platform-fit | algorithm_signals, format_compliance, native_feel, timing | All platforms |
| seo | keyword_relevance, search_intent, topical_authority, competitive_gap, uniqueness | SEO content |

**Verdicts:**
- **PASS** (score >= 0.8): Ready for humanization + publishing
- **PARTIAL** (0.5-0.8): Needs human review
- **FAIL** (< 0.5): Auto-rejected, triggers learning

**Key files:**
- `src/holus/agents/marketing/quality_score.py` — deterministic gate
- `src/holus/self_improvement/judge.py` — LLM judges + routing
- `agentic/agents/evaluators/*.md` — judge rubric prompts

---

## Layer 3: System Diagnostician

**Command:** `just diagnose`

The diagnostician watches the pipeline from OUTSIDE. It doesn't evaluate
individual content — it evaluates the machine that makes content.

**What it reads:**
- Trajectory data (last 30 days of scores, verdicts, feedback)
- Judge feedback patterns (which dimensions consistently fail?)
- Platform failure rates (Threads failing 75%? Instagram failing 86%?)

**What it produces:**
- P0 tasks: System is broken (e.g., "judges returned null on all pieces")
- P1 tasks: Quality is systematically poor (e.g., "hook_strength < 0.6 on 70%")
- P2 tasks: Improvement opportunities (e.g., "feedback loop not connected")

Tasks are automatically appended to `agentic/memory/NEXT.md`.

**Key files:**
- `src/holus/self_improvement/diagnostician.py`
- `.self-improvement/reports/diagnostic/` — diagnostic reports

---

## Layer 4: Learning Loop

**Command:** `just improve-cycle` (runs weekly via launchd)

The improvement cycle has 5 steps:

### Step 1: Statistical Learning ($0)

`WeeklyLearningLoop` reads trajectory entries from the last 7 days:
- Groups by product × content_type × platform
- Computes success rates, avg scores, engagement signals
- Detects score drift (agents whose avg dropped 0.1+ from peak)
- Updates `agentic/memory/MEMORY.md` with insights

### Step 2: Prompt Evolution ($0.15/cycle)

Genetic algorithm that evolves agent prompts:
- Keeps top 3 variants per agent (elitism)
- Creates mutations (Sonnet rewrites weakest section)
- Creates crossovers (combines best parts of 2 variants)
- Activates at 100+ trajectory observations

### Step 3: System Diagnostic ($0)

Runs the diagnostician (Layer 3) and appends findings to NEXT.md.

### Step 4: Failure Streak Detection ($0)

Checks for 3+ consecutive FAIL/PARTIAL verdicts per agent.
Logs warnings. (Future: auto-triggers prompt optimizer.)

### Step 5: Gap Detection ($0)

Classifies failures into 4 buckets:
- `capability_gap` — missing tool/integration
- `data_gap` — missing knowledge
- `prompt_issue` — instructions wrong/unclear
- `quality_issue` — poor output quality

Writes gap requests to `.self-improvement/capability-requests/` and
`agentic/memory/knowledge/requests/`.

**Key files:**
- `src/holus/agents/marketing/orchestrator.py` — ties all 5 steps together
- `src/holus/self_improvement/learning_loop.py` — statistical patterns
- `src/holus/self_improvement/prompt_evolution.py` — genetic algorithm

---

## Layer 5: Feedback Injection (the closed loop)

This is what connects evaluation BACK to generation:

### Judge Feedback → Next Generation

When the marketing agent runs `observe()`, it loads the last 5 FAIL/PARTIAL
judge feedbacks from `trajectory.jsonl`. These are injected into the
generation prompt as "Lessons from Last Cycle":

```
## Lessons from Last Cycle (do NOT repeat these mistakes)

- [THREADS — PARTIAL] "Critically incomplete — ends with '...'"
  Weak dimensions: completeness=0.40, actionability=0.35

- [TWITTER — PARTIAL] "Incomplete — ends mid-thread with '→...'"
  Weak dimensions: narrative_arc=0.60
```

This means: if the judge says "hooks are weak" on cycle N, the generator
on cycle N+1 sees that feedback and adjusts.

### Few-Shot Examples → Generation

The content generator loads top-3 performing posts from the reference
library (via `data/few-shot-examples/`) that match the current content type.
These are real LinkedIn posts with real engagement data. The generator
sees what good content looks like before writing.

### Personal Context → Authenticity

2-3 real anecdotes/metrics from `data/personal-context.json` are injected
per generation. These are facts only Camilo would know (real bugs, real
metrics, real tool opinions). This makes content verifiably human.

### Bandit → Content Strategy

Thompson Sampling tracks which product × content_type × platform combinations
perform best. Each cycle, the bandit suggests what to create based on
accumulated performance data.

---

## Data Flow Diagram

```
                    ┌─────────────────────────────────┐
                    │     REFERENCE LIBRARY (SSD)      │
                    │  255 posts, 19 creators, SQLite  │
                    └──────────────┬──────────────────┘
                                   │ few-shot examples
                                   ▼
┌──────────────┐    ┌──────────────────────────────┐
│ personal-    │───▶│     CONTENT GENERATOR         │
│ context.json │    │  (Sonnet + few-shot + context)│
└──────────────┘    └──────────────┬───────────────┘
                                   │ generated content
                                   ▼
                    ┌──────────────────────────────┐
                    │      QUALITY GATE ($0)        │
                    │  40+ AI slop phrases          │
                    │  4 structural checks          │
                    │  readability + specificity     │
                    └──────────────┬───────────────┘
                                   │ passes (score >= 60)
                                   ▼
                    ┌──────────────────────────────┐
                    │    DOMAIN JUDGES (~$0.004)    │
                    │  7 specialized evaluators     │
                    │  5 dimensions each            │
                    └──────────────┬───────────────┘
                                   │ scores + feedback
                                   ▼
                    ┌──────────────────────────────┐
                    │     TRAJECTORY.JSONL          │
                    │  Every score, verdict, metric │
                    └───┬──────────┬───────────┬───┘
                        │          │           │
              ┌─────────▼──┐  ┌───▼────┐  ┌───▼──────────┐
              │ LEARNING   │  │ BANDIT │  │ DIAGNOSTICIAN│
              │ LOOP       │  │ update │  │ trace to     │
              │ (weekly)   │  │ rewards│  │ code/prompts │
              └─────┬──────┘  └───┬────┘  └───┬──────────┘
                    │             │            │
                    ▼             ▼            ▼
              ┌──────────────────────────────────────┐
              │    NEXT GENERATION CYCLE              │
              │  - Prior feedback injected            │
              │  - Bandit suggests content type       │
              │  - Evolved prompts (if available)     │
              │  - Diagnostician tasks for human      │
              └──────────────────────────────────────┘
```

---

## Commands

| Command | What it does | When to run |
|---------|-------------|-------------|
| `just generate` | One content cycle (no publishing) | Testing |
| `just evaluate-content` | Run judges on pending content | After generating |
| `just diagnose` | Run system diagnostician | After evaluating |
| `just improve-cycle` | Full improvement cycle | Weekly |
| `just data-reindex` | Rebuild corpus from scraped posts | After scraping |
| `just data-materialize` | Update few-shot examples | After reindexing |
| `just data-stats` | Show corpus statistics | Anytime |

---

## Optimization Methods (activate by data volume)

| Observations | Method | Cost | Status |
|---|---|---|---|
| 0-100 | Just publish, accumulate data | $0 | **Current stage** |
| 100+ | DSPy BootstrapFewShot (example selection) | $0.60-$1.20/run | Gate lowered, ready |
| 100+ | Genetic prompt evolution | $0.15/cycle | Gate lowered, ready |
| 500+ | DSPy MIPROv2 (instruction + example optimization) | $3-$6/run | Stubbed |
| 2000+ | TextGrad (gradient-based prompt refinement) | ~$10/run | Not built |

---

## Key Metrics to Track

1. **Avg judge score per cycle** — should trend upward
2. **FAIL/PARTIAL rate** — should decrease over time
3. **Diagnostician finding count** — should decrease as issues are fixed
4. **Bandit arm convergence** — winning arms should emerge
5. **Content published** — the flywheel needs data to spin
