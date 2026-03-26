# Phase 2: Scale The Data (Hours 200-400, ~$35 API)

**Goal:** 5,000+ posts in reference library. 100 published pieces with analytics.
Visual evaluation working with multimodal judges.

**Deliverable:** 5K+ classified posts, 100 published with engagement data,
multimodal visual evaluation, calibrated judges.

**Entry criteria:** Phase 1 complete — 20 published posts, closed feedback loop,
average judge score > 0.75.

---

## Task 18: Expand Scraper to 50+ Creators

**Hours:** 30 | **Type:** CODE | **Priority:** P0 | **Dependencies:** Phase 1 Task 7

**What:** Scale the LinkedIn scraper from 19 to 50+ creators. Add proxy rotation
to avoid bans. Target: 5,000+ posts with images.

**Files to modify:**
- `docs/reference/linkedin/scraper/linkedin-scraper.js` — add proxy support
- `docs/reference/linkedin/scraper/scrape-all.sh` — add Tier 2 + Tier 3 handles

**New creators (from ADR-008):**
- **Tier 2 (visual-first, 10):** Zain Kahn, Lenny Rachitsky, Justin Welsh,
  Sahil Bloom, Ben Tossell, Irina Stanescu, Yasin Ozbey, Matt Shumer,
  Linas Beliunas, Aakash Gupta
- **Tier 3 (niche AI/ML, 20+):** Research and add 20 more creators in the
  AI consulting/builder niche. Focus on: engagement rate > 3%, post frequency
  > 2x/week, audience overlap with CTO/VP target.

**Proxy rotation:**
- Use residential proxy (BrightData/Oxylabs ~$10/mo)
- Rotate session every 100 requests
- Randomize delays between 45-120 seconds
- Max 300 posts per 24h window per session
- Store cookies encrypted, rotate sessions daily

**Rate limiting schedule:**
- 50 creators * 100 posts/creator = 5,000 posts
- At 300 posts/night = ~17 nights of scraping
- Run via launchd plist at 2am-6am daily

**Acceptance criteria:**
- [ ] 50+ creator handles in scrape-all.sh
- [ ] Proxy rotation working (verified by IP check)
- [ ] Rate limiting: max 300 posts/session, 45-120s random delays
- [ ] 5,000+ posts downloaded with images
- [ ] No LinkedIn bans during scraping period

---

## Task 19: Build Nightly Scraping Launchd Plist

**Hours:** 10 | **Type:** INFRA | **Priority:** P1 | **Dependencies:** Task 18

**What:** Automate the scraping via macOS launchd. Runs at 2am nightly,
scrapes next batch of creators, stores to SSD.

**File to create:**
- `infra/launchd/com.holus.scraper.plist`

**Configuration:**
- Run at 2:00 AM daily
- Environment: PATH, HOME, proxy credentials
- Working directory: repo root
- Stdout/stderr to logs/scraper.log
- Script: `cd docs/reference/linkedin/scraper && ./scrape-batch.sh`

**Batch script:** `scrape-batch.sh` reads a queue file (`scrape-queue.txt`),
pops the next 5 creators, scrapes them, marks them done. This way scraping
resumes across sessions without re-scraping completed creators.

