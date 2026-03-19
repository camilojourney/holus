# Experiment: Bilingual Content Strategy

**Goal:** Find the optimal language strategy for Juan's LinkedIn — Spanish, English, both, or mix. Data-driven, not assumption-based.

**Start date:** TBD
**Owner:** Juan Martinez

---

## Hypothesis

The "conventional wisdom" says: never translate, separate languages, English-first. But we don't know if that's true for Juan's specific niche (voice AI + AI adoption) and audience (mix of LatAm + global tech). This experiment tests 4 language strategies AND 3 timing strategies to find what actually works.

---

## Phase 1: Language Strategy (8 weeks)

### Conditions

| Condition | What | Posts | Duration |
|-----------|------|-------|----------|
| A | **English only** — all posts in English | 20 | 2 weeks |
| B | **Spanish only** — all posts in Spanish | 20 | 2 weeks |
| C | **Translated** — same content posted in both languages (EN version + ES version, same day or next day) | 20 pairs (40 posts) | 2 weeks |
| D | **Mixed original** — some posts in EN, some in ES, each original (not translated). ~60% EN / 40% ES | 20 | 2 weeks |

**Order:** A → B → C → D (not randomized — we need clean periods to measure follower growth per phase)

**Content control:** All 4 periods use the SAME content topics and formats. The ONLY variable is language. Pre-plan 20 topic ideas and assign them evenly across conditions.

**Topic bank (use same topics across all conditions):**
- Voice AI explainers (how TTS works, how ASR works)
- Invoz pipeline architecture
- AI adoption advice (should your business use voice AI?)
- Learning-in-public (what broke this week)
- Tool comparisons (Whisper vs Deepgram vs AssemblyAI)

### What to Measure (per post)

| Metric | How to Get |
|--------|-----------|
| Impressions | LinkedIn analytics (visible to post author) |
| Likes | Post metrics |
| Comments | Post metrics |
| Reposts | Post metrics |
| Engagement rate | (likes + comments + reposts) / impressions × 100 |
| Comment language | Manual: count EN vs ES comments |
| New followers that day | LinkedIn analytics → follower tab |
| Profile views that day | LinkedIn analytics |
| Save rate | LinkedIn analytics (if available) |

### Tracking Sheet

Create a simple spreadsheet or JSONL file:

```jsonl
{"date": "2026-04-01", "condition": "A", "language": "EN", "topic": "voice-ai-explainer", "format": "image+text", "time": "07:00 EST", "day": "Tuesday", "impressions": 0, "likes": 0, "comments": 0, "reposts": 0, "followers_gained": 0, "profile_views": 0, "comment_languages": {"en": 0, "es": 0, "other": 0}}
```

Record metrics at 24h, 48h, and 7d after posting (LinkedIn engagement peaks at 24-48h, long tail through 7d).

---

## Phase 2: Timing Strategy (6 weeks)

Run AFTER Phase 1 — using the winning language strategy from Phase 1.

### Variables to Test

| Variable | Options | Why It Matters |
|----------|---------|---------------|
| **Time of day** | 7 AM EST vs 12 PM EST vs 6 PM EST | LatAm audience is EST-adjacent. European Spanish speakers are +6h. Peak LinkedIn usage differs by timezone |
| **Day of week** | Weekday (Tue-Thu) vs Weekend (Sat-Sun) | LinkedIn engagement reportedly higher Tue-Thu, but Spanish-speaking audience might scroll weekends |
| **Posting gap** | Daily vs every-other-day vs 3x/week | Tests frequency fatigue. Does daily posting cannibalize your own reach? |

### Test Matrix

| Week | Time | Days | Frequency | Posts |
|------|------|------|-----------|-------|
| 1 | 7 AM EST | Tue-Thu-Sat | Every other day | 3 |
| 2 | 12 PM EST | Tue-Thu-Sat | Every other day | 3 |
| 3 | 6 PM EST | Tue-Thu-Sat | Every other day | 3 |
| 4 | 7 AM EST | Mon-Tue-Wed-Thu-Fri | Daily | 5 |
| 5 | 7 AM EST | Tue-Thu | 2x/week | 2 |
| 6 | Best time from W1-3 | Best frequency from W4-5 | Optimized | 3-5 |

