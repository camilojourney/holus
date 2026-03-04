---
last_updated: 2026-03-04
review_cadence: 60d
next_review: 2026-05-03
owner: juan
dependent_specs: []
---

# Market Research — Holus

Last updated: 2026-03-04
Review cadence: 60 days
Next review: 2026-05-03

---

## 1. Market Context

Holus is Juan's **private competitive advantage** — not a product sold to customers. It is the internal content brain that powers his public-facing apps (Pilaster, Genpeli, Invoz). The "market" research here serves two purposes:

1. Understand what competitors exist so Holus can do what they *can't* do
2. Identify the positioning gap Holus fills for its internal client (Juan)

---

## 2. Competitor Matrix

| Name | Type | Pricing | Key Feature | Our Advantage | Our Gap |
|------|------|---------|-------------|---------------|---------|
| Jasper | SaaS | $49–$69/month (Pro) | Brand voice, marketing workflows, image gen | Autonomous pipeline; no manual workflow setup | Jasper has brand compliance tools we'd need to build |
| Copy.ai | SaaS | $49/month Starter, $249/month Advanced | GTM workflows, sales automation | Full approval queue + publishing API | Copy.ai's sales workflow automation is deeper |
| Buffer + AI | SaaS | Free–$15/month | Scheduling + AI rewrite assistant | Bilingual EN↔ES + autonomous generation | Buffer's scheduling is more robust |
| Lately.ai | SaaS | ~$49/month | Auto-repurpose long content → social posts | Autonomous multi-post generation | Lately.ai's repurposing is a direct feature gap |
| ContentStudio | SaaS | ~$25/month | Multi-platform scheduling + AI caption | Platform size/tone guidance | ContentStudio's analytics are stronger |

[VERIFIED pricing for Jasper, Copy.ai, Buffer — Zapier July 2025 + buffer.com official; Grade B for Jasper/Copy.ai, Grade A for Buffer]

### 2.1 Deep Dives

#### Jasper (jasper.ai)
- **What they do well:** Multiple brand voices, audience profiles, style guides, canvas collaboration
- **What they do poorly:** No autonomous pipeline; requires human workflow setup; no direct publishing API
- **Recent pivot:** Enterprise-focused marketing platform (2024–2025)
- **Threat level:** Low (different target user — teams, not solo creators)
- [VERIFIED — Zapier blog July 24, 2025, Grade B]

#### Copy.ai
- **What they do well:** Sales workflow automation, CRM connections, web scraping, lead scoring
- **What they do poorly:** Less focus on content quality; no image generation; basic brand voice
- **Recent pivot:** Go-to-market tool for sales teams (2024–2025)
- **Threat level:** Low (sales-focused, not content creation for personal brand)
- [VERIFIED — Zapier blog July 24, 2025, Grade B]

#### Buffer + AI Assistant
- **What they do well:** Scheduling, analytics, simple AI rewrites, free tier, easy onboarding
- **What they do poorly:** AI is a bolt-on, not native; no autonomous generation; no translation
- **Threat level:** Medium (closest to Holus in scheduling focus, but shallow AI)
- [VERIFIED — buffer.com, 2026, Grade A]

#### Lately.ai
- **What they do well:** Auto-repurpose long-form content → multiple social posts
- **What they do poorly:** No bilingual support; no approval queue; no pipeline to publishing API
- **Threat level:** Medium (repurposing is a direct feature overlap with Holus's content adaptation)
- [UNVERIFIED detailed feature set — limited sources reviewed]

#### ContentStudio
- **What they do well:** Multi-platform scheduling, analytics, team collaboration
- **What they do poorly:** AI is caption-level, not full content strategy
- **Threat level:** Low
- [UNVERIFIED detailed pricing — Seen $25/month reference in search snippets, not directly verified]

---

## 3. Holus Differentiation

Why Holus does what competitors can't:

1. **Autonomous end-to-end pipeline** — Holus runs weekly/daily without human setup. Competitors require manual workflow configuration. [VERIFIED — by absence in competitor feature sets, Grade B]

2. **Human-in-the-loop approval built-in** — LangGraph interrupt() gives Holus a native approval gate before publishing. Buffer/Jasper/Copy.ai have no equivalent autonomous-then-pause mechanism. [VERIFIED — LangGraph docs, Grade A]

3. **Bilingual EN↔ES in same pipeline** — Content is created, translated, and adapted in one unified Claude call chain. No competitor reviewed offers this as an integrated capability. [UNVERIFIED — inferred from competitor research]

4. **Platform-adapted content, not just scheduled** — Holus adapts tone, format, and character count per platform. Competitors schedule; Holus adapts first, then schedules. [UNVERIFIED — directional advantage, not benchmarked]

5. **Self-improvement loop** — Holus learns from analytics. Each cycle feeds back into MEMORY.md and trajectory.jsonl. No competitor offers a learning loop tied to your own audience data. [VERIFIED as a design property of Holus — not a competitor feature]

---

## 4. Positioning

**Holus is not a social media scheduling tool. It is a content brain.**

- Competitors are tools used by teams to produce content
- Holus is an autonomous agent that *is* the team for Juan's solo creator workflow
- The comparison is unfair: Jasper requires a marketing manager; Holus *replaces* the marketing manager for internal projects

**Target use case:** Juan spends zero time on content strategy, writing, or scheduling for Pilaster/Genpeli/Invoz. Holus handles the full cycle.

---

## 5. Weaknesses to Address

| Gap | Who Does It Better | Action |
|-----|-------------------|--------|
| Brand voice consistency | Jasper (style guides, compliance tools) | Implement products.yaml brand voice per product |
| Content analytics | ContentStudio | Leverage social-media-auto analytics API |
| Scheduling robustness | Buffer | Delegate scheduling to social-media-auto service |
| Content repurposing | Lately.ai | Add long-form → multi-post repurpose agent |

---

## Open Questions

- [ ] Does Lately.ai offer bilingual content? (direct competitor check needed)
- [ ] ContentStudio exact pricing — seen $25/month in snippet, needs direct verification
- [ ] Is there a competitor that connects content AI to a publishing API like social-media-auto? (2026 landscape check needed)

---

## Sources

1. Zapier, "Jasper vs. Copy.ai: Which is best?", https://zapier.com/blog/jasper-vs-copy-ai/ (July 24, 2025)
2. Buffer, "Pricing | Buffer", https://buffer.com/pricing (accessed 2026-03-04)
3. Buffer, "Social Media Scheduler & Planner for Everyone", https://buffer.com/publish (accessed 2026-03-04)
4. Futurepedia, "Buffer AI Reviews: Use Cases, Pricing & Alternatives", https://www.futurepedia.io/tool/buffer (2025)
5. SearchAtlas, "Copy.ai vs Jasper: Which Is Better for SEO? (2025 Comparison)", https://searchatlas.com/blog/copy-ai-vs-jasper/ (September 29, 2025)
