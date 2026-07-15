# LinkedIn Content Workflow

**Goal:** Build audience — grow followers, establish Juan as the go-to AI engineer
for the bilingual market.
**Target cadence:** 3-5 posts/week
**Phase 1 gate:** 4 consecutive weeks of ≥3 posts/week + measurable follower growth

---

## The Flow

```
INPUT
  ↓
[1. Idea Injector]
  ↓
[2. Context Builder]
  ↓
[3. Voice Writer]
  ↓
[4. Format Router]
  ↓
[5. Visual Generator — 2-3 variants]
  ↓
[6. Creator Council — evaluation + scores]
  ↓
[7. Approval Gate — Juan picks or rejects]
  ↓
[8. Publish → social-media-automatization]
  ↓
[9. Performance Loop — 48h later]
```

---

## Step 1: Idea Injector

**Two input modes:**

**Mode A — Juan's raw idea:**
Juan sends a raw idea via Telegram. Can be a sentence, a thought, a topic.
Examples:
- "MCPs are the new frontier for agent communication"
- "I realized agents need a quality gate to self-improve"
- "building invoz taught me how hard production ML really is"

**Mode B — Researcher auto-idea:**
`niche-researcher` agent runs on a schedule. Reads:
- LinkedIn trending topics in AI/ML/tech
- Recent papers or announcements relevant to Juan's positioning
- What competitor accounts in `brand.yaml` are posting
Outputs 3 candidate ideas. Juan picks one (or skips).

**Output of Step 1:**
```json
{
  "raw_idea": "MCPs are the new frontier for agents",
  "source": "juan" | "researcher",
  "content_pillar": "ai_engineering" | "building_in_public" | "bilingual_ai" | "systems_thinking",
  "product_angle": "holus" | "invoz" | "pilaster" | "genpeli" | null
}
```

---

## Step 2: Context Builder

Enriches the raw idea with substance.

**What it does:**
- Web search: what's happening in this space right now? (recent news, papers, threads)
- Product tie-in: if the idea connects to a product, pull relevant proof points from `brand.yaml → products_as_proof`
- Data point search: find 1-2 specific numbers, examples, or facts that ground the claim
- Anti-pattern check: flags if the idea risks any `brand.yaml → anti_patterns`

**Output:**
```json
{
  "enriched_idea": "MCPs (Model Context Protocol) are solving the agent communication problem...",
  "supporting_data": ["Anthropic released MCP spec Nov 2024", "250+ MCP servers on GitHub"],
  "product_connection": "Holus uses MCPs to connect to genpeli/pilaster/social-media",
  "angle": "builder who has shipped MCP integrations, not just read about them",
  "anti_pattern_flags": []
}
```

---

## Step 3: Voice Writer

Writes the LinkedIn post in Juan's voice.

**Agent:** `voice-guardian` + `hook-architect` + `storyteller` (sequential)

**Process:**
1. `hook-architect` writes the first 2 lines (80% of reach is decided here)
   - Must use one of: contrarian / confession / bold_claim / observation pattern
   - No "Let's dive in", no "In today's world", no exclamation marks
2. `storyteller` writes the body (personal experience → insight → bigger pattern)
   - First person always
   - Short paragraphs (1-3 sentences max)
   - One paradox or inversion
3. `cta-strategist` writes the closer
   - Direct question OR forward-looking statement
   - One sentence
4. `voice-guardian` reviews the full post
   - Checks every anti-pattern in `brand.yaml`
   - Checks voice consistency: builder-philosopher tone, contractions, em-dashes
   - BLOCKS if any anti-pattern detected → rewrites the offending section

**Output:**
```
[Hook — 2 lines]
[Body — 4-8 paragraphs of 1-3 sentences]
[Closer — 1 line]
[Optional: hashtags — max 3, relevant only]
```

