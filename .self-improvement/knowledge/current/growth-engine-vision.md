# Knowledge: Authority Engine Vision

**Last updated:** 2026-03-01
**Updated by:** builder agent (cycle 26 — authority engine alignment)
**Confidence:** high (this IS the product — aligned with brand.yaml, strategy, audience, platforms)
**Affects:** marketing agent strategy, content generation, analytics, everything
**Research cadence:** continuous

---

## What Holus MUST Become

Holus is not a content poster. It is an **authority-building engine** that positions
Camilo as the go-to AI transition consultant. Every piece of content builds the case:
"This person has done it. He can help us."

1. **Researches what's working in the niche** — finds top-performing AI consulting/builder content on LinkedIn, extracts patterns
2. **Extracts frameworks from top performers** — reverse-engineers why certain posts get engagement (hooks, structure, proof, CTAs)
3. **Creates content using proven patterns in Camilo's voice** — builder-philosopher archetype, first-person, direct, evidence-grounded
4. **Publishes LinkedIn-first, repurposes everywhere** — one post becomes 5 platform adaptations
5. **Tracks what converts to consulting leads** — DMs, discovery calls, profile views, not just impressions
6. **Learns and improves automatically** — weekly analysis feeds back into strategy

## The Authority Loop

```
OLD: Post about products → Hope for users → Wait → Nothing
NEW: Research niche → Create authority content → Publish → Track consulting signals → Learn → Scale
```

The difference: content serves the consulting pipeline, not product adoption.
Products are proof points ("I built this") not the primary pitch.

---

## Target Results (Consulting Metrics)

### Pipeline Metrics (what actually matters)

| Metric | Month 1 | Month 2 | Why It Matters |
|--------|---------|---------|----------------|
| Inbound DMs from prospects | 5/week | 15/week | Direct consulting interest |
| Discovery calls booked | 1/week | 3/week | Pipeline conversion |
| Profile views | 500/week | 1500/week | Top-of-funnel awareness |

### Content Performance Metrics (leading indicators)

| Metric | Month 1 | Month 2 | Why It Matters |
|--------|---------|---------|----------------|
| Post impressions | 5K/week | 20K/week | Reach into target audience |
| Engagement rate | >3% | >5% | Content resonance |
| Follower growth | +50/week | +150/week | Audience building |
| Saves/shares | Track per post | Optimize | Signal of high-value content |
| Comment quality | Track manually | Automate detection | Prospect vs. peer engagement |

### Anti-Metrics (deprioritize)

