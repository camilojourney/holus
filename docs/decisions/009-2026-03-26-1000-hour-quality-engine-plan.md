# Consultation 009: 1000-Hour Quality Engine Plan

**Date:** 2026-03-26 | **Team:** Engineering | **CID:** CONSULT-ENG-20260326-0aee4fb9

## Question

Design a 1000-hour engineering plan to build the best AI content system possible.
Scrape 10K+ LinkedIn posts, learn to create visuals from what performs, sound
genuinely human, self-improve through evaluation cycles, great architecture.

## Critical Finding (all 3 consultants agreed)

> **The system has never self-improved.** 35 agents, 7 evaluators, a diagnostician,
> Thompson Sampling bandits, prompt evolution, DSPy bridge — and none have ever
> modified a prompt or changed content strategy in response to data. The evolution
> gate is at 500 (only 240 entries). The bandit has 0 trials. The diagnostician
> writes reports nobody reads. This is a sophisticated observation machine with
> no actuators.

**The #1 priority is publishing content and closing the feedback loop.**
Everything else (scraping 10K posts, visual tools, optimization) is secondary.

---

## Recommendations

### 1. DATA_PIPELINE
**Chosen:** SQLite-backed 3-layer corpus (raw → index → few-shot)
**Vote:** systems-architect: SQLite 3-layer | ml-engineer: SQLite + Gemini Flash classification | developer-experience: SQLite + wire into pipeline
**Result:** Unanimous (3-0)

**Architecture:**
- **Raw layer:** `/Volumes/SSD/holus/reference-library/{creator}/` — append-only JSONs + images
- **Index layer:** SQLite at `_index/posts.db` — FTS + engagement sorting + visual type filtering
- **Few-shot layer:** `data/few-shot-examples/{visual_type}/top-N.json` — materialized weekly

**Classification cost:** Gemini Flash 2.0 for bulk (10K posts = $1.60), Haiku validation on 10% sample ($1.44). Total: **$3-$9 for entire 10K dataset.**

**Hypothesis:** Few-shot examples from top-performing scraped posts will measurably improve content quality scores by 10%+.
**Validation:** Generate 10 pieces with few-shot injection vs 10 without; compare judge scores.
**Fallback:** If no quality improvement, the corpus is still valuable for rubric calibration.

### 2. VISUAL_GENERATION
**Chosen:** Playwright engine + progressive evaluation gating + template expansion
**Vote:** systems-architect: template evolution + multimodal eval | ml-engineer: progressive cost gates | developer-experience: standalone visual commands
**Result:** Unanimous (3-0)

**Progressive gating (cost per carousel):**
1. Deterministic spec checks ($0) — blocks 30-40% of bad specs
2. Slide-1 only Haiku vision ($0.04-$0.15) — scroll-stop test
3. Full Sonnet vision on PASS candidates only ($1.22 * 25% = $0.30)
4. **Blended cost: ~$0.48/carousel** (vs $1.50 without gating)

**Template expansion:** From 7 → 20+ visual types derived from reference library top-50 carousels.

### 3. SELF_IMPROVEMENT_LOOP
**Chosen:** Wire 4 existing connections in leverage order + phase optimization by data volume
**Vote:** systems-architect: 4 connections in order | ml-engineer: phase by observation count | developer-experience: lower gates + wire diagnostician
**Result:** Unanimous (3-0)

**Wiring order (highest leverage first):**
1. Judge feedback → generator prompts (hours 0-20)
2. Diagnostician → NEXT.md tasks (hours 20-60)
3. Analytics → bandit rewards (hours 60-120)
4. Few-shot grounding from corpus (hours 120-200)

**Optimization phasing by data volume:**
| Observations | Method | Cost/cycle |
|---|---|---|
| 0-100 | Nothing. Just publish. | $0 |
| 100-500 | DSPy BootstrapFewShot (example selection) | $0.60-$1.20 |
| 500-2000 | Genetic evolution (already built) + MIPROv2 monthly | $8.40/month |
| 2000+ | TextGrad if genetic plateaus | ~$10/run |

**Immediate action:** Upgrade bandit from epsilon-greedy to Thompson Sampling (15 lines of code). Lower evolution gate from 500 → 100.

