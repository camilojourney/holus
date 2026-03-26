# Phase 4: Scale & Polish (Hours 700-1000, ~$55 API)

**Goal:** Multi-platform, multi-format content approaching human quality.
Fully autonomous operation with human approval only at publish gate.

**Deliverable:** Content marketing system that generates, evaluates, publishes,
learns, and improves across text, visual, and video formats in two languages.

**Entry criteria:** Phase 3 complete — system self-improves measurably,
500+ observations, prompt evolution producing better variants, calibrated judges.

---

## Task 37: Video Content Pipeline via Genpeli MCP

**Hours:** 50 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Phase 3

**What:** Wire genpeli MCP for short-form video generation from text scripts.
This is a new modality that reuses the existing pipeline architecture.

**Files to modify/create:**
- `src/holus/agents/marketing/video_workflow.py` — already exists, verify/extend
- `src/holus/integrations/genpeli/client.py` — already exists, verify MCP connection
- `agents/specialists/script-writer.md` — verify prompt quality

**Pipeline:**
```
content_calendar proposes video topic
  → script-writer agent generates video script
  → script evaluated by video-content-judge
  → if PASS: send to genpeli MCP (process_video)
  → genpeli processes: silence removal, captions, audio normalization
  → human reviews via Telegram approval
  → publish to LinkedIn/TikTok/YouTube Shorts
```

**Video types to support:**
1. Talking head with captions (Camilo speaking)
2. Screen recording with narration (code walkthrough)
3. Slide-to-video (carousel animated into video)

**Acceptance criteria:**
- [ ] Script generation → genpeli MCP → processed video → publish
- [ ] Video judge evaluates scripts (hook_timing, pacing, retention)
- [ ] At least 3 videos generated and published
- [ ] Video engagement data collected and fed to bandit

---

## Task 38: Bilingual Content (Spanish)

**Hours:** 40 | **Type:** CODE+DATA | **Priority:** P2 | **Dependencies:** Phase 3

**What:** Generate original Spanish content (not translations). Pattern 11 from
the reference library: "Never translate the same post; create original per language."

**Files to create/modify:**
- `config/brand-es.yaml` — Spanish voice profile
- `.self-improvement/knowledge/current/voice-profile-es.md` — Spanish voice identity
- `src/holus/agents/marketing/agent.py` — language-aware generation
- `agents/specialists/bilingual-localizer.md` — already exists, verify

**Details:**
- Spanish targets different audience segment (LatAm tech founders, not US CTOs)
- Separate Thompson Sampling arms for Spanish content
- Separate judge calibration (engagement patterns differ by language)
- LinkedIn primary, Facebook secondary (strong LatAm Facebook usage)

**Acceptance criteria:**
- [ ] Spanish brand voice defined in brand-es.yaml
- [ ] Content generated natively in Spanish (not translated)
- [ ] Separate bandit arms for Spanish content
- [ ] At least 10 Spanish posts generated and published
- [ ] Engagement data collected for Spanish content

---

## Task 39: Advanced Visual Generation

**Hours:** 40 | **Type:** ML | **Priority:** P2 | **Dependencies:** Phase 2 Task 23

**What:** Evaluate whether HTML/CSS templates have hit their quality ceiling.
If yes, integrate an image generation API for hero visuals while keeping
templates for structured content.

**Decision process:**
1. Compare template-rendered carousels against hand-designed reference carousels
2. Score both with multimodal visual judge
3. If template avg < 7/10 on brand_alignment and visual_hierarchy → ceiling hit

**If ceiling hit, integrate:**
- DALL-E 3 for hero images (~$0.04/image)
- OR Midjourney API for higher quality (~$0.08/image)
- OR Pilaster MCP for character-consistent images (own infrastructure)

**Keep templates for:**
- Flowcharts, architecture diagrams, comparison tables, code cards
- Anything with precise text placement and data visualization

**Use image generation for:**
- Hero slides (slide 1 of carousel — the scroll-stopper)
- Social media thumbnails
- Blog post headers

**Acceptance criteria:**
- [ ] Template quality ceiling measured objectively
- [ ] Image generation API integrated if needed
- [ ] Hero images generated for carousel slide 1
- [ ] Cost per visual tracked and within budget
- [ ] Template + generated hybrid carousels score higher than templates alone

---

## Task 40: Observatory Dashboard with Live Quality Metrics

**Hours:** 35 | **Type:** FRONTEND | **Priority:** P2 | **Dependencies:** Phase 3

**What:** Upgrade the Observatory frontend to show real-time quality metrics,
bandit performance, and improvement trajectory.

**Files to modify:**
- `observatory/frontend/` — React dashboard
- `src/holus/api/` — FastAPI backend routes

**Dashboard sections:**
1. **Quality Trend:** Line chart of avg judge score over time (weekly buckets)
2. **Bandit Arms:** Table showing each arm's win rate, trials, 95% CI
3. **Platform Performance:** Engagement by platform (LinkedIn, Twitter, etc.)
4. **Dimension Heatmap:** Which rubric dimensions score highest/lowest
5. **Improvement Log:** Timeline of prompt evolution generations, DSPy optimizations
6. **Diagnostician Findings:** Current P0/P1 issues with status (open/fixed)
7. **Cost Tracker:** API spend per day/week/month by model

