# Knowledge: Content Marketing Strategy

**Last updated:** 2026-03-01
**Updated by:** builder agent (cycle 23 — authority engine rewrite)
**Confidence:** high (derived from brand.yaml, tasks/next.md, voice-profile.md)
**Affects:** marketing agent strategy, content creation, platform selection, cadence
**Research cadence:** bi-weekly

---

## Strategic Goal

**Build Camilo's authority as the go-to AI transition consultant.**

This is NOT a product marketing strategy. Products (Pilaster, genpeli, invoz) are
proof points for consulting expertise. Content should position Camilo as a builder
who ships production AI — someone who helps companies do the same.

**Timeline:** NYC consulting launch in ~2 months. Content pipeline must be warm
by launch day. Every post builds the case: "This person has done it. He can help us."

**Primary outcome:** Inbound consulting leads (DMs, discovery calls).
**Secondary outcome:** Product awareness (brand building, not conversion-focused).

---

## Platform Hierarchy

| Platform | Role | Cadence | Content Source |
|----------|------|---------|---------------|
| **LinkedIn** | PRIMARY pipeline | 5x/week | Original, optimized for LinkedIn algorithm |
| Twitter | Amplification | 3x/week | Repurposed from LinkedIn (condensed) |
| Instagram | Brand building | 2x/week | Repurposed (visual or condensed caption) |
| Threads | Community | 2x/week | Repurposed (conversational version) |
| Facebook | Bilingual reach | 1x/week | Repurposed (Spanish translation when applicable) |

**Rule:** Create for LinkedIn. Repurpose for everything else.
Never create platform-specific content from scratch except for LinkedIn.

---

## Content Pillars

Five pillars. Every piece of content maps to exactly one.

### 1. Builder Stories (2x/week)
**Frame:** "I built X, here's what I learned."
**Products used:** Pilaster, genpeli, invoz (as evidence, not the pitch).
**Why it works:** Demonstrates hands-on expertise. Prospects think: "This person builds real things."
**Formats:** Long-form text post, carousel (architecture walkthrough), video (screen recording + narration).
**Example hooks:**
- "I replaced 4 hours of video editing with one command. Here's the architecture."
- "I made AI image generation backend-agnostic. Here's why your AI stack should be too."
- "Whisper in production — the lessons nobody talks about."

### 2. AI Implementation Frameworks (1x/week)
**Frame:** "How to actually deploy AI in your company."
**Products used:** None directly — consulting-focused, product-agnostic.
**Why it works:** Provides actionable value. Positions Camilo as someone who knows the playbook.
**Formats:** Text post with numbered steps, carousel (framework diagram), document post.
**Example hooks:**
- "Most companies fail at AI not because of the model. They fail at the data pipeline."
- "The 3-question test for whether your company actually needs AI (most don't pass)."
- "Here's exactly how I evaluate an AI vendor in 30 minutes."

### 3. Industry Analysis (1x/week)
**Frame:** "What's working in AI right now and what's hype."
**Products used:** None — landscape commentary.
**Why it works:** Shows Camilo sees the full picture, not just his own niche.
**Formats:** Text post (hot take + evidence), thread (multi-point analysis).
**Example hooks:**
- "Everyone's talking about agents. Nobody's talking about the infrastructure they need."
- "The AI startup graveyard is full of companies that nailed the model and ignored distribution."
- "What I learned reading 50 AI implementation case studies this month."

### 4. Results & Proof (every other week)
**Frame:** "Real numbers, real architectures, real outcomes."
**Products used:** Pilaster, genpeli, invoz (with metrics).
**Why it works:** Backs up authority with evidence. Hard to argue with data.
**Formats:** Before/after, data visualization, architecture diagram, screenshot + commentary.
**Example hooks:**
- "247 automated tests. 3 production AI systems. 0 downtime incidents. Here's how."
- "This AI image platform remembers every experiment it's ever run. Here's the schema."
- "Processing 1000 video clips per week with one Python script. The full pipeline."

### 5. Contrarian Takes (every other week)
**Frame:** "Everyone's doing X wrong. Here's why."
**Products used:** None — thought leadership.
**Why it works:** Sparks discussion, drives engagement, demonstrates independent thinking.
**Formats:** Text post (bold claim + reasoning), thread (myth-busting).
**Example hooks:**
- "Stop hiring AI engineers. Start training the ones you have."
- "Your AI strategy document is 40 pages too long."
- "The best AI tool for your company might be a spreadsheet."

---

## Pipeline Parameters