### 4. HUMANIZATION_ARCHITECTURE
**Chosen:** 3-layer humanization (deterministic + injection + comparison)
**Vote:** systems-architect: anti-pattern + personal context + structural templates | ml-engineer: structural scoring + style-transfer + A/B corpus test | developer-experience: (aligned on "wire the learning")
**Result:** 2-0 (DX focused on other points; SA and ML aligned)

**Three layers:**
1. **Deterministic scoring** ($0): sentence length variance (std dev < 4 = flag), single-sentence paragraph ratio, opening word diversity, consecutive same-structure detection
2. **Personal context injection** ($0): `data/personal-context.json` with 30+ real anecdotes, metrics, tool opinions. Rotate per generation.
3. **Style-transfer + A/B test** ($0.005/piece): Haiku rewrites to match voice profile, then runs Turing test against 3 real Camilo posts

**Total humanization cost: $0.005/piece = $0.40/month at 20 pieces/week.**

### 5. 1000_HOUR_PHASING
**Chosen:** 4-phase plan, publish-first, each phase independently valuable
**Vote:** All 3 aligned on sequence (close loop → scale data → optimize → polish)
**Result:** Unanimous (3-0)

---

## The 1000-Hour Plan

### Phase 1: Close The Loop (Hours 0-200, ~$25 API)

**Goal:** Publish 50 pieces you are proud of. Full telemetry. First complete improvement cycle with real engagement data.

| # | Task | Hours | Type |
|---|------|-------|------|
| 1 | Wire judge feedback injection into generator prompts | 20 | CODE |
| 2 | Wire diagnostician → NEXT.md task generation | 15 | CODE |
| 3 | Fix scraper image download bug, re-scrape 19 creators | 20 | DATA |
| 4 | Build SQLite corpus index from scraped data | 15 | CODE |
| 5 | Materialize top-50 few-shot examples per visual type | 10 | CODE |
| 6 | Wire few-shot examples into content generator prompts | 15 | CODE |
| 7 | Build humanization Layer 1 (structural scoring in quality_score.py) | 15 | CODE |
| 8 | Build humanization Layer 2 (personal-context.json + injection) | 10 | DATA+CODE |
| 9 | Build humanization Layer 3 (style-transfer + A/B corpus test) | 15 | CODE |
| 10 | Upgrade bandit to Thompson Sampling | 4 | CODE |
| 11 | Lower evolution gate from 500 → 100 | 1 | CODE |
| 12 | Fix judge model to Haiku (3.75x cost reduction) | 1 | CODE |
| 13 | Add `just data scrape/analyze/corpus` commands | 10 | DX |
| 14 | Reorganize justfile into 5-7 top-level verbs | 15 | DX |
| 15 | Generate 50 LinkedIn posts with full pipeline | 20 | CONTENT |
| 16 | Human-review all 50, fix issues diagnostician finds | 10 | REVIEW |
| 17 | Publish best 20 via social-media MCP | 4 | PUBLISH |

**Deliverable:** 20 published LinkedIn posts with engagement data, closed feedback loop, calibrated quality bar.

### Phase 2: Scale The Data (Hours 200-400, ~$35 API)

**Goal:** 5,000+ posts in reference library. 100 published pieces. Visual evaluation working.

| # | Task | Hours | Type |
|---|------|-------|------|
| 18 | Expand scraper to 50+ creators with proxy rotation | 30 | CODE |
| 19 | Build nightly scraping launchd plist | 10 | INFRA |
| 20 | Classify 5K+ posts with Gemini Flash pipeline | 20 | ML |
| 21 | Build multimodal visual judge (slide-1 gating) | 30 | ML |
| 22 | Wire 3-judge panel with cross-model validation | 20 | CODE |
| 23 | Expand carousel templates from 7 → 20 visual types | 40 | DESIGN |
| 24 | Build visual pattern analyzer from reference library | 25 | ML |
| 25 | Run 20-piece judge calibration set with Camilo | 10 | REVIEW |
| 26 | Generate 200 more pieces, publish 80 | 15 | CONTENT |