**Hard rules:**
- Max 1500 characters (LinkedIn sweet spot for algorithm)
- No bullet lists for narrative posts (→ arrows for technical only)
- No walls of text
- Authenticity gate: if `voice-guardian` score < 70/100 → rewrite, don't publish

---

## Step 4: Format Router

Decides what format the post takes based on content type.

**Decision table:**

| Content type | Format | Visual |
|---|---|---|
| Personal story / lesson learned | Short text post | Optional image |
| Technical explanation (how X works) | Text + visual | Architecture diagram or chart |
| Framework / mental model | Carousel (5-7 slides) | Carousel PDF |
| Data-backed claim | Text + data visual | Chart or infographic |
| Behind-the-scenes / building update | Text post | Screenshot or before/after |
| Strong opinion / take | Short text post | None (text-only often outperforms) |

**Output:**
```json
{
  "format": "text_with_visual" | "carousel" | "text_only",
  "visual_type": "architecture_diagram" | "chart" | "carousel_pdf" | "infographic" | "image" | null,
  "visual_brief": "Show the 3-layer MCP architecture: Holus → MCP server → silo"
}
```

---

## Step 5: Visual Generator

Creates 2-3 visual variants from the `visual_brief`.

**The diversity algorithm: ε-greedy multi-armed bandit**

Each "arm" is a visual treatment combination:
- Background style (dark gradient / light clean / bold color)
- Typography (large headline / body-heavy / minimal)
- Layout (centered / split / asymmetric)
- Extras (icons / data annotations / product screenshots)

**Algorithm behavior:**
- 70% exploit: use the treatment combination with the highest engagement score from past posts
- 30% explore: try a new combination never used before (or rarely used)
- After each post's 48h performance data arrives → update arm weights

**Phase 1 (no data yet):** Pure exploration — randomly sample 2-3 different treatments.
**Phase 2 (10+ posts):** Start exploiting. Weight by engagement rate per treatment.
**Phase 3 (30+ posts):** Full bandit. Treatments that underperform get dropped.

**Output:** 2-3 visual files + metadata
```json
{
  "variants": [
    {"id": "A", "file": "variant_a.png", "treatment": "dark_gradient+large_headline+centered"},
    {"id": "B", "file": "variant_b.png", "treatment": "light_clean+body_heavy+split"},
    {"id": "C", "file": "variant_c.png", "treatment": "bold_color+minimal+asymmetric"}
  ]
}
```

---

## Step 6: Creator Council

**Phase 1: 1 evaluator (keep it simple)**
**Phase 2+: 3 evaluators with different lenses**

### Phase 1 Evaluator: `written-content-judge`

Scores the full post (text + best visual) on:

| Dimension | Weight | What it checks |
|---|---|---|
| Hook strength | 30% | Would YOU stop scrolling at this? |
| Voice fidelity | 25% | Sounds like Juan, not a bot |
| Insight depth | 20% | Teaches something real, not generic |
| Readability | 15% | Short paragraphs, clear flow |
| CTA quality | 10% | Closes with intention |

**Total score: 0-100**
- ≥ 80: Publish as-is
- 60-79: Publish with specific fixes noted
- < 60: Rewrite — specific feedback on what failed

### Phase 2 Evaluators (3 lenses):

**Evaluator 1: Engagement Expert**
"Would this get comments? Would people share it?"
Rubric: hook, CTA, conversation trigger, shareability

**Evaluator 2: Brand Voice Expert**
"Does this sound like Juan? Authentic or polished-corporate?"
Rubric: voice fidelity, anti-patterns, personal specificity, builder credibility

**Evaluator 3: LinkedIn Algorithm Expert**
"Will this get reach? Does it follow platform best practices?"
Rubric: format compliance, hook front-load, length, hashtag use, posting time

**Each evaluator:** scores 0-100 + 2-3 specific lines of feedback
**Combined:** weighted average + ranked variants (A > B > C)

---

## Step 7: Approval Gate

