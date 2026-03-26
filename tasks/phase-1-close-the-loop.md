# Phase 1: Close The Loop (Hours 0-200, ~$25 API)

**Goal:** Publish 50 pieces you are proud of. Full telemetry. First complete
improvement cycle with real engagement data.

**Deliverable:** 20 published LinkedIn posts with engagement data, a working
closed feedback loop, and a calibrated quality bar.

**Exit criteria:** You can run `just generate` → `just evaluate-content` →
`just approve-content <id>` → `just publish` → wait 72h → `just collect-analytics`
→ `just improve-cycle` and the system learns from what worked.

---

## Task 1: Upgrade Bandit to Thompson Sampling

**Hours:** 4 | **Type:** CODE | **Priority:** P0 | **Dependencies:** None

**What:** Replace epsilon-greedy exploration in the strategy bandit with Thompson
Sampling using Beta distributions. Thompson Sampling converges 2-3x faster with
sparse data (< 30 trials per arm).

**Files to modify:**
- `src/holus/agents/marketing/strategy_bandit.py` — the `Bandit` class
- `tests/unit/agents/test_strategy_bandit.py` — update tests

**Details:**
- Current: `random.random() < epsilon` for exploration
- New: `numpy.random.beta(alpha, beta)` per arm, pick highest sample
- Each arm tracks `wins` (engagement > threshold) and `trials`
- Prior: Beta(1, 1) = uniform (no bias)
- Update: on success → alpha += 1, on failure → beta += 1
- Remove epsilon parameter, add `prior_alpha` and `prior_beta` (default 1, 1)

**Acceptance criteria:**
- [ ] Bandit selects arms using Beta distribution sampling
- [ ] Arms with more wins get selected more often
- [ ] Arms with few trials get explored more (uncertainty)
- [ ] Existing tests updated, new tests for Thompson Sampling behavior
- [ ] `just check` passes

---

## Task 2: Lower Evolution Gate from 500 to 100

**Hours:** 1 | **Type:** CODE | **Priority:** P0 | **Dependencies:** None

**What:** The prompt evolution system (`prompt_evolution.py`) has an activation
gate at 500 trajectory entries. Currently at ~240. Lower to 100 so it activates.

**Files to modify:**
- `src/holus/agents/marketing/orchestrator.py` — line with `if total_entries >= 500`
- Change `500` to `100`

**Risk:** Overfitting at n=100. Mitigate: evolution only runs weekly and keeps
top 3 variants (elitism prevents catastrophic regression).

**Acceptance criteria:**
- [ ] Gate changed from 500 to 100
- [ ] `just improve-cycle` triggers prompt evolution when trajectory has 100+ entries
- [ ] `just check` passes

---

## Task 3: Fix Judge Default Model to Haiku

**Hours:** 1 | **Type:** CODE | **Priority:** P0 | **Dependencies:** None

**What:** `JudgeAgent.__init__` defaults to `anthropic/claude-sonnet-4-6` ($3/M input).
The architecture doc says Haiku for cost efficiency. Change to Haiku for 3.75x savings.

**Files to modify:**
- `src/holus/self_improvement/judge.py` — `__init__` method, default model parameter

**Cost impact:** 100 evals/week: Sonnet = $0.44/week, Haiku = $0.12/week.

**Acceptance criteria:**
- [ ] Default model is `anthropic/claude-haiku-4-5-20251001` (or latest Haiku)
- [ ] Judge still produces structured JSON evaluations
- [ ] Run `just evaluate-content` on 3 pieces, verify scores are reasonable
- [ ] `just check` passes

---

## Task 4: Build personal-context.json

**Hours:** 2 | **Type:** DATA | **Priority:** P0 | **Dependencies:** None

**What:** Create a JSON file with 30+ real anecdotes, metrics, tool opinions,
and personal experiences that only Camilo would know. These get injected into
content generation prompts to make content sound genuinely human.

