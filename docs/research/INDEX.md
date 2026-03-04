---
last_updated: 2026-03-04
owner: juan
---

# Research Index — Holus

Last updated: 2026-03-04

## Status Tracker

| File | Scope | Updated | Cadence | Next Review | Status |
|------|-------|---------|---------|-------------|--------|
| [stack.md](stack.md) | LLM models, frameworks, translation engines | 2026-03-04 | 30d | 2026-04-03 | Fresh |
| [market.md](market.md) | Competitors, pricing, positioning | 2026-03-04 | 60d | 2026-05-03 | Fresh |
| [architecture.md](architecture.md) | Agent orchestration, approval workflows | 2026-03-04 | 90d | 2026-06-02 | Fresh |
| [domain.md](domain.md) | Content marketing, bilingual strategy, platform rules | 2026-03-04 | 60d | 2026-05-03 | Fresh |

Status legend: **Fresh** (within cadence) | **Stale** (past cadence) | **Critical** (past 2× cadence)

---

## File Summaries

- **stack.md** — Which LLM models to use for each agent role, Claude API pricing, LangGraph framework overview, translation engine comparison (LLMs vs DeepL vs Google Translate).
- **market.md** — Competitor matrix (Jasper, Copy.ai, Buffer AI, Lately.ai, ContentStudio), pricing breakdown, Holus positioning, key differentiation.
- **architecture.md** — LangGraph multi-agent patterns (supervisor vs swarm), human-in-the-loop implementation, approval queue design, content generation pipeline.
- **domain.md** — Platform-specific content rules (character limits, tone by platform), bilingual content strategy (EN↔ES), content marketing fundamentals.

---

## How to Use This Research

1. Before writing a spec: read the relevant research files
2. Every claim in a spec must cite a research section: `(research/stack.md §2.1)`
3. If research doesn't cover what you need: update research first, then write the spec
4. After research update: check all dependent specs for stale claims

---

## Open Questions (Across All Files)

- [ ] Does Jasper or Copy.ai offer a native human-in-the-loop approval queue? (needs direct product research)
- [ ] What is Claude Sonnet 4's actual creative writing quality vs Opus 4 in a bilingual marketing context? (needs own benchmarking)
- [ ] Is there any competitor that does EN↔ES automated content with platform adaptation? (needs targeted competitor research)
- [ ] What engagement delta is attributable to bilingual vs English-only posting for a bilingual audience? (domain research gap)
