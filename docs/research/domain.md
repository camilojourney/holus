---
last_updated: 2026-03-04
review_cadence: 60d
next_review: 2026-05-03
owner: juan
dependent_specs: []
---

# Domain Research — Holus

Last updated: 2026-03-04
Review cadence: 60 days
Next review: 2026-05-03

---

## 1. Platform-Specific Content Rules

### 1.1 Character Limits (Hard Limits)

| Platform | Post Limit | Visible Before Truncation | Notes |
|----------|-----------|--------------------------|-------|
| Twitter / X | 280 characters | Full post visible | No "See more" |
| Instagram | 2,200 characters | ~125 chars (approx) | Caption-heavy posts ok |
| LinkedIn | 3,000 characters | ~140 chars (desktop), ~110 chars (mobile) | "See more" triggers early |
| Facebook | 33,000 characters | ~80 chars ideal | Longer = less engagement |
| TikTok | 2,200 characters | Visual-first, text secondary | Captions less critical |
| YouTube (Shorts desc.) | 5,000 characters | First 100 chars visible | Algorithm reads description |

[VERIFIED — sociality.io Nov 21 2025 + quickfansandlikes.com Feb 2026, Grade B]

### 1.2 Tone Guidelines Per Platform

| Platform | Tone | Format | Hashtag Strategy |
|----------|------|--------|-----------------|
| LinkedIn | Professional, educational, thought-leadership | Paragraphs with line breaks, bullet lists OK | 3–5 hashtags, relevant industry terms |
| Instagram | Visual-first, fun, aspirational, emotional | Hook → body → CTA, emoji OK | 5–15 hashtags in caption or first comment |
| Twitter / X | Punchy, conversational, opinionated | Short sentences, threads for long-form | 1–2 hashtags max |
| TikTok | Casual, trend-aware, relatable, high energy | Hook in first 3 seconds (video), caption is secondary | Trending hashtags, 3–5 |
| Facebook | Conversational, community-focused | Shorter is better (≤80 chars ideal) | 1–2 hashtags |

[VERIFIED — contentstudio.io 2025, sociality.io Nov 2025, Grade B]

### 1.3 Key Adaptation Rules for Holus

When adapting content across platforms, Holus must:

1. **Hard limit enforcement:** Never generate content exceeding platform character limits
2. **LinkedIn truncation optimization:** Put the hook in the first 140 characters — that's what users see before "See more" [VERIFIED — quickfansandlikes.com Feb 2026, Grade B]
3. **Twitter compression:** Full ideas must compress to ≤280 chars or become a thread
4. **Tone shift:** Same concept, different voice — professional for LinkedIn, punchy for Twitter, emotional for Instagram
5. **Hashtag injection:** Platform-appropriate hashtag count, injected at the end

---

## 2. Bilingual Content Strategy (EN ↔ ES)

### 2.1 Why Bilingual for Juan's Products

Juan is bilingual Colombian-American. His audience for Pilaster/Genpeli potentially spans both English-speaking and Spanish-speaking communities. Bilingual content doubles reach without doubling creation effort — when done by an AI brain.

### 2.2 Translation Approach

**Recommendation:** Use Claude Sonnet 4 for in-pipeline translation, not a dedicated MT engine.