| Parameter | Value | Confidence | Source |
|-----------|-------|------------|--------|
| linkedin_cadence | 5x/week | high | brand.yaml |
| repurpose_ratio | 1 LinkedIn post → 4 platform adaptations | high | brand.yaml |
| pillar_rotation | builder_stories:2, frameworks:1, analysis:1, proof:0.5, contrarian:0.5 | high | brand.yaml |
| content_format_mix | 50% text, 25% carousel/document, 15% video, 10% image | medium | needs validation from analytics |
| cta_strategy | Soft CTA (DM me / comment) on 3/5 posts. Hard CTA (discovery call) on 1/5 | medium | needs A/B testing |
| review_mode | Human review for all posts (Phase 1) | high | AGENTS.md authority matrix |
| bilingual_frequency | 1x/week minimum (Facebook + selected LinkedIn) | medium | brand.yaml |

---

## Consulting Lead Metrics

Track these — not vanity metrics.

| Metric | What It Measures | Target (month 1) | Target (month 2) |
|--------|-----------------|-------------------|-------------------|
| Inbound DMs | Direct interest from prospects | 5/week | 15/week |
| Discovery calls booked | Pipeline conversion | 1/week | 3/week |
| Profile views | Top-of-funnel awareness | 500/week | 1500/week |
| Post impressions | Content reach | 5K/week | 20K/week |
| Engagement rate | Content resonance | >3% | >5% |
| Follower growth | Audience building | +50/week | +150/week |
| Saves/shares | Signal of high value content | Track per post | Optimize for these |
| Comment quality | Prospect vs. peer engagement | Track manually | Automate detection |

**Vanity metrics to deprioritize:** Likes (low signal), follower count (lagging), reach without engagement.

---

## Content Creation Flow

```
1. OBSERVE
   → Read analytics: what performed well this week?
   → Read niche research: what's trending in AI consulting space?
   → Read brand.yaml: refresh identity and positioning

2. REASON
   → Pick content pillar based on rotation schedule
   → Pick content format based on pillar + platform
   → Pick hook pattern based on viral framework library
   → Draft LinkedIn post using voice profile + authority framing

3. ACT
   → Generate LinkedIn post (primary)
   → Adapt for Twitter (condense to 280 chars or thread)
   → Adapt for Instagram (visual version or short caption)
   → Adapt for Threads (conversational reframe)
   → Adapt for Facebook (bilingual ES if applicable)
   → Queue all for review

4. EVALUATE
   → Track which pillar/format/hook performed best
   → Update performance-patterns.md
   → Feed learnings into next cycle
```

---

## LinkedIn Algorithm Signals (2026)

Prioritize content that triggers these signals:

| Signal | Weight | How to Trigger |
|--------|--------|---------------|
| Dwell time | High | Long-form posts (150+ words), storytelling, formatting that slows reading |
| Comments | High | End with a question, use contrarian framing, share actionable frameworks |
| Shares | Very high | Data-backed insights, frameworks people want to reference |
| Saves | High | Step-by-step guides, checklists, architecture diagrams |
| Profile clicks | Medium | Strong hook + incomplete story (makes reader curious about author) |
| External clicks | Low (penalized) | Avoid links in post body. Put links in first comment only |

**Formatting rules:**
- Hook in first line (stop the scroll)
- Line breaks between every 1-2 sentences
- Arrow bullets (→) for lists
- No external links in post body
- Question or forward statement as closer
- No hashtags in body (use 3-5 in first comment if at all)

---

## Content Calendar Template (Weekly)

| Day | Pillar | Format | Notes |
|-----|--------|--------|-------|
| Monday | Builder Stories | Text post | Start week strong with real experience |
| Tuesday | AI Frameworks | Carousel/document | High-value actionable content mid-week |
| Wednesday | Builder Stories | Text post or video | Second builder story, different product |
| Thursday | Industry Analysis | Text post | Commentary on current AI news/trends |
| Friday | Results/Proof OR Contrarian | Text post | End week with impact or thought-provoking take |

Rotate Results/Proof and Contrarian Takes on alternating Fridays.

---

## Research Priorities (Authority-Aligned)

| Priority | Research Area | Method | Frequency |
|----------|-------------|--------|-----------|
| P1 | Trending AI consulting content on LinkedIn | Web search + competitor monitoring | Weekly |
| P1 | Top-performing post formats in B2B/technical space | Analytics from social-media MCP | Weekly |
| P2 | Competitor content strategies (AI builders/consultants) | Manual review + pattern extraction | Bi-weekly |
| P2 | LinkedIn algorithm changes | Industry newsletters + testing | Monthly |
| P3 | New content formats (LinkedIn newsletters, audio events) | Exploratory | Quarterly |

---

## What Changed vs Last Version

**Complete rewrite.** Previous version (2026-02-26) was generic research questions about SaaS content
marketing. This version is an operational strategy document aligned to the authority engine pivot:
- Product promotion → consulting authority building
- Multi-platform → LinkedIn-first with repurposing
- Generic cadence → 5x/week LinkedIn with pillar rotation
- Engagement metrics → consulting lead metrics (DMs, discovery calls)
- Research questions → actionable parameters the marketing agent reads