**File to create:**
- `data/personal-context.json`

**Structure:**
```json
{
  "anecdotes": [
    {
      "id": "judge-broken-2-months",
      "text": "The judge evaluator was broken for 2 months because of a one-line path bug (parents[2] instead of parents[3]). All content scored 100/100. Nobody noticed because the system had no way to check itself.",
      "products": ["holus"],
      "topics": ["debugging", "self-improvement", "automation"]
    }
  ],
  "metrics": [
    {
      "id": "holus-test-count",
      "text": "1266 unit tests passing across 130 source files",
      "product": "holus",
      "updated": "2026-03-26"
    }
  ],
  "opinions": [
    {
      "id": "mcp-over-rest",
      "text": "MCP (Model Context Protocol) is better than REST for agent-to-tool communication because the agent discovers capabilities at runtime instead of hardcoding endpoints",
      "products": ["holus", "genpeli"]
    }
  ],
  "project_facts": [
    {
      "id": "genpeli-pipeline",
      "text": "genpeli processes raw human video footage — removes silences, burns word-by-word captions, normalizes audio. One command replaces 4 hours of manual editing.",
      "product": "genpeli"
    }
  ]
}
```

**Fill with real data from:**
- Git history (`git log --oneline | head -50`)
- ARCHITECTURE.md product descriptions
- Real bugs encountered (judge path bug, Twitter threading, Threads truncation)
- Real metrics (test count, LOC, agent count, specs written)
- Real tool opinions (why Playwright, why MCP, why SQLite)

**Acceptance criteria:**
- [ ] 30+ entries across anecdotes, metrics, opinions, project_facts
- [ ] All entries are factually true (verifiable from codebase/git)
- [ ] JSON validates cleanly
- [ ] No sensitive data (API keys, passwords, client names)

---

## Task 5: Wire Judge Feedback into Generator Prompts

**Hours:** 20 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Task 3

**What:** When the marketing agent generates content, it should see what the
judge said about the LAST cycle's content. This closes the tightest feedback loop:
piece N's evaluation improves piece N+1.

**Already partially done:** `agent.py` `observe()` now calls `_load_prior_judge_feedback()`
which reads trajectory. But the feedback needs to flow into the actual LLM prompt
during the `reason()` and `act()` phases.

**Files to modify:**
- `src/holus/agents/marketing/agent.py` — ensure `prior_judge_feedback` from observe
  is included in the system prompt for the reason/act phases
- `src/holus/agents/marketing/prompts.py` — add a `{prior_feedback}` template variable
  in the generation prompt that receives the formatted judge feedback
- `src/holus/agents/marketing/idea_runner.py` — if this is the generation path,
  inject feedback here too

**Details:**
The feedback should be formatted as:
```
## Lessons from Last Cycle (do NOT repeat these mistakes)

- [THREADS — PARTIAL] "Content was LinkedIn essay format, not Threads native. Compress to 3-4 punchy lines."
  Weak dimensions: brevity=0.30, native_feel=0.25

- [TWITTER — PARTIAL] "NOT formatted as a Twitter thread. Split into numbered tweets."
  Weak dimensions: thread_pacing=0.48
```

Cap at 5 most recent failures. Only include FAIL/PARTIAL, not PASS.

**Acceptance criteria:**
- [ ] Generator prompt includes last cycle's judge feedback
- [ ] Feedback is formatted with platform, verdict, and weak dimensions
- [ ] Capped at 5 entries to prevent prompt bloat
- [ ] Generate 3 pieces and verify the output addresses prior feedback
- [ ] `just check` passes

---

## Task 6: Wire Diagnostician to NEXT.md Task Generation

**Hours:** 15 | **Type:** CODE | **Priority:** P1 | **Dependencies:** None

**What:** The diagnostician produces structured findings (DiagnosticTask objects)
but they're only written to a report file. Wire it to also append tasks to NEXT.md.

