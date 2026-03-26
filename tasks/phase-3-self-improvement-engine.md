# Phase 3: Self-Improvement Engine (Hours 400-700, ~$45 API)

**Goal:** System quality improves measurably without human intervention.
The system proposes content, generates, evaluates, and improves its own
prompts. Human approval only at the publish gate.

**Deliverable:** Autonomous content proposal + generation + evaluation +
prompt improvement. Measurable quality improvement over 4+ weekly cycles.

**Entry criteria:** Phase 2 complete — 100+ published pieces, 100+ observations
in bandit, multimodal visual evaluation working, judge calibrated.

---

## Task 27: Wire Analytics to Bandit Rewards

**Hours:** 25 | **Type:** CODE | **Priority:** P0 | **Dependencies:** Phase 2

**What:** The `analytics_cycle()` in orchestrator.py collects engagement data
but never updates the bandit with real rewards. Wire the connection.

**Files to modify:**
- `src/holus/agents/marketing/orchestrator.py` — add `_feed_bandit()` at end of analytics_cycle
- `src/holus/agents/marketing/strategy_bandit.py` — add `update_from_analytics()` method

**Reward calculation (from BlogBurst research):**
```python
engagement_score = (
    likes * 1.0 +
    comments * 3.0 +
    reposts * 5.0 +
    saves * 10.0
) / impressions

# Adaptive threshold: rolling 30-day average
threshold = rolling_avg_engagement(days=30)
success = engagement_score > threshold
```

A post is "successful" when its score exceeds the rolling 30-day average.
This auto-adjusts as content quality improves.

**Bandit arm structure:**
Currently: `product:content_type:platform`
Add: `product:content_type:platform:visual_style`
This lets the bandit learn which visual treatments work on which platforms.

**Acceptance criteria:**
- [ ] analytics_cycle() updates bandit with real engagement rewards
- [ ] Reward uses weighted engagement formula (saves > reposts > comments > likes)
- [ ] Adaptive threshold (rolling 30-day average)
- [ ] Bandit arms include visual_style dimension
- [ ] `just arms` shows real performance data

---

## Task 28: Activate DSPy BootstrapFewShot

**Hours:** 20 | **Type:** ML | **Priority:** P1 | **Dependencies:** Phase 2

**What:** The DSPy bridge exists but isn't connected. Add DSPy to dependencies,
wire BootstrapFewShot for automatic few-shot example selection.

**Files to modify:**
- `pyproject.toml` — add `dspy-ai` to optional dependencies
- `src/holus/self_improvement/dspy_optimizer.py` — fix `bootstrap_few_shot()` to actually
  inject results into prompts
- `src/holus/self_improvement/dspy_bridge.py` — connect output to PromptLoader

**Pipeline:**
1. Bridge reads trajectory entries with judge_score >= 0.75
2. Selects k=5 diverse examples (one per content_type/platform combo)
3. BootstrapFewShot optimizes example selection against a quality metric
4. Optimized examples written to `config/prompts/{agent_id}/few_shot.md`
5. PromptLoader Layer 1 picks up the few-shot file

**Activation gate:** 100 trajectory entries (lowered from 500 in Phase 1).

**Cost:** ~$0.60-$1.20 per optimization run. Run monthly per agent.

**Acceptance criteria:**
- [ ] DSPy installed and importable
- [ ] BootstrapFewShot runs on trajectory data
- [ ] Optimized examples written to config/prompts/
- [ ] PromptLoader loads the few-shot examples
- [ ] Generator prompts include DSPy-selected examples
- [ ] Quality metric defined and working

---

## Task 29: Activate Genetic Prompt Evolution

**Hours:** 10 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Phase 1 Task 2

**What:** The genetic evolution system is fully built but never activated.
With the gate lowered to 100 and 100+ observations available, verify it works.

**Files to verify:**
- `src/holus/self_improvement/prompt_evolution.py` — evolve() method
- `src/holus/agents/marketing/orchestrator.py` — improvement_cycle() evolution call

**Test procedure:**
1. Run `just improve-cycle`
2. Verify evolution triggers (gate should be met)
3. Check `config/prompts/{agent_id}/population.json` — should show 2-3 variants
4. Verify variants are meaningfully different (not just whitespace changes)
5. Run A/B test: generate 5 pieces with variant A, 5 with variant B
6. Compare judge scores

**Acceptance criteria:**
- [ ] Evolution runs and produces 2-3 prompt variants
- [ ] Variants are meaningfully different
- [ ] A/B test shows measurable score difference
- [ ] Best variant auto-promoted after 10+ observations
- [ ] Rollback works if new variant performs worse