**Deliverable:** 5K+ classified posts, 100 published with analytics, multimodal visual evaluation, calibrated judges.

### Phase 3: Self-Improvement Engine (Hours 400-700, ~$45 API)

**Goal:** System quality improves measurably without human intervention.

| # | Task | Hours | Type |
|---|------|-------|------|
| 27 | Wire analytics → bandit rewards (engagement feedback) | 25 | CODE |
| 28 | Activate DSPy BootstrapFewShot at 100 observations | 20 | ML |
| 29 | Activate genetic evolution (already built) | 10 | CODE |
| 30 | Build MIPROv2 integration (replace stub) | 40 | ML |
| 31 | Full diagnostician with code reading (Opus) | 40 | CODE |
| 32 | Analytics-driven content calendar (system proposes topics) | 35 | CODE |
| 33 | Visual style replication ("in the style of X") | 40 | ML |
| 34 | Build carousel layout planner agent | 30 | CODE |
| 35 | Spearman correlation calibration at 100 paired observations | 10 | ANALYSIS |
| 36 | Reach 500 observations, run first full optimization | 50 | CONTENT |

**Deliverable:** System proposes content, generates, evaluates, improves its own prompts. Human approval only at publish gate.

### Phase 4: Scale & Polish (Hours 700-1000, ~$55 API)

**Goal:** Multi-platform, multi-format, approaching human quality.

| # | Task | Hours | Type |
|---|------|-------|------|
| 37 | Video content pipeline via genpeli MCP | 50 | CODE |
| 38 | Bilingual content (Spanish, separate voice profile) | 40 | CODE+DATA |
| 39 | Advanced visuals (evaluate DALL-E 3/Midjourney if template ceiling hit) | 40 | ML |
| 40 | Observatory dashboard with live quality metrics | 35 | FRONTEND |
| 41 | TextGrad integration (if genetic evolution plateaus) | 35 | ML |
| 42 | Full pipeline stress test: 100 pieces in one week | 30 | TEST |
| 43 | Cost monitoring (finance agent from ARCHITECTURE.md) | 20 | CODE |
| 44 | Documentation, test coverage 80%+, edge case hardening | 50 | QUALITY |

**Deliverable:** Fully autonomous content marketing system across text, visual, and video in two languages.

---

## Cost Summary

| Category | Spend |
|----------|-------|
| Data classification (10K posts) | $3-$9 |
| Content generation (500 pieces) | ~$36 |
| Evaluation (judges + panels) | ~$25 |
| Optimization (DSPy + genetic + MIPROv2) | ~$30 |
| Visual multimodal evaluation | ~$25 |
| Testing + calibration | ~$15 |
| **TOTAL API SPEND** | **~$140** |

**That's $0.14/hour of engineering or $0.28/piece.**

---

## Assumptions

| Assumption | Why We Made It | How to Validate | Risk if Wrong |
|---|---|---|---|
| Few-shot examples improve quality | Research shows 10-25% improvement on generation tasks | A/B test 10 pieces with vs without examples | Corpus is still valuable for calibration |
| Haiku is sufficient for judging | Classification task, not generation — Haiku within 5% of Sonnet on binary quality | Run calibration set, measure agreement | Switch to Sonnet if agreement < 80% |
| 50 pieces is enough to calibrate | N=84 for Spearman rho=0.3 at 80% power | Check correlation confidence intervals | Generate more before moving to Phase 2 |
| LinkedIn won't ban scraping at scale | Proxy rotation + rate limiting mitigates | Monitor ban rate per session | Supplement with LinkedIn API or data providers |
| Template ceiling is at ~7/10 quality | HTML/CSS can't match Figma sophistication | Compare template output to hand-designed references | Integrate image generation API earlier |

## Action Items (Start Tomorrow)

- [ ] Upgrade bandit to Thompson Sampling (4h, zero cost)
- [ ] Lower evolution gate 500 → 100 (1h, zero cost)
- [ ] Fix judge default to Haiku (1h, 3.75x cost savings)
- [ ] Build personal-context.json with 30+ real anecdotes (2h, zero cost)
- [ ] Generate 5 pieces with real judges and review quality (2h, ~$0.50)