**Files to modify:**
- `src/holus/self_improvement/diagnostician.py` — add `append_to_next_md()` function
- `.self-improvement/NEXT.md` — the diagnostician appends under a `## System Diagnostic Tasks` section

**Details:**
- Only append P0 and P1 findings (not P2/P3 — those are suggestions, not urgent)
- Check if a similar task already exists before appending (avoid duplicates)
- Format as: `- [ ] [{category}] {description} — File: {file_ref}. Fix: {suggested_fix}`
- Add a `last_diagnostic: YYYY-MM-DD` header so the next run knows when it last ran

**Acceptance criteria:**
- [ ] `just diagnose` appends P0/P1 findings to NEXT.md
- [ ] Duplicate tasks are not re-added
- [ ] Tasks are formatted with category, file reference, and suggested fix
- [ ] `just check` passes

---

## Task 7: Fix Scraper Image Download Bug + Re-scrape

**Hours:** 20 | **Type:** DATA | **Priority:** P1 | **Dependencies:** None

**What:** The LinkedIn scraper has a known bug where images are tagged as "video"
resulting in 0 images downloaded for 6 out of 19 creators. Fix the image detection
logic and re-scrape all 19 creators with proper image downloads.

**Files to modify:**
- `docs/reference/linkedin/scraper/linkedin-scraper.js` — image detection logic
- `docs/reference/linkedin/scraper/scrape-all.sh` — verify all 19 handles

**Details:**
- LinkedIn loads images lazily with `<img>` tags inside `<div data-urn>` containers
- The bug: some image containers have a video play button overlay, causing the
  scraper to classify them as video type when they're actually static images with
  a decorative overlay
- Fix: check for actual `<video>` tags, not just play button overlays
- Re-scrape all 19 creators with images enabled
- Verify: each creator should have images/ directory with JPGs

**Acceptance criteria:**
- [ ] All 19 creators have posts-raw.json with image URLs
- [ ] Images downloaded to `{creator}/images/{id}.jpg`
- [ ] JSON sidecar files alongside each image
- [ ] Total corpus: 500+ posts with images

---

## Task 8: Build SQLite Corpus Index

**Hours:** 15 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Task 7

**What:** Build a SQLite database that indexes all scraped posts for fast querying.
This replaces scanning flat JSON files and enables FTS + engagement sorting.

**File to create:**
- `src/holus/data/corpus.py` — CorpusDB class

**Schema:**
```sql
CREATE TABLE posts (
    id TEXT PRIMARY KEY,
    creator TEXT NOT NULL,
    text TEXT,
    engagement_total INTEGER DEFAULT 0,
    reactions INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    reposts INTEGER DEFAULT 0,
    visual_type TEXT,  -- flowchart, carousel, comparison, data_viz, etc.
    content_type TEXT, -- tutorial, builder_story, contrarian, etc.
    teaching_value REAL,  -- 0-10 from classifier
    scroll_stop_power REAL,  -- 0-10 from classifier
    image_path TEXT,
    scraped_at TEXT,
    created_at TEXT
);

CREATE VIRTUAL TABLE posts_fts USING fts5(text, creator, content_type);
CREATE INDEX idx_engagement ON posts(engagement_total DESC);
CREATE INDEX idx_visual_type ON posts(visual_type);
```

**API:**
```python
class CorpusDB:
    def __init__(self, db_path: Path): ...
    def ingest_raw(self, creator_dir: Path): ...  # Import from posts-raw.json
    def search(self, query: str, limit: int = 10) -> list[dict]: ...
    def top_by_engagement(self, visual_type: str = None, limit: int = 5) -> list[dict]: ...
    def top_by_type(self, content_type: str, limit: int = 5) -> list[dict]: ...
    def stats(self) -> dict: ...  # counts, avg engagement, etc.
```

**Justfile commands:**
```
just data reindex    # Rebuild SQLite from all raw JSON files
just data stats      # Show corpus statistics
just data search "query"  # Full-text search
just data top --type carousel --limit 10  # Top by engagement
```