---

## Task 30: Build MIPROv2 Integration

**Hours:** 40 | **Type:** ML | **Priority:** P2 | **Dependencies:** Task 28

**What:** Replace the DSPy optimizer stub with full MIPROv2. MIPROv2 co-optimizes
instructions AND examples (BootstrapFewShot only optimizes examples).

**Files to modify:**
- `src/holus/self_improvement/dspy_optimizer.py` — implement `mipro_optimize()`

**How MIPROv2 works:**
1. Bootstraps demonstrations from trajectory data
2. Proposes candidate instructions grounded in dataset properties
3. Uses Bayesian optimization to find best instruction+example combo
4. Requires 50-100 LLM calls per optimization run

**Cost:** $3-$6 per run on Sonnet. Run monthly.

**Gate:** Only optimize agents with 50+ evaluated pieces.

**Acceptance criteria:**
- [ ] MIPROv2 runs and produces optimized prompts
- [ ] Optimized prompts score higher than baseline on held-out test set
- [ ] Results written to config/prompts/{agent_id}/versions/
- [ ] Rollback if optimized version performs worse
- [ ] Cost tracking per optimization run

---

## Task 31: Full Diagnostician with Code Reading

**Hours:** 40 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Phase 1

**What:** Upgrade the diagnostician to use Opus for reading actual code files
and tracing failures to specific lines/sections.

**Files to modify:**
- `src/holus/self_improvement/diagnostician.py` — add `_code_reading_diagnostic()`

**Currently:** Diagnostician detects patterns from trajectory data (statistical).
**New:** Diagnostician reads source files and agent prompts to trace WHY a
dimension consistently fails.

**Example:**
```
Pattern detected: hook_strength < 0.6 on 70% of pieces
→ Read agents/specialists/idea-generator.md
→ Find: "Generate content for {platform}" — no mention of hooks
→ Task: "idea-generator.md line 15 doesn't mention hook quality.
   Add: 'The first 1-2 lines must create a specific curiosity gap.
   Use a number, a failure, or a counterintuitive claim.'"
```

**Implementation:**
- When a dimension fails systemically (3+ times), read the responsible agent prompt
- Use Opus to analyze: "Given this prompt and this feedback pattern, what's missing?"
- Generate a specific prompt edit suggestion with before/after
- Cost: ~$0.10 per code-reading diagnostic (Opus, 2K tokens)

**Acceptance criteria:**
- [ ] Diagnostician reads source files when tracing failures
- [ ] Suggestions include specific file:line references
- [ ] Suggestions include before/after prompt edit proposals
- [ ] Cost per diagnostic run < $0.50

---

## Task 32: Analytics-Driven Content Calendar

**Hours:** 35 | **Type:** CODE | **Priority:** P2 | **Dependencies:** Task 27