**Acceptance criteria:**
- [ ] Dashboard loads at localhost:3000
- [ ] All 7 sections populated with real data
- [ ] Auto-refreshes every 5 minutes
- [ ] Mobile-responsive (Camilo checks on phone)

---

## Task 41: TextGrad Integration

**Hours:** 35 | **Type:** ML | **Priority:** P3 | **Dependencies:** Task 29

**What:** If genetic evolution plateaus (3 consecutive cycles with < 1% improvement),
integrate TextGrad for fine-grained gradient-based prompt optimization.

**When to build:** ONLY if genetic evolution + MIPROv2 plateau.

**How TextGrad works:**
1. Define a computation graph: prompt → LLM → output → judge → score
2. When score is low, ask LLM: "Given this output scored low on X,
   how should the prompt change?"
3. LLM provides textual "gradient" (e.g., "add more specificity requirements")
4. Apply gradient to prompt, re-run, compare scores
5. Keep changes that improve, revert changes that hurt

**Cost:** ~$0.10 per optimization step. 10-20 steps per prompt = $1-$2/optimization.

**Files to create:**
- `src/holus/self_improvement/textgrad_optimizer.py`

**Acceptance criteria:**
- [ ] TextGrad optimization produces measurable improvement over genetic+MIPROv2
- [ ] Changes are specific (not just "make it better")
- [ ] Rollback works if optimization makes things worse
- [ ] Cost tracked per optimization run

---

## Task 42: Full Pipeline Stress Test

**Hours:** 30 | **Type:** TEST | **Priority:** P1 | **Dependencies:** All above

**What:** Generate 100 pieces in one week. Publish 50+. Verify the entire
pipeline holds up under sustained load.

**Test scenarios:**
1. **Throughput:** Generate 20 pieces/day for 5 days
2. **Quality:** Average judge score stays above 0.75
3. **Variety:** Content covers all 5 pillars, all platforms
4. **Self-improvement:** Weekly improvement cycle runs and changes something
5. **Cost:** Total API spend for 100 pieces + evaluations + optimizations
6. **Reliability:** No crashes, no stale locks, no data corruption
7. **Recovery:** Simulate failure mid-generation, verify pipeline resumes

**Acceptance criteria:**
- [ ] 100 pieces generated without crashes
- [ ] 50+ pieces published
- [ ] Average judge score > 0.75
- [ ] All 5 content pillars represented
- [ ] Improvement cycle ran and produced at least 1 prompt change
- [ ] Total cost documented and within budget

---

## Task 43: Cost Monitoring (Finance Agent)

**Hours:** 20 | **Type:** CODE | **Priority:** P2 | **Dependencies:** Phase 3

**What:** Build the finance agent described in ARCHITECTURE.md. Reads API costs
from the proxy, tracks spend per model/agent/task.

**Files to create:**
- `src/holus/agents/finance/report.py`

**What it tracks:**
- Daily/weekly/monthly API spend by model (Haiku/Sonnet/Opus/Gemini)
- Cost per content piece (generation + evaluation + optimization)
- Cost per optimization cycle
- Cost trending (is spend increasing or stable?)
- Budget alerts (if daily spend > $5, weekly > $20)

**Report output:** `.self-improvement/reports/finance/YYYY-MM-DD.md`
```markdown
# Finance Report — 2026-04-15

## Weekly Spend: $4.32
- Generation (Sonnet): $1.80 (42%)
- Evaluation (Haiku): $0.60 (14%)
- Visual eval (Haiku vision): $0.92 (21%)
- Optimization (DSPy): $0.60 (14%)
- Other: $0.40 (9%)

## Per-Piece Cost: $0.29
## Budget Status: ON TRACK ($4.32 / $10 weekly budget)
```

**Justfile command:** `just improve costs`

**Acceptance criteria:**
- [ ] Cost tracking from trajectory metadata (tokens, model used)
- [ ] Weekly report generated automatically in improvement_cycle
- [ ] Budget alerts logged when thresholds exceeded
- [ ] `just improve costs` shows current spend breakdown

---

## Task 44: Documentation + Test Coverage + Hardening

**Hours:** 50 | **Type:** QUALITY | **Priority:** P2 | **Dependencies:** All above

**What:** Final polish. Documentation for the entire system. Test coverage
to 80%+. Edge case handling.

**Documentation:**
- `docs/GETTING_STARTED.md` — How to set up and run Holus from scratch
- `docs/CONTENT_WORKFLOW.md` — Step-by-step content creation → publishing flow
- `docs/SELF_IMPROVEMENT.md` — How the learning loop, bandits, evolution work
- `docs/TROUBLESHOOTING.md` — Common errors and fixes

**Test coverage targets:**
- `src/holus/data/corpus.py` — 90%+
- `src/holus/data/few_shot.py` — 90%+
- `src/holus/self_improvement/diagnostician.py` — 80%+
- `src/holus/agents/marketing/humanize.py` — 90%+
- `src/holus/visual/style_replicator.py` — 80%+

**Edge case hardening:**
- Graceful degradation when proxy is down
- Graceful degradation when SSD is disconnected
- Lock file handling for concurrent generation
- Rate limit handling for social-media API
- Retry logic for all external API calls

**Acceptance criteria:**
- [ ] 4 documentation files written
- [ ] Test coverage > 80% on new modules
- [ ] All external API calls have retry + graceful degradation
- [ ] System runs for 7 days unattended without crashes