**Acceptance criteria:**
- [ ] SQLite database created at `/Volumes/SSD/holus/reference-library/_index/posts.db`
- [ ] All scraped posts indexed with engagement data
- [ ] FTS search works (`just data search "ComfyUI workflow"`)
- [ ] Top-by-engagement query returns correct results
- [ ] `just data stats` shows total posts, creators, visual types
- [ ] Tests for CorpusDB class

---

## Task 9: Materialize Few-Shot Examples

**Hours:** 10 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Task 8

**What:** Extract the top 3-5 examples per visual type from the corpus and save
them as pre-computed JSON files. The content generator reads ONLY these files
at generation time, keeping prompt token costs constant.

**File to create:**
- `src/holus/data/few_shot.py` — FewShotMaterializer class

**Output directory:** `data/few-shot-examples/`
```
data/few-shot-examples/
  text_post/top-5.json
  carousel/top-5.json
  thread/top-5.json
  video_script/top-5.json
  infographic/top-5.json
```

**Each example contains:**
```json
{
  "creator": "santiago_valdarrama",
  "text": "...",
  "engagement_total": 4521,
  "visual_type": "carousel",
  "why_it_works": "Specific debugging story with real error messages. Hook uses a number. Each slide reveals one new insight."
}
```

The `why_it_works` field is generated by running Haiku on each example once at
materialization time (~$0.01 for 50 examples).

**Justfile command:** `just data materialize`

**Acceptance criteria:**
- [ ] Top-5 files exist for each content type
- [ ] Each example has text, engagement, creator, and `why_it_works`
- [ ] Materialization is idempotent (running twice produces same output)
- [ ] `just data materialize` works

---

## Task 10: Wire Few-Shot Examples into Content Generator

**Hours:** 15 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Task 9

**What:** When the content generator creates a LinkedIn post, inject the top 3
examples from the few-shot library that match the target content type/platform.

**Files to modify:**
- `src/holus/agents/marketing/idea_runner.py` or `content_generator.py` — load
  few-shot examples before generation call
- `src/holus/agents/marketing/prompts.py` — add `{few_shot_examples}` section
  to generation prompt

**Prompt format:**
```
## Top-Performing Examples (study these — they worked on LinkedIn)

### Example 1 (4,521 reactions — @santiago_valdarrama)
[full post text]
Why it works: Specific debugging story with real error messages...

### Example 2 (3,102 reactions — @chip_huyen)
[full post text]
Why it works: Production ML incident with exact metrics...

### Example 3 (2,847 reactions — @armand_ruiz)
[full post text]
Why it works: Architecture diagram with contrarian framing...

Now write YOUR post about {topic}. Match their quality. Be specific like them.
```

Cap at 3 examples (~1500 tokens) to avoid prompt bloat.

**Acceptance criteria:**
- [ ] Few-shot examples loaded and injected into generation prompt
- [ ] Examples match the target content type (carousel examples for carousel generation)
- [ ] Capped at 3 examples
- [ ] Generate 3 pieces and verify output quality is influenced by examples
- [ ] `just check` passes

---

## Task 11: Build Humanization Layer 1 — Structural Scoring

**Hours:** 15 | **Type:** CODE | **Priority:** P1 | **Dependencies:** None

**What:** Add structural AI-detection checks to `quality_score.py`. These catch
patterns that make text "feel" AI-generated beyond phrase matching.

**Files to modify:**
- `src/holus/agents/marketing/quality_score.py`

**New checks:**
1. **Sentence length variance:** Split text into sentences. Compute std dev of
   word counts. If std dev < 4 → penalty 15 (AI has unnaturally consistent
   sentence lengths).
2. **Single-sentence paragraph ratio:** For LinkedIn, 30%+ of paragraphs should
   be 1 sentence (pattern from top creators). If < 30% → penalty 10.