**What:** Instead of human-triggered content, the system proposes a weekly
content plan based on: what performed best (bandit), trending topics (reference
library), and recency (what hasn't been covered recently).

**File to create:**
- `src/holus/agents/marketing/content_calendar.py`

**Calendar algorithm:**
1. Query bandit for top-performing arms (content_type × platform × visual_style)
2. Query corpus for trending topics (frequency in last 30 days vs prior 30)
3. Query trajectory for recently covered topics (recency penalty)
4. Query brand.yaml for content pillar cadence (builder_stories 2x/week, etc.)
5. Generate weekly plan: 5 LinkedIn posts + repurposed versions

**Output:** `data/content-calendar/YYYY-WNN.yaml`
```yaml
week: 2026-W14
generated_at: 2026-03-26T14:00:00Z
plan:
  - day: monday
    content_type: builder_story
    platform: linkedin
    visual_style: text_post
    topic_seed: "genpeli silence detection threshold tuning"
    reasoning: "builder_stories due for rotation, genpeli hasn't been covered in 10 days"
  - day: wednesday
    content_type: tutorial
    platform: linkedin
    visual_style: carousel
    topic_seed: "MCP vs REST for agent tool communication"
    reasoning: "tutorials get 2.3x avg engagement, carousel visual style winning"
```

**Justfile command:** `just content calendar-propose`

**Acceptance criteria:**
- [ ] Calendar proposes 5 posts/week based on real data
- [ ] Bandit arms influence content type/visual style selection
- [ ] Recency penalty prevents topic repetition
- [ ] Calendar respects pillar cadence from brand.yaml
- [ ] `just content calendar-propose` generates next week's plan

---

## Task 33: Visual Style Replication

**Hours:** 40 | **Type:** ML | **Priority:** P2 | **Dependencies:** Tasks 20, 23

**What:** Given a creator name and visual type, generate carousels "in the style of"
that creator using few-shot prompting with their top 5 images as reference.

**File to create:**
- `src/holus/visual/style_replicator.py`

**Pipeline:**
1. Query corpus: top 5 images by `creator + visual_type`
2. Load image sidecar JSONs (layout description, color scheme, text placement)
3. Build style prompt: "Create a carousel in the style of {creator}. Their
   top carousels use: {layout patterns}, {color schemes}, {text density}."
4. Inject style prompt into carousel spec generation
5. Render with Playwright
6. Evaluate with multimodal judge, comparing against reference images

**Acceptance criteria:**
- [ ] Can generate "in the style of Santiago Valdarrama" carousel
- [ ] Style prompt grounded in real reference data, not hallucinated
- [ ] Generated carousel matches reference style on visual_hierarchy dimension
- [ ] Works for at least 5 different creator styles

---

## Task 34: Carousel Layout Planner Agent

**Hours:** 30 | **Type:** CODE | **Priority:** P2 | **Dependencies:** Task 23

**What:** Add a layout planner agent between the format planner and content
generator. The layout planner receives the topic + top 5 performing carousel
layouts from the reference library and outputs a slide-by-slide layout plan.

**File to create:**
- `src/holus/agents/marketing/layout_planner.py`
- `agents/specialists/carousel-layout-planner.md` — agent prompt

**Pipeline change:**
```
Before: topic → format_planner → content_generator → carousel_builder
After:  topic → format_planner → layout_planner → content_generator → carousel_builder
```

**Layout planner output:**
```json
{
  "slide_count": 8,
  "template": "step_by_step_tutorial",
  "slides": [
    {"type": "hook", "layout": "big_number_centered", "max_words": 10},
    {"type": "context", "layout": "text_left_diagram_right", "max_words": 30},
    {"type": "step", "layout": "numbered_with_code", "max_words": 40}
  ],
  "style_reference": "santiago_valdarrama",
  "color_scheme": "dark_navy_gold"
}
```

**Acceptance criteria:**
- [ ] Layout planner produces slide-by-slide plans
- [ ] Plans reference real templates from the template library
- [ ] Plans grounded in few-shot examples from corpus
- [ ] Generated carousels follow the layout plan
- [ ] Quality improvement: carousels with layout planning score higher on visual_hierarchy

---

## Task 35: Spearman Correlation Calibration

**Hours:** 10 | **Type:** ANALYSIS | **Priority:** P1 | **Dependencies:** Task 27

**What:** At 100 paired observations (judge score + engagement data), compute
Spearman rank correlation to verify judges predict real-world performance.

**File to create:**
- `src/holus/self_improvement/calibration.py`

**Protocol:**
1. Load all pieces with both judge_score and engagement_score from trajectory
2. Compute Spearman's rho (rank correlation)
3. Decision table:
   - rho > 0.3: judges calibrated, maintain 0.3 judge / 0.7 engagement blend
   - rho 0.15-0.3: weak correlation, increase engagement weight to 0.1/0.9
   - rho < 0.15: judges miscalibrated, rebuild rubric from top-10 and bottom-10 posts
   - rho < 0: judges anti-correlated (!), freeze and rebuild

**Justfile command:** `just improve calibrate`

**Acceptance criteria:**
- [ ] Correlation computed at 100+ paired observations
- [ ] Decision table applied automatically
- [ ] Results logged to trajectory
- [ ] Blend weights adjusted based on correlation

---

## Task 36: Reach 500 Observations + Full Optimization Cycle

**Hours:** 50 | **Type:** CONTENT | **Priority:** P1 | **Dependencies:** All above

**What:** Generate enough content to reach 500 trajectory observations, then
run the first full optimization cycle with all systems active.

**Process:**
- Continue generating 5 pieces/day
- Publish approved content via social-media MCP
- Collect analytics every 72 hours
- Run improvement_cycle weekly

**At 500 observations:**
1. Genetic evolution activates for real (not just gate check)
2. DSPy MIPROv2 can run with sufficient data
3. Bandit has converged on winning arms
4. Calibration has been validated

**Acceptance criteria:**
- [ ] 500+ trajectory entries
- [ ] Genetic evolution has produced 2+ generations of prompt variants
- [ ] At least 1 prompt variant promoted (scored higher than baseline)
- [ ] Bandit arms show clear winners (95% CI doesn't overlap)
- [ ] Content quality measurably improved (avg score Phase 3 > Phase 2)
