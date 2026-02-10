# HOLUS Strategy — The AI Content Company

> **Date:** 2026-02-10  
> **Author:** Strategy Session (3-Cycle Deep Think)  
> **Status:** Draft for Juan's Review

---

## 1. Executive Summary (The Pitch)

**Holus is an AI-powered content operations platform that turns one creator into a studio.**

The problem: Content creators and small media companies spend 80% of their time on operations — cutting clips, scheduling posts, managing outreach, translating content — instead of creating. Enterprise tools (Sprout Social, Descript, etc.) cost $500+/mo and still require manual glue work between them.

**Holus connects the full content lifecycle** — from ideation and guest research, through production and clip generation, to multi-platform distribution — orchestrated by AI agents that learn and improve autonomously.

**Value prop in one line:** *"Your AI production team that runs 24/7 for the cost of one freelancer."*

**Target customer (v1):** Bilingual (EN/ES) content creators and podcast producers doing $5K-50K/mo revenue, with 1-3 person teams, posting across 3+ platforms.

**Why now:** LLM costs dropped 90% in 2025. MCP protocol standardized tool connectivity. The creator economy is $250B but tooling is fragmented. First-mover on AI-orchestrated content ops.

---

## 2. Product Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        HOLUS HUB                             │
│              (Orchestrator + Manager Agent)                   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Scheduler│  │  Router  │  │  Agent   │  │ Dashboard│   │
│  │ (APSched)│  │ (Tasks)  │  │ Registry │  │ (Web UI) │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘   │
│       │              │              │                         │
├───────┼──────────────┼──────────────┼────────────────────────┤
│       │         MCP LAYER           │                        │
│  ┌────┴────────┬────┴────────┬─────┴──────┐                │
│  │             │             │             │                 │
│  ▼             ▼             ▼             ▼                 │
│ ┌───────────┐┌───────────┐┌───────────┐┌───────────┐       │
│ │  SOCIAL   ││  GENPELLI ││  REACHOUT ││  FUTURE   │       │
│ │  MEDIA    ││  (Content ││  (CRM +   ││  MODULES  │       │
│ │  AUTO     ││  Gen)     ││  Research)││           │       │
│ ├───────────┤├───────────┤├───────────┤├───────────┤       │
│ │• Notion   ││• Transcr. ││• Contacts ││• Trading  │       │
│ │• Claude AI││• Clip Cut ││• Pipeline ││• Email    │       │
│ │• DeepL    ││• DALL-E   ││• Outreach ││• Job Hunt │       │
│ │• IG/FB/X  ││• Carousel ││• Research ││• ...      │       │
│ │• GCP Cron ││• pgvector ││• SQLite   ││           │       │
│ └───────────┘└───────────┘└───────────┘└───────────┘       │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  SHARED INFRASTRUCTURE                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ LLM Pool │ │ Memory   │ │ Notifier │ │ Auth/    │      │
│  │ (multi-  │ │ (Chroma) │ │ (Telegram│ │ Billing) │      │
│  │  model)  │ │          │ │  /Email) │ │          │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└──────────────────────────────────────────────────────────────┘
```

### How Products Connect

| Flow | Path |
|------|------|
| Guest research → Interview → Content | Reachout → Genpelli → Social Media Auto |
| Long video → Clips → Multi-platform post | Genpelli → Social Media Auto |
| Trending topic → Script → Assets → Post | Holus Research Agent → Genpelli → Social Media Auto |
| Contact outreach → Schedule → Follow-up | Reachout → Holus Scheduler → Notifier |

---

## 3. Manager Agent Design

The Manager Agent is the brain of Holus. It doesn't do work — it **decides what work needs doing**.

### Architecture

```python
class ManagerAgent(BaseAgent):
    """
    Responsibilities:
    1. Monitor system health and agent performance
    2. Decide when to spawn/scale workers
    3. Create and modify cron schedules
    4. Research new capabilities
    5. Report to human (Juan) for approval gates
    """
    
    capabilities = [
        "spawn_agent",        # Create new agent instance
        "modify_schedule",    # Change cron timing
        "create_task",        # Add one-off task to queue
        "research_web",       # Search for new tools/APIs
        "analyze_metrics",    # Review agent performance
        "propose_improvement" # Suggest system changes (needs approval)
    ]