**Content control:** Same format, similar topics across all weeks. Only variable is timing.

### What to Measure

Same metrics as Phase 1, plus:

| Metric | Why |
|--------|-----|
| Time to first engagement | How fast does the first like/comment come? Indicates timezone alignment |
| Impressions at 1h | Early signal of algorithmic boost |
| Impressions at 24h vs 48h | Some times have longer tails |
| Which timezone comments come from | Look at commenter profiles — LatAm? US? Europe? |

---

## Phase 3: Translation Test (2 weeks)

Only if Condition C (translated) showed promise in Phase 1. Deep-dive:

| Test | What | Duration |
|------|------|----------|
| C1 | Post EN version first, ES version 4 hours later same day | 1 week (5 pairs) |
| C2 | Post EN version Monday, ES version Tuesday (next day) | 1 week (5 pairs) |

**Measure:** Does the second post cannibalize the first? Do they reach different audiences? Does time gap matter?

---

## Phase 4: Format × Language Interaction (4 weeks)

Test whether certain FORMATS work better in certain LANGUAGES.

| Week | Format | Language | Posts |
|------|--------|----------|-------|
| 1 | PDF carousel | EN + ES (one of each per day) | 10 |
| 2 | Image + text | EN + ES | 10 |
| 3 | Text only | EN + ES | 10 |
| 4 | Video/demo | EN + ES | 10 |

**Hypothesis to test:**
- Carousels work equally in both languages (visual-heavy = language-agnostic?)
- Text-only posts perform better in English (larger reading audience?)
- Demos/videos work better in Spanish (more engaging for non-technical adopters?)

---

## Decision Framework

After all phases, score each strategy:

| Strategy | Avg Engagement Rate | Follower Growth/Week | Comment Quality (1-5) | Effort Required (1-5) | Score |
|----------|--------------------|--------------------|----------------------|----------------------|-------|
| English only | | | | | |
| Spanish only | | | | | |
| Translated | | | | | |
| Mixed original | | | | | |

**Weighted formula:**
```
Score = (engagement × 0.30) + (follower_growth × 0.30) + (comment_quality × 0.25) + (effort_inverse × 0.15)
```

Effort_inverse = 5 minus effort. Translation takes more effort, so if results are similar, the simpler strategy wins.

**Minimum sample for decision:** 20 posts per condition. Below that, do NOT make permanent strategy decisions.

---

## Guardrails

1. **Don't optimize prematurely.** Run the full 2 weeks per condition even if one looks bad early. LinkedIn engagement has high variance
2. **Same quality across conditions.** Don't subconsciously put more effort into your preferred language
3. **Record within 24 hours.** Engagement data gets stale. Log metrics the day after posting
4. **Account for external events.** If a post goes viral because of a trending topic, mark it as an outlier. Don't let one viral hit decide your strategy
5. **Content > language.** If ALL conditions get low engagement, the problem is content quality or topic selection, not language strategy. Don't blame language for bad content

---

## Timeline Summary

| Phase | Duration | What You Learn |
|-------|----------|---------------|
| Phase 1: Language | 8 weeks | Which language strategy gets best engagement |
| Phase 2: Timing | 6 weeks | Best time of day, day of week, frequency |
| Phase 3: Translation | 2 weeks | Whether translation helps or cannibalizes |
| Phase 4: Format × Language | 4 weeks | Which formats work in which language |
| **Total** | **20 weeks (~5 months)** | **Complete, data-backed content strategy** |

**Shortcut:** If Phase 1 shows a clear winner (>2x engagement difference), skip Phase 3 and go straight to Phase 2 with the winner. Cuts total time to ~14 weeks.

---

## How to Automate Tracking

The scraper (`scraper/linkedin-scraper.js`) can re-scrape your OWN profile weekly to capture engagement changes. Combined with LinkedIn's native analytics export (Settings → Get a copy of your data → Posts), you can build a complete dataset.

For production tracking, log each post to:
```
holus/docs/reference/linkedin/experiment-data/
├── phase1-language.jsonl
├── phase2-timing.jsonl
├── phase3-translation.jsonl
└── phase4-format.jsonl
```