3. **Opening word diversity:** Check first word of each paragraph. If "I", "The",
   "In", or "It" appear as openers in > 50% of paragraphs → penalty 10.
4. **Consecutive same-structure:** If 3+ consecutive sentences have the same word
   count (+/- 2 words) → penalty 10 (mechanical rhythm).

**Acceptance criteria:**
- [ ] All 4 checks implemented with ViolationDetail entries
- [ ] AI-generated text from today's output triggers at least 1 new check
- [ ] Human-written reference posts (from voice-profile.md) score 0 penalties
- [ ] Tests for each new check
- [ ] `just check` passes

---

## Task 12: Build Humanization Layer 2 — Personal Context Injection

**Hours:** 10 | **Type:** CODE | **Priority:** P1 | **Dependencies:** Task 4

**What:** Before each content generation, randomly select 2-3 entries from
`personal-context.json` that match the target product/topic and inject them
into the prompt as "real experiences to reference."

**Files to modify:**
- `src/holus/agents/marketing/agent.py` or `idea_runner.py` — load and inject context
- `src/holus/agents/marketing/prompts.py` — add `{personal_context}` template var

**Prompt format:**
```
## Your Real Experiences (reference these — they're TRUE)

- You built genpeli's pipeline. One command replaces 4 hours of manual editing.
- The judge evaluator was broken for 2 months because of a one-line path bug.
- Holus has 1266 unit tests across 130 source files.

Use at least ONE of these real facts in your post. They make it authentic.
```

**Selection logic:**
- Filter by product match (if generating about genpeli, prefer genpeli entries)
- Filter by topic overlap (if generating about debugging, prefer debugging anecdotes)
- Random selection within filtered set (so consecutive posts reference different facts)
- Never inject more than 3 entries (keep it brief)

**Acceptance criteria:**
- [ ] 2-3 personal context entries injected per generation
- [ ] Entries match the target product/topic when possible
- [ ] Generated content references at least 1 real fact
- [ ] Different facts used on consecutive generations
- [ ] `just check` passes

---

## Task 13: Build Humanization Layer 3 — Style Transfer + A/B Test

**Hours:** 15 | **Type:** CODE | **Priority:** P2 | **Dependencies:** None

**What:** After content generation, run two post-processing steps:
1. Style-transfer rewrite with Haiku to match Camilo's voice
2. A/B corpus comparison (Turing test) to verify humanness

**File to create:**
- `src/holus/agents/marketing/humanize.py`

**Style transfer:**
```python
def humanize_text(text: str, voice_examples: list[str]) -> str:
    """Haiku rewrites text to match Camilo's voice.

    System prompt: 'You are Camilo. Rewrite this to match your voice.
    Break one long paragraph. Add one rough edge. Remove one qualifier.
    Make one sentence unexpectedly short. Keep ALL factual claims intact.'

    Input: generated text + 3 real Camilo posts from corpus
    Output: rewritten text
    Cost: ~$0.003 per piece
    """
```

**A/B corpus test:**
```python
def turing_test(candidate: str, real_posts: list[str]) -> float:
    """Run Turing test: can Haiku identify the AI-generated post?

    Prompt: 'Here are 3 real LinkedIn posts by Camilo and 1 candidate.
    Which one is the candidate? Explain why.'

    Returns confidence score 0-1 (how easily it was identified).
    Score > 0.8 = too obviously AI, needs more humanization.
    Score < 0.5 = passes the test, sounds human.
    """
```

**Cost:** ~$0.005/piece total ($0.003 + $0.002).

**Acceptance criteria:**
- [ ] Style transfer rewrites content to be more voice-consistent
- [ ] A/B test correctly identifies obviously AI text (score > 0.8)
- [ ] A/B test gives low scores to real Camilo posts (score < 0.3)
- [ ] Integration: runs after content generation, before judge evaluation
- [ ] Tests for both functions
- [ ] `just check` passes

---

## Task 14: Add Data Commands to Justfile