- Likes (low signal — easy to give, doesn't indicate intent)
- Raw follower count (lagging — quality matters more)
- Reach without engagement (vanity — impressions alone mean nothing)
- Cross-platform aggregate views (misleading — LinkedIn is what matters)

---

## What This Means for the Agent

### The agent MUST:

1. **Load brand identity every cycle** — read `config/brand.yaml` for positioning, voice, anti-patterns
2. **Study the niche BEFORE creating content** — web search for trending AI consulting content on LinkedIn
3. **Analyze what top performers do** — extract hooks, structures, proof patterns, CTAs
4. **Pick a content pillar from the rotation** — builder stories, AI frameworks, industry analysis, results/proof, contrarian takes
5. **Create for LinkedIn first** — optimized for LinkedIn algorithm signals (dwell time, comments, shares)
6. **Repurpose for all other platforms** — one LinkedIn post becomes Twitter, Instagram, Threads, Facebook adaptations
7. **Track consulting signals** — DMs, profile views, comment quality, not just engagement
8. **Run weekly analysis** — what pillar/format/hook drove prospect engagement? Double down.
9. **Match Camilo's voice exactly** — first-person, direct, builder mindset, no corporate speak (see brand.yaml voice section)

### The agent MUST NOT:

- Create product-focused promotional content ("Check out Pilaster's new feature!")
- Optimize for vanity metrics (likes, impressions without engagement)
- Create platform-specific content from scratch for non-LinkedIn platforms
- Use corporate language, buzzwords, or sycophantic openings (see brand.yaml anti_patterns)
- Generate financial advice or reference trading systems
- Post without human review (Phase 1 — all posts require approval)

---

## Content Pillar Framework

Five pillars. Every post maps to exactly one. Rotation: 5x/week on LinkedIn.

| Pillar | Frequency | Frame | Consulting Signal |
|--------|-----------|-------|-------------------|
| Builder Stories | 2x/week | "I built X, here's what I learned" | Demonstrates hands-on expertise |
| AI Frameworks | 1x/week | "How to actually deploy AI" | Provides actionable value to prospects |
| Industry Analysis | 1x/week | "What's working and what's hype" | Shows landscape awareness |
| Results/Proof | every other week | "Real numbers, real outcomes" | Backs authority with evidence |
| Contrarian Takes | every other week | "Everyone's doing X wrong" | Sparks discussion, shows independent thinking |

Products appear in pillars 1 and 4 as evidence. Pillars 2, 3, and 5 are product-agnostic
consulting content.

---

## Hook Framework (Proven Patterns)

Machine-readable format — the agent selects from these per pillar and format.

```yaml
hooks:
  contrarian:
    pattern: "Most [audience] are still [old approach]. That's why they [pain]."
    pillars: [contrarian_takes, ai_frameworks]
    example: "Most companies are still evaluating AI vendors. That's why they're 18 months behind."

  builder_reveal:
    pattern: "I [built/automated/replaced] X. Here's [the architecture/what broke/what I learned]."
    pillars: [builder_stories, results_proof]
    example: "I replaced 4 hours of video editing with one command. Here's the architecture."

  bold_claim:
    pattern: "[Strong statement]. [Evidence or qualification]."
    pillars: [contrarian_takes, industry_analysis]
    example: "Your AI strategy document is 40 pages too long. Here's why."

  data_lead:
    pattern: "I [analyzed/tracked/measured] [quantity] of [thing]. Here's what [nobody tells you/I found]."
    pillars: [results_proof, industry_analysis]
    example: "I tracked every AI implementation I've done. The #1 failure mode isn't the model."

  question_inversion:
    pattern: "[Common assumption]. But what if [contrarian reframe]?"
    pillars: [contrarian_takes, ai_frameworks]
    example: "Everyone wants to hire AI engineers. But what if you already have them?"

  confession:
    pattern: "I used to [common belief]. Then I [experience that changed my mind]."
    pillars: [builder_stories, contrarian_takes]
    example: "I used to believe the formula was simple. Then I built three production systems."
```

---

## Voice Profile Summary

Derived from brand.yaml and analysis of 15 published posts (full details in voice-profile.md).

**Archetype:** Builder-philosopher
**Core traits:**
- First person always — "I built", "I learned", "I realized"
- Short paragraphs — 1-3 sentences max
- Arrow bullets (→) for technical lists
- One paradox or inversion per post
- Close with a direct question or forward-looking statement
- Confident but honest — builder, not guru
- Ground claims in evidence — data, names, real outcomes

**Never sounds like:** ChatGPT, corporate comms, influencer, guru, generic AI content

---

## The End State

Holus wakes up every day and:

1. Checks what went viral in the AI consulting niche overnight
2. Reads Camilo's brand identity and current strategy (`config/brand.yaml`)
3. Picks a content pillar from the weekly rotation
4. Selects a hook pattern from the viral framework library
5. Creates a LinkedIn post that sounds like Camilo, uses proven patterns, builds authority
6. Adapts it for Twitter, Instagram, Threads, Facebook
7. Queues everything for human review (Phase 1)
8. After posting, tracks what converted to consulting signals (DMs, profile views, calls)
9. Runs weekly analysis: which pillar/format/hook drove prospect engagement?
10. Feeds learnings back — doubles down on what works, kills what doesn't

Camilo reviews once a week. Content flows. Authority builds.
By the time the NYC consulting launch happens, the pipeline is warm.
Prospects already know who Camilo is, what he builds, and what he can do for them.

---

## What Changed vs Last Version

**Authority engine alignment rewrite.** Previous version (2026-02-26) was the original founder
vision — framed as "social media growth engine" targeting 1M+ organic views, focused on
product promotion and viral content creation. This version:
- "Growth engine" → "Authority-building engine" for consulting pipeline
- Target metrics: 1M views → consulting metrics (DMs, discovery calls, profile views)
- Products: primary pitch → proof points for builder expertise
- Content: viral for virality's sake → authority-building with consulting conversion
- Voice: placeholder → references complete voice profile and brand.yaml
- Hook patterns: generic templates → categorized by pillar with consulting angles
- Loop: Post→Hope→Wait → Research→Create→Publish→Track consulting signals→Learn
- Aligned with brand.yaml, content-marketing-strategy.md, audience-profiles.md, platforms.md