**Rationale:**
- Marketing content requires tone adaptation, not just literal translation
- LLMs capture idiomatic expressions and cultural nuance in marketing copy [VERIFIED — vincentschmalbach.com Apr 2025, getblend.com Oct 2025, Grade B]
- DeepL is stronger for literal fidelity but weaker for creative voice [UNVERIFIED — DeepL's own claim, Grade C vendor source]
- Using Claude means no additional API dependency

### 2.3 Translation Quality Notes

- For EN↔ES (a well-resourced language pair), top LLMs perform at par or above specialized MT systems for marketing content [VERIFIED — two independent secondary sources agree, Grade B]
- DeepL's self-reported claim: 2-3× fewer edits needed vs Google Translate [UNVERIFIED — vendor-only source, Grade C]
- Google Translate: generally lower quality for creative/marketing content than both LLMs and DeepL [UNVERIFIED — community consensus, no primary benchmark]

### 2.4 Bilingual Pipeline Design

```
Draft in English (primary language)
  ↓
Spanish adaptation (Claude Sonnet 4 — translate + culturally adapt)
  ↓
Platform adaptation (EN version per platform)
  ↓
Platform adaptation (ES version per platform)
  ↓
Approval queue (Juan reviews both versions)
  ↓
Publish: EN to primary accounts, ES to bilingual/Hispanic-targeted accounts (if configured)
```

**Key constraint:** Translation is not literal — it's cultural adaptation. The Spanish version of an Instagram caption should feel native to a Spanish speaker, not translated.

---

## 3. Content Marketing Fundamentals

### 3.1 Content Type Performance (Holus's Internal Reference)

From RESEARCH.md (existing internal data, not externally verified):
- Tutorial posts outperform promo posts 4:1 (Juan's observed pattern)
- Platform analytics drive content type weighting

### 3.2 Content Calendar Logic

- **Feature-triggered content:** New product release → immediate tutorial or demo post
- **Evergreen content:** Scheduled during quiet weeks, pulled from backlog
- **Platform weighting:** Platform allocation follows engagement analytics

### 3.3 Hook Optimization

Per platform adaptation rules:
- **LinkedIn:** First 140 chars are the hook — must create curiosity or state value clearly
- **Twitter:** The entire post is the hook — no room for buildup
- **Instagram:** Caption hook matters less; visual is the hook — caption amplifies
- **TikTok:** First 3 seconds of video is the hook — caption is secondary

[VERIFIED for LinkedIn truncation rule — quickfansandlikes.com Feb 2026, Grade B; rest [UNVERIFIED] as industry best practice]

---

## 4. Domain Constraints

| Constraint | Impact on Holus Design |
|-----------|----------------------|
| Twitter/X 280 char hard limit | Content adapter must enforce before sending to social-media-auto API |
| LinkedIn "See more" at 140 chars | Hook must be front-loaded in first 140 chars |
| Instagram visual-first | Caption quality matters less than image/video quality; Holus focuses on brief, punchy captions |
| Platform algorithm opacity | No reliable public data on what content gets boosted; rely on observed analytics |
| API rate limits (platform side) | Handled by social-media-auto service; Holus doesn't manage this directly |

---

## Open Questions

- [ ] What is the actual engagement delta for bilingual vs English-only posts on Juan's accounts? (needs production data)
- [ ] Does Instagram's algorithm differentiate between English and Spanish captions? (platform research needed)
- [ ] What is the optimal EN/ES content ratio for Juan's audience? (analytics-driven decision, not research)
- [ ] Optimal hashtag count for Reels in 2026? (platform rules change frequently)

---

## Sources

1. Sociality.io, "Social media character limits in 2025 (Free Cheat Sheet and tools)", https://sociality.io/blog/social-media-character-limits/ (November 21, 2025)
2. QuickFansAndLikes, "LinkedIn Post Size Guide 2025: Character Limits & Best Practices", https://quickfansandlikes.com/linkedin-post-size (February 2026)
3. ContentStudio, "The complete guide to social media image sizes in 2025", https://contentstudio.io/blog/social-media-post-sizes (2025)
4. Vincent Schmalbach, "DeepL vs LLMs for Translation", https://www.vincentschmalbach.com/deepl-vs-llms-for-translation/ (April 25, 2025)
5. Blend, "Best LLMs for Translation in 2025: GPT-4 vs Claude, Gemini", https://www.getblend.com/blog/which-llm-is-best-for-translation/ (October 17, 2025)
6. GTR Socials, "Character Limits on Social Media: The 2025 Guide", https://gtrsocials.com/blog/character-limits-on-social-media (2025)