```

### Decision Loop (runs every 30 min)

```
1. OBSERVE  → Check agent run logs, error rates, queue depth
2. ANALYZE  → Are any agents failing? Is throughput low? New opportunities?
3. DECIDE   → What action to take (or nothing)
4. ACT      → Execute decision (spawn, reschedule, alert)
5. LEARN    → Store outcome in memory for future decisions
```

### Approval Gates (Critical)

The Manager Agent should **never** autonomously:
- Spend money (API calls above threshold)
- Send external communications
- Delete data
- Deploy to production

These require human approval via Telegram notification:
```
🤖 Manager Agent Proposal:
"Genpelli clip generation is failing 40% on videos >20min. 
I want to add a pre-processing step that splits long videos.
Estimated effort: 2 hours of agent work.
Approve? [Yes] [No] [Details]"
```

### Self-Improvement Cycle (Weekly)

```
Every Sunday 6am:
1. Aggregate week's metrics (success rates, processing times, errors)
2. Search web for new tools/APIs relevant to content creation
3. Compare current stack vs alternatives
4. Generate "Weekly Improvement Report" → send to Juan
5. If approved, create tasks for implementation
```

---

## 4. MCP (Model Context Protocol) Design

MCPs are the connective tissue. Each product exposes capabilities as MCP tools.

### Required MCPs

| MCP Server | Tools Exposed | Used By |
|------------|---------------|---------|
| `mcp-social-media` | `post_to_platform`, `get_scheduled_posts`, `enhance_text`, `translate` | Holus, Genpelli |
| `mcp-genpelli` | `transcribe_video`, `generate_clips`, `create_carousel`, `generate_asset` | Holus, Social Media |
| `mcp-reachout` | `search_contacts`, `create_outreach`, `get_pipeline`, `research_person` | Holus |
| `mcp-notion` | `read_content_db`, `create_entry`, `update_status` | All products |
| `mcp-holus-core` | `spawn_agent`, `get_status`, `create_schedule`, `get_metrics` | Manager Agent |

### Implementation Priority
1. **mcp-social-media** (already has API, just wrap it)
2. **mcp-genpelli** (core value, needs transcription + clip tools)
3. **mcp-reachout** (already has REST API)
4. **mcp-notion** (shared CMS)
5. **mcp-holus-core** (orchestration)

---

## 5. Cron/Automation Recommendations

### Tier 1 — Already Working (Keep)
| Cron | Schedule | Product |
|------|----------|---------|
| Daily content post | 9am/1pm/6pm ET | Social Media Auto |
| Notion content sync | Every 2 hours | Social Media Auto |

### Tier 2 — Build Next (High Impact)
| Cron | Schedule | Product |
|------|----------|---------|
| Manager health check | Every 30 min | Holus |
| Clip generation pipeline | On new video upload | Genpelli |
| Outreach follow-up reminders | Daily 10am | Reachout |
| Weekly improvement report | Sunday 6am | Holus Manager |
| Trending topic scan | Every 4 hours | Holus Research |

### Tier 3 — Future
| Cron | Schedule | Product |
|------|----------|---------|
| Auto-thumbnail generation | On new content | Genpelli |
| Guest research automation | On new contact added | Reachout |
| Cross-platform analytics | Daily midnight | Holus Dashboard |
| Self-healing (restart failed agents) | Every 5 min | Holus Core |

---

## 6. Business Model Options

### Option A: Vertical SaaS (Recommended for v1)

**"Holus for Creators"** — sell the unified platform as a subscription.

| Tier | Price | Includes |
|------|-------|----------|
| **Starter** | $49/mo | Social Media Auto (3 platforms, 30 posts/mo) |
| **Creator** | $149/mo | + Genpelli (10 videos/mo, clip gen) |
| **Studio** | $399/mo | + Reachout + unlimited + priority |
| **Enterprise** | Custom | White-label, API access, custom agents |

**Pros:** Recurring revenue, clear upgrade path, sticky (data lock-in)  
**Cons:** Needs polish for self-serve, support burden

### Option B: Modular Products (Individual Sales)

Sell each product standalone:
- **Social Media Auto** → $29-79/mo (competes with Buffer/Hootsuite)
- **Genpelli** → $49-199/mo (competes with Opus Clip, Descript)
- **Reachout** → $19-49/mo (competes with Hunter.io, Lemlist)
- **Holus Bundle** → 30% discount on combined

**Pros:** Wider market, each product can stand alone  
**Cons:** More products to maintain, slower to build moat

### Option C: Agency + Software (Bootstrap Revenue)

Use the tools yourself as an agency, then productize.

1. **Now:** Offer content management services using your stack ($2-5K/mo per client)
2. **3 months:** Onboard 3-5 clients, refine the tools
3. **6 months:** Launch self-serve platform with proven workflows
4. **12 months:** Transition from agency to SaaS

**Pros:** Revenue from day 1, customer feedback, proven before building  
**Cons:** Agency work is time-consuming, harder to scale

### Recommendation: **Option C → Option A**

Start as a productized agency (immediate revenue + validation), then transition to SaaS. The bilingual EN/ES angle is a real differentiator — the Latin American creator market is underserved by existing tools.

---

## 7. Competitive Landscape

| Competitor | What They Do | Holus Advantage |
|------------|-------------|-----------------|
| **Buffer/Hootsuite** | Social scheduling | AI enhancement, auto-translation, video gen |
| **Opus Clip** | AI video clipping | Integrated with posting pipeline, not standalone |
| **Descript** | Video editing | Automated end-to-end, not editing tool |
| **Repurpose.io** | Cross-platform repost | AI-generated variants, not just reposts |
| **Jasper** | AI content writing | Full pipeline (write → produce → post → analyze) |
| **Lemlist** | Outreach automation | Integrated with content workflow |

**Moat:** No one connects research → production → distribution → outreach in one AI-orchestrated system. Competitors are point solutions. Holus is the **operating system for content businesses**.

---

## 8. 90-Day Roadmap

### Month 1: Foundation (Days 1-30)
- [ ] **Week 1-2:** MCP wrappers for Social Media Auto (it already works)
- [ ] **Week 2-3:** Genpelli semantic clip cutting (core differentiator)
- [ ] **Week 3-4:** Manager Agent v1 (health checks, basic scheduling)
- [ ] **Week 4:** Dashboard v1 (status page, agent logs)
- [ ] Land 1 paying agency client using existing tools

### Month 2: Integration (Days 31-60)
- [ ] Connect Genpelli → Social Media Auto pipeline (video in → posts out)
- [ ] Reachout → research automation (auto-research guests)
- [ ] MCP for Genpelli and Reachout
- [ ] Manager Agent self-improvement cycle v1
- [ ] Land 2 more agency clients

### Month 3: Polish & Package (Days 61-90)
- [ ] Unified onboarding flow
- [ ] Billing/auth system
- [ ] Documentation and demo videos
- [ ] Beta launch landing page
- [ ] Pitch deck for potential investors/advisors
- [ ] 5 paying clients target

---

## 9. Immediate Tasks (For Juan to Approve)

### Priority 1 — This Week
| # | Task | Product | Est. |
|---|------|---------|------|
| 1 | Build MCP server wrapper for Social Media Auto API | Social Media | 4h |
| 2 | Implement semantic clip cutting in Genpelli (whisper timestamps + LLM scoring) | Genpelli | 8h |
| 3 | Create Manager Agent skeleton (extends BaseAgent, 30-min health loop) | Holus | 4h |
| 4 | Set up holus dashboard with agent status view | Holus | 4h |

### Priority 2 — Next 2 Weeks
| # | Task | Product | Est. |
|---|------|---------|------|
| 5 | Genpelli MCP server (transcribe + clip tools) | Genpelli | 4h |
| 6 | Connect Genpelli output → Social Media Auto input | Integration | 4h |
| 7 | Reachout: add "research person" feature (web search + summarize) | Reachout | 6h |
| 8 | Manager Agent: web research capability (weekly tech scan) | Holus | 4h |
| 9 | Landing page for Holus (even simple, for credibility) | Marketing | 4h |

### Priority 3 — Month 1
| # | Task | Product | Est. |
|---|------|---------|------|
| 10 | Autonomous cron creation by Manager Agent | Holus | 8h |
| 11 | Multi-tenant support (for agency clients) | All | 12h |
| 12 | Analytics dashboard (cross-platform post performance) | Holus | 8h |
| 13 | Reachout → Genpelli thumbnail generation | Integration | 4h |

---

## 10. What Makes This Sellable

### As a Company (Acquisition Target)
- **Proprietary data pipeline:** Bilingual content optimization data
- **Agent orchestration IP:** Self-improving agent workforce is novel
- **Recurring revenue:** SaaS subscriptions
- **Network effects:** More creators → better AI models → better content
- **Acquirers:** Sprout Social, HubSpot, Canva, any media tech company

### Valuation Drivers
- ARR (annual recurring revenue) — target $100K ARR in 12 months
- User retention and engagement metrics
- Unique technology (agent orchestration + MCP integration)
- Bilingual market positioning (EN/ES is massive and underserved)

### The Big Bet
The creator economy needs its **"Shopify moment"** — a platform that handles the entire back-office so creators can focus on creating. Holus is positioning to be that platform, starting with the content production pipeline and expanding to business management.

---

## Summary

```
TODAY:  3 separate tools + an orchestrator skeleton
       ↓
30 DAYS: Connected pipeline, Manager Agent live, 1 client
       ↓  
90 DAYS: 5 paying clients, self-improving system, beta launch
       ↓
12 MO:  SaaS platform, $100K ARR, sellable company
```

**The key insight:** You already have the hardest part — working products. Now it's about connection, packaging, and selling. The Manager Agent makes it defensible. The MCP layer makes it extensible. The bilingual angle makes it differentiated.

Build the bridge between your products. Sell the bridge. That's Holus.