**Acceptance criteria:**
- [ ] Plist validates with `plutil -lint`
- [ ] Nightly scraping runs unattended
- [ ] Queue tracks progress (don't re-scrape completed)
- [ ] Logs capture any errors

---

## Task 20: Classify 5K+ Posts with Gemini Flash

**Hours:** 20 | **Type:** ML | **Priority:** P1 | **Dependencies:** Tasks 8, 18

**What:** Run bulk classification on all 5K+ posts using Gemini Flash 2.0
(cheapest multimodal model). Classify visual type, teaching value, scroll-stop power.

**File to create:**
- `src/holus/data/classifier.py`

**Classification pipeline:**
1. Load unclassified posts from SQLite corpus
2. For each post with an image:
   - Send image + text to Gemini Flash
   - Classify: visual_type (12 categories), teaching_value (0-10), scroll_stop_power (0-10)
   - Store classification in SQLite sidecar columns
3. For text-only posts:
   - Classify: content_type (12 categories), hook_type, structural_pattern
4. Validate: run Haiku on 10% random sample, compare classifications

**Cost math:**
- 5K posts * ~1000 tokens/post = 5M tokens
- Gemini Flash 2.0: $0.10/M input, $0.40/M output
- Total: $0.50 + $2.00 = **$2.50**
- Haiku validation (500 posts): **$1.44**
- **Total: ~$4**

**Classification schema:**
```json
{
  "visual_type": "flowchart|carousel|comparison|data_viz|code_card|screenshot|diagram|chart|infographic|meme|photo|text_only",
  "content_type": "tutorial|builder_story|contrarian|framework|case_study|announcement|tips|career|industry_analysis|personal|tool_review|research",
  "teaching_value": 7.5,
  "scroll_stop_power": 8.2,
  "hook_type": "contrarian|question|bold_claim|narrative|number|confession",
  "structural_pattern": "hook_story_insight_cta|list_with_examples|before_after|problem_solution|thread"
}
```

**Acceptance criteria:**
- [ ] All 5K+ posts classified
- [ ] Haiku validation accuracy > 90% on visual_type
- [ ] Classifications stored in SQLite corpus
- [ ] `just data stats` shows classification coverage
- [ ] Total classification cost < $5

---

## Task 21: Build Multimodal Visual Judge (Slide-1 Gating)

**Hours:** 30 | **Type:** ML | **Priority:** P1 | **Dependencies:** None

**What:** Build a visual evaluator that looks at actual rendered PNGs, not just
text descriptions. Use progressive gating: evaluate only slide 1 first (cheap),
then full carousel only if slide 1 passes (expensive).

**Files to create/modify:**
- `src/holus/self_improvement/visual_judge.py` — new module
- `agents/evaluators/visual-content-judge.md` — update to support image input

**Architecture:**
```
Gate 1: Deterministic spec checks ($0)
  → slide count, text density, color palette, font sizes
  → Blocks 30-40% of bad specs

Gate 2: Slide-1 Haiku vision ($0.04-$0.15)
  → Render first slide to PNG
  → Send to Haiku vision: "Score scroll-stop power 1-10. Would you stop scrolling?"
  → Threshold: score >= 6 passes

Gate 3: Full Sonnet vision on PASS candidates ($1.22)
  → Render all slides
  → Full 5-dimension rubric evaluation
  → Only for the 25% that pass Gate 2
```

**Blended cost: ~$0.48/carousel instead of $1.50 without gating.**

**Acceptance criteria:**
- [ ] Gate 1 catches obvious spec failures (too many words, wrong dimensions)
- [ ] Gate 2 evaluates slide 1 PNG with Haiku vision
- [ ] Gate 3 evaluates full carousel with Sonnet vision
- [ ] Progressive gating reduces evaluation cost by 60%+
- [ ] Integration with existing `evaluate_with_routing()` for CAROUSEL content type

---

## Task 22: Wire 3-Judge Panel with Cross-Model Validation

**Hours:** 20 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Task 21

**What:** Replace single-model judge with a 3-model panel: Haiku + Haiku + Gemini Flash.
Median score is the final score. Cross-model validation breaks same-model bias.

**Files to modify:**
- `src/holus/self_improvement/judge.py` — add panel evaluation mode

**Panel composition:**
- Judge A: Claude Haiku (written-content-judge rubric)
- Judge B: Claude Haiku (brand-safety-judge rubric)
- Judge C: Gemini Flash (cross-model validator — same rubric as Judge A)

**Scoring:** Median of 3 scores. If any judge gives FAIL → FAIL (gate authority preserved).

**Cost:** ~$0.008/eval for the panel (vs $0.004 for single judge). Acceptable
because cross-model validation catches the most dangerous systematic bias.

**Acceptance criteria:**
- [ ] 3 judges run in parallel
- [ ] Median score used as final score
- [ ] FAIL from any judge = FAIL (gate authority)
- [ ] Cross-model validator uses different provider (Gemini, not Claude)
- [ ] Tests for panel scoring logic

---

## Task 23: Expand Carousel Templates

**Hours:** 40 | **Type:** DESIGN | **Priority:** P2 | **Dependencies:** Task 20

**What:** Analyze the top 50 carousels from the reference library and create
20+ HTML/CSS templates based on real high-performing layouts.

**Files to modify:**
- `src/holus/visual/templates/` — new template directory
- `src/holus/visual/carousel_builder.py` — register new templates

**Template categories (from reference library analysis):**
1. Step-by-step tutorial (numbered steps, each slide = one step)
2. Before/after comparison (split layout)
3. Framework diagram (central concept + branches)
4. Code walkthrough (syntax-highlighted code + annotation)
5. Data visualization (chart + insight callout)
6. Checklist (checkmarks + brief descriptions)
7. Timeline (chronological progression)
8. Comparison table (X vs Y grid)
9. Quote + insight (large quote + context)
10. Architecture diagram (boxes + arrows)
11. Tool review (screenshot + pros/cons)
12. Storytelling (one paragraph per slide, photo-style background)
13. FAQ format (question slide → answer slide)
14. Statistic callout (big number + context)
15. Process flow (input → steps → output)
16. Decision tree (if/then branching)
17. Myth vs reality (two-column debunk)
18. Resource list (curated links/tools)
19. Case study (problem → solution → results)
20. Mini-course (lesson 1/5, lesson 2/5, etc.)

**Each template has:**
- HTML/CSS file in `templates/{name}.html`
- JSON schema defining required fields
- Preview PNG for reference
- Mapping to visual_type classification

**Acceptance criteria:**
- [ ] 20+ templates created
- [ ] Each template renders correctly in Playwright
- [ ] Templates cover all 12 visual_type classifications
- [ ] `carousel_builder.py` can select template by visual_type
- [ ] Brand colors/fonts applied to all templates

---

## Task 24: Build Visual Pattern Analyzer

**Hours:** 25 | **Type:** ML | **Priority:** P2 | **Dependencies:** Task 20

**What:** Analyze the classified visual corpus to extract patterns: which visual
types get highest engagement, what layout elements correlate with scroll-stop power,
which color schemes work best.

**File to create:**
- `src/holus/data/visual_analyzer.py`

**Analysis outputs:**
```json
{
  "top_visual_types_by_engagement": [
    {"type": "carousel", "avg_engagement": 4521, "count": 230},
    {"type": "architecture_diagram", "avg_engagement": 3102, "count": 85}
  ],
  "scroll_stop_patterns": [
    "Bold number in first 3 words of slide 1",
    "Dark background with light text",
    "Max 10 words on slide 1"
  ],
  "engagement_by_slide_count": {
    "5-7": 3200, "8-10": 4100, "11-15": 2800
  },
  "winning_color_schemes": ["dark_navy_gold", "white_black_accent"]
}
```

Store results in `data/visual-patterns.json`. Feed into carousel builder
template selection and visual evaluator rubric calibration.

**Acceptance criteria:**
- [ ] Analysis runs on full classified corpus
- [ ] Patterns are statistically significant (n >= 20 per category)
- [ ] Results saved to `data/visual-patterns.json`
- [ ] `just data analyze-visuals` command

---

## Task 25: Judge Calibration with Camilo

**Hours:** 10 | **Type:** REVIEW | **Priority:** P1 | **Dependencies:** Tasks 16-17

**What:** Camilo rates 20 content pieces: 10 he considers "excellent" and 10
"bad." Compare Camilo's ratings with judge scores. If agreement < 80%,
adjust judge rubric before freezing.

**Process:**
1. Select 20 diverse pieces from content-queue (mix of platforms, types)
2. Camilo reads each and rates: PASS / FAIL
3. Compare with judge verdicts
4. For disagreements: analyze which dimension the judge got wrong
5. Adjust dimension weights or thresholds

**Statistical target:** Cohen's kappa > 0.6 (substantial agreement).

**Acceptance criteria:**
- [ ] 20 pieces rated by Camilo
- [ ] Judge-human agreement >= 80% (16/20)
- [ ] Disagreement analysis identifies which dimensions need adjustment
- [ ] Rubric updated if agreement < 80%

---

## Task 26: Generate 200 + Publish 80

**Hours:** 15 | **Type:** CONTENT | **Priority:** P1 | **Dependencies:** All above

**What:** Generate 200 more content pieces using the improved pipeline (few-shot
grounding, humanization, better templates). Publish the best 80.

**Process:**
- Run 40 generation cycles (5 pieces each)
- Review with `just evaluate-content` after each batch
- Run `just diagnose` weekly
- Publish approved pieces via social-media MCP
- Collect analytics every 72 hours

**Tracking:**
- Judge score trend (should improve week over week)
- Engagement data from published pieces
- Bandit arm performance (which visual types/content types win)
- Diagnostician finding count (should decrease)

**Acceptance criteria:**
- [ ] 200 pieces generated
- [ ] 80 pieces published
- [ ] Average engagement rate tracked
- [ ] Bandit has 100+ observations with real engagement rewards
- [ ] At least 1 prompt evolution cycle triggered (gate at 100)