Juan sees:
- The post text
- 2-3 visual variants ranked by Creator Council score
- Per-variant scores + 1-line feedback each
- Recommended pick (highest score)

**Juan's options:**
- ✅ Approve variant X → schedule for posting
- ✏️ Edit + approve → Juan edits text, approves visual
- 🔄 Regenerate → new visuals with same text
- ❌ Reject all → back to Step 3 with Juan's note on what was wrong

**Every choice logged:**
```json
{
  "post_id": "...",
  "chosen_variant": "B",
  "council_scores": {"A": 82, "B": 79, "C": 71},
  "juan_overrode_recommendation": true,
  "juan_override_note": "B felt more authentic even with lower score"
}
```
Juan overrides are gold — they train the council's rubric over time.

---

## Step 8: Publish

Routes approved post + visual to `social-media-automatization`:
```python
social_media.schedule_post(
    content=post_text,
    media=chosen_variant_file,
    platforms=["linkedin"],
    scheduled_at=optimal_time  # from platform_config
)
```

Optimal posting times for LinkedIn audience growth:
- Tuesday–Thursday: 8-9am or 12-1pm (target timezone: EST)
- Avoid: Friday afternoon, weekends

---

## Step 9: Performance Loop (48h after posting)

**What it reads:**
- Impressions, reactions, comments, shares, profile visits
- Follower delta (did this post drive follows?)
- Comment quality (were they substantive or just emoji?)

**What it updates:**
1. Visual treatment bandit weights (which variant style got engagement?)
2. Hook pattern performance (which of the 4 hook types worked this week?)
3. Content pillar performance (which pillar is growing faster?)
4. `trajectory.jsonl` — full record for WeeklyLearningLoop

**Weekly synthesis (every Sunday):**
`marketing-strategist` reads all 7 days of trajectory → writes `MEMORY.md` update:
- What worked this week (specific)
- What didn't (specific)
- What to try next week
- Any pattern emerging in the audience (who's engaging?)

---

## Phase 1 Success Metrics

| Metric | Target | Measure |
|---|---|---|
| Posts/week | ≥ 3 | Count |
| Avg council score | ≥ 75/100 | Per post |
| Follower growth | +50/week | LinkedIn analytics |
| Avg engagement rate | ≥ 3% | (reactions+comments)/impressions |
| Post rejection rate | < 20% | Juan approval gate |

**Phase 1 → Phase 2 gate:**
4 consecutive weeks hitting all 5 metrics → activate 3-evaluator council + full bandit.

---

## What Needs to Be Built (not yet wired)

| Component | Status | Blocker |
|---|---|---|
| `idea-injector` — Telegram intake | ❌ Not built | Need Telegram → Holus pipeline |
| `niche-researcher` auto-mode | 🟡 Partial | Agent exists, not scheduled |
| `context-builder` enrichment | ❌ Not built | Need web search wiring |
| `voice-writer` pipeline (hook→story→cta→guard) | 🟡 Partial | `specialist_dispatch.py` exists, not sequential |
| `format-router` | 🟡 Partial | `format_planner.py` exists |
| Visual bandit algorithm | ❌ Not built | Need engagement data first |
| `creator-council` Phase 1 | 🟡 Partial | `judge.py` exists, rubric needs LinkedIn tuning |
| Approval gate UI (Telegram buttons) | ❌ Not built | Need Telegram inline buttons |
| Performance loop (48h read-back) | ❌ Not built | Need social-media MCP analytics call |

**Build order for Phase 1:**
1. Voice writer pipeline (hook → story → cta → guard) — core of the product
2. Approval gate via Telegram (you need to see and pick)
3. Format router + visual generator (2 variants minimum)
4. Publish wiring to social-media-automatization
5. 48h performance read-back

**Don't build yet:**
- Researcher auto-mode (manual idea injection first)
- Visual bandit (no data yet)
- 3-evaluator council (1 is enough for Phase 1)