**Hours:** 10 | **Type:** DX | **Priority:** P2 | **Dependencies:** Tasks 8, 9

**What:** Add data pipeline commands to the justfile.

**Commands to add:**
```
just data reindex        # Rebuild SQLite from raw JSON files
just data stats          # Show corpus statistics
just data search "query" # Full-text search
just data top --type X   # Top posts by engagement
just data materialize    # Generate few-shot example files
just data scrape <handle> # Scrape a single LinkedIn creator
```

**Acceptance criteria:**
- [ ] All commands work
- [ ] `just data stats` shows total posts, creators, visual types

---

## Task 15: Reorganize Justfile

**Hours:** 15 | **Type:** DX | **Priority:** P2 | **Dependencies:** None

**What:** The justfile has 55 commands with semantic overlap (4 publish commands,
3 improve commands, 3 schedule commands). Reorganize into clear top-level verbs.

**Target structure:**
```
just content generate         # was: just generate
just content evaluate         # was: just evaluate-content
just content review           # was: just review-content
just content approve <id>     # was: just approve-content
just content publish          # was: just publish
just content calendar         # was: just calendar

just data scrape <handle>     # NEW
just data reindex             # NEW
just data stats               # NEW
just data materialize         # NEW

just improve learn            # was: just learn
just improve diagnose         # was: just diagnose
just improve cycle            # was: just improve-cycle
just improve status           # was: just improvement-status

just deploy schedule          # was: just schedule
just deploy unschedule        # was: just unschedule
just deploy status            # was: just schedule-status

just check                    # unchanged (lint + test)
just health                   # unchanged
```

Keep old names as hidden aliases for backward compat with launchd plists.

**Acceptance criteria:**
- [ ] Commands reorganized into 5-7 top-level verbs
- [ ] Old command names still work (aliases)
- [ ] Launchd plists still reference valid commands
- [ ] `just --list` is readable at a glance

---

## Task 16: Generate 50 LinkedIn Posts

**Hours:** 20 | **Type:** CONTENT | **Priority:** P1 | **Dependencies:** Tasks 5, 10, 11, 12

**What:** Run the full content pipeline 10 times (5 pieces each = 50 total).
Use `just generate` with all improvements wired in.

**Process:**
1. Run `just generate` — produces 5 pieces (LinkedIn + 4 repurposed)
2. Run `just evaluate-content` — see real judge scores
3. Run `just diagnose` — see if diagnostician finds issues
4. Fix any issues the diagnostician identifies
5. Repeat 10 times

**Track:**
- Average judge score per iteration (should improve)
- Number of FAIL/PARTIAL verdicts (should decrease)
- Diagnostician findings (should decrease)

**Acceptance criteria:**
- [ ] 50 pieces generated in data/content-queue/
- [ ] Average judge score > 0.75 by iteration 8-10
- [ ] Diagnostician finding count decreases over iterations
- [ ] At least 30 pieces score PASS

---

## Task 17: Human Review + Publish 20

**Hours:** 14 | **Type:** REVIEW + PUBLISH | **Priority:** P1 | **Dependencies:** Task 16

**What:** Review all 50 pieces. Select the best 20. Humanize them (SPEC-032 gate).
Publish via social-media MCP.

**Process:**
1. `just content review` — scan all pending pieces
2. For each: read the text, check quality, decide approve/reject
3. For approved pieces: edit in Observatory UI for humanization
4. `just publish --dry-run` — verify what will be posted
5. `just publish` — post to LinkedIn

**After publishing:** Wait 72 hours. Then:
6. `just collect-analytics` — fetch engagement data
7. `just improve-cycle` — run first real improvement cycle with engagement data

**Acceptance criteria:**
- [ ] 20 pieces published to LinkedIn
- [ ] Analytics collected for all 20 pieces
- [ ] First improvement cycle completes with real engagement data
- [ ] Bandit has 20+ observations with real rewards
