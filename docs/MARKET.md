# Market — Holus

**Last updated:** 2026-02

---

## The Problem

Solo founders cannot scale beyond their own hours. Hiring is expensive, slow, and introduces management overhead that defeats the purpose of being solo. The alternative — dozens of disconnected automations, cron jobs, and scripts — creates a maintenance burden that grows faster than the value it produces.

Marketing across a portfolio of products is especially painful: each product needs different content, different audiences, different platforms, and constant attention to what's working. A solo founder managing 5+ products can't do justice to any of them.

## Why Now

1. **AI agent frameworks are mature** — LangGraph, CrewAI, AutoGen provide production-grade agent orchestration. MCP protocol enables cross-tool communication.
2. **Cloud AI API quality** — Claude Opus 4 handles genuine strategic reasoning. Not chat — real decision-making about content strategy.
3. **Creator-as-operator** — solo founders increasingly run their entire business through AI assistants. The tools exist; the orchestration layer is missing.
4. **Cross-product intelligence** — a system that learns from content performance across multiple products can identify patterns no single-product tool would find.

## Category

AI marketing strategist agent — federated multi-agent system that promotes a product portfolio through coordinated autonomous agents.

## What Holus Is

An AI marketing strategist that:
- **Observes** — reads analytics from social-media-automatization
- **Reasons** — decides what content to create and where to publish
- **Acts** — calls genpeli (video), pilaster (images), social-media (publishing) via MCP
- **Learns** — logs decisions and outcomes, improves strategy over time

**What Holus is NOT:** a unified codebase replacing individual repos, a trading system, a content publisher, or a video generator. Those are silos. Holus uses them as tools.

## Target User

The portfolio owner (Camilo Martinez) — a solo founder with 5+ products who needs autonomous marketing that learns and improves. Not a SaaS product.

## The Products Holus Promotes

| Product | Audience | Platforms |
|---------|----------|-----------|
| Pilaster | AI artists, ComfyUI users | LinkedIn, TikTok, YouTube Shorts |
| Genpeli | Content creators, video editors | LinkedIn, Instagram |
| Invoz | Developers | LinkedIn, Twitter |

## Competitive Landscape

| Tool | Approach | Weakness |
|------|----------|----------|
| **Buffer/Hootsuite** | Scheduling only | No strategy, no AI, no cross-product |
| **Jasper AI** | Content generation | No publishing, no strategy, single-product |
| **HubSpot** | Full marketing suite | Enterprise pricing, no AI agent loop |
| **Custom GPT workflows** | Prompt chains | No persistence, no learning, no tool integration |
| **n8n / Zapier** | Workflow automation | No strategic reasoning, rule-based only |
| **AutoGPT / AgentGPT** | General-purpose agents | Not specialized for marketing, unreliable |

**No tool combines strategic AI reasoning + cross-product marketing + tool orchestration (MCP) + learning loops.**

## Business Model

### Phase 1 — Personal Infrastructure (Current)
- Runs as a cron-triggered agent on Mac Mini
- No revenue — internal marketing automation
- Cost: ~$50/month in API calls (Claude Opus + Sonnet)

### Phase 2 — Measurable Value
- Track: content published, engagement rates, audience growth, lead generation
- Goal: demonstrate that Holus-generated content outperforms manual posting
- Value metric: hours saved × consulting rate = internal ROI

### Phase 3 — Potential Productization
- "AI marketing strategist for multi-product founders"
- Extremely niche market — may be better as open-source reputation play

## Architecture

### Silo Model (Federated)
```
                    HOLUS
              (marketing brain)
                      |
      ┌───────────────┼───────────────┐
      ▼               ▼               ▼
genpeli-mcp    social-media-mcp   pilaster-mcp
(make videos)  (post + analytics) (make images)
```

- Holus holds the BRAIN (strategy, decisions, learning)
- The silos hold the HANDS (execution, data, publishing)
- Data never flows back into Holus permanently
- Holus reads silo data to make decisions; source of truth stays in the silo

### Agent Loop (ReAct)
1. **OBSERVE** — get analytics, read product updates, recall learnings
2. **REASON** — strategic decisions (Claude Opus)
3. **ACT** — call MCP tools (generate image, create video, schedule post)
4. **EVALUATE** — log decisions, write weekly report

## Growth Strategy

1. **Prove the loop works** — automated content creation → measurable engagement
2. **Expand product coverage** — add consulting, job-tracker to the promotion matrix
3. **Self-improvement cycle** — analytics → pattern recognition → strategy refinement
4. **Open source the architecture** — "how to build a federated AI marketing agent" content

## Moats

1. **Cross-product learning** — patterns emerge across multiple products that single-product tools miss
2. **MCP integration depth** — deep tool orchestration with existing repos
3. **Cumulative intelligence** — strategy improves with every cycle's data
4. **Architecture precedent** — federated agent design is the correct pattern for multi-domain AI

## Kill Criteria

- Content quality too low for publishing (requires heavy human editing)
- No measurable engagement improvement over 3 months
- MCP tool reliability too low for autonomous operation
- API costs exceed value generated
