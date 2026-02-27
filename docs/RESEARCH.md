# Research — Holus

**Last updated:** 2026-02

---

## 1. Federated Agent Architecture

### Design Principle
Process-isolated federation: agents operate independently so a crash in one never affects another. A shared event bus and lightweight Coordinator synthesize cross-project intelligence.

Every production multi-agent system studied (Replit, Vercel, Cognition/Devin, Anthropic) converges on this pattern: independent agents with bounded communication channels.

### Why Federated Over Unified
| Aspect | Unified | Federated (Holus) |
|--------|---------|-------------------|
| Failure blast radius | One crash affects all | Isolated per silo |
| Complexity growth | Quadratic (N×N interactions) | Linear (N silos + coordinator) |
| Debugging | Tangled state | Each silo independently testable |
| Deployment | All-or-nothing | Independent silo updates |
| Data ownership | Central database | Each silo owns its data |

### Silo Communication
Holus communicates with silos via MCP (Model Context Protocol) tool calls:

```python
# genpeli
genpeli.create_video(brief, style, voice) → VideoResult
genpeli.get_job_status(job_id) → JobStatus

# social-media-automatization
social_media.schedule_post(content, platforms, scheduled_at) → PostResult
social_media.get_analytics(days, platform) → AnalyticsReport
social_media.get_top_posts(limit, metric) → List[Post]

# pilaster
pilaster.generate_image(brief, workflow_id) → ImageResult
pilaster.get_best_workflow(style) → WorkflowRecommendation
```

## 2. ReAct Agent Loop

### Episodic Execution
Holus runs as an episodic agent — triggered weekly by cron or manually via Telegram. Not a long-running daemon.

### Loop Phases
```
OBSERVE
  → social-media-mcp: get_analytics(last_7_days)
  → config/products.yaml: what's new in each product?
  → .self-improvement/MEMORY.md: what have we learned?

REASON (Claude Opus — strategy decisions)
  → "Tutorial posts outperform promo posts 4:1"
  → "Pilaster shipped workflow diff — good tutorial topic"
  → "LinkedIn performing better than Instagram for this audience"

ACT
  → pilaster-mcp: generate_image(brief)
  → genpeli-mcp: create_video(brief, images, voice)
  → social-media-mcp: schedule_post(video, platforms)

EVALUATE
  → log decisions + reasoning → trajectory.jsonl
  → write weekly report
```

## 3. Model Strategy

### Intelligence-First Principle
Intelligence is the primary constraint, not cost. Every agent runs on the highest-capability model available.

| Task | Model | Why |
|------|-------|-----|
| Strategy decisions | Claude Opus 4 | Requires genuine reasoning about content strategy |
| Content generation | Claude Sonnet 4.5 | High-volume, good quality, faster |
| Weekly deep analysis | Claude Opus 4 | Comprehensive pattern recognition |
| Daily health check | Claude haiku | Simple monitoring, cost-efficient |

### Cost Model
- Target: <$500/month for full intelligence-forward operation
- Opus for strategy (~$200/month at weekly cadence)
- Sonnet for content (~$100/month)
- Haiku for monitoring (~$20/month)
- Remaining budget: Replicate (images), R2 (storage)

## 4. Self-Improvement System

### Memory Architecture
```
.self-improvement/
├── MEMORY.md           ← learned patterns, updated after each cycle
├── NEXT.md             ← agent priorities
├── memory/
│   └── trajectory.jsonl  ← decision log (what was decided, why, outcome)
└── reports/
    └── marketing/
        └── YYYY-MM-DD.md  ← weekly performance reports
```

### Learning Loop
1. Each cycle's decisions and reasoning are logged
2. Analytics from previous cycle's content are observed
3. Patterns extracted: "tutorial posts outperform promo posts"
4. Future decisions weighted by historical performance
5. Weekly report summarizes learnings for human review

### DSPy Prompt Optimization (Phase 3)
- Monthly optimization cycle
- Test current prompts against historical outcomes
- Optimize for engagement metrics
- 15–30% accuracy improvement per cycle (target)

## 5. Product Configuration

### products.yaml
```yaml
products:
  pilaster:
    audience: "AI artists, ComfyUI users"
    platforms: ["linkedin", "tiktok", "youtube_shorts"]
    content_types: ["tutorial", "before_after", "tips"]
  genpeli:
    audience: "Content creators, video editors"
    platforms: ["linkedin", "instagram"]
    content_types: ["demo", "tutorial", "case_study"]
  invoz:
    audience: "Developers"
    platforms: ["linkedin", "twitter"]
    content_types: ["technical_post", "demo"]
```

### Content Calendar Logic
- Each product gets content proportional to: launch recency + feature velocity + engagement history
- New features trigger immediate content ("Pilaster shipped workflow diffing")
- Evergreen content scheduled during quiet weeks

## 6. Infrastructure

### Core Stack
| Component | Role |
|-----------|------|
| Mac Mini | Runs cron jobs, hosts local services |
| Docker Compose | PostgreSQL, Redis, n8n (workflow automation) |
| Claude API | All agent reasoning (with prompt caching) |
| MCP Protocol | Tool communication with silos |
| Telegram | Manual triggers, daily reports, alerts |

### Kill Switch System
Global pause mechanism for when something goes wrong:
- CLI trigger
- SSH trigger
- Webhook trigger
- Tested from all three paths before production use

### Circuit Breakers
Per-agent error rate monitoring:
- >5% error rate → agent pauses, notifies human
- Automatic restart after cooldown
- Recovery time target: <5 minutes

## 7. Finance Agent (Phase 1.5)

Simple weekly report (not LangGraph, just a Python script):
1. Read Stripe for revenue (Pilaster credits sold)
2. Read Anthropic + Replicate usage for costs
3. Calculate net P&L
4. Send report to Telegram

## 8. Key Technical Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Architecture | Federated (silos + coordinator) | Failure isolation, independent scaling |
| Communication | MCP protocol | Standard, tool-based, async-friendly |
| Strategy model | Claude Opus 4 | Best reasoning for strategic decisions |
| Orchestration | Episodic (weekly cron) | Simpler than real-time, sufficient cadence |
| State | File-based (.self-improvement/) | Inspectable, debuggable, no database needed |
| LLM providers | Claude-only | One provider = one prompt format, one cache, one failure mode |

## 9. What Is NOT In Holus

- **Trading** — pythia and milo-to-the-moon are completely isolated
- **Publishing logic** — social-media-automatization handles posting
- **Video rendering** — genpeli handles ffmpeg, whisper, captions
- **Image generation** — pilaster handles ComfyUI, Replicate
- **Code review** — each repo has its own CI and review process
