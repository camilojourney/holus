# HOLUS APPROACH v1 — Manager & Worker System
*Created: 2026-02-10*
*Status: Active — will iterate based on results*

---

## Overview

An autonomous AI company that builds, researches, and improves itself.

```
┌─────────────────────────────────────────────────────────────┐
│                    HOLUS COMPANY                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐                                           │
│   │   MANAGER   │  Opus 4.6 — The Brain                     │
│   │   (PM)      │  Assigns tasks, QA, strategy              │
│   └──────┬──────┘                                           │
│          │                                                   │
│          │ assigns specs                                     │
│          ▼                                                   │
│   ┌─────────────┐                                           │
│   │  BUILDERS   │  Grok — The Hands                         │
│   │  (Workers)  │  Execute tasks, write code                │
│   └──────┬──────┘                                           │
│          │                                                   │
│          │ reports done                                      │
│          ▼                                                   │
│   ┌─────────────┐                                           │
│   │     QA      │  Haiku — The Eyes                         │
│   │ (Validator) │  Checks output, approves/rejects          │
│   └─────────────┘                                           │
│                                                              │
│   ┌─────────────┐                                           │
│   │ RESEARCHER  │  Grok + Perplexity — The Ears             │
│   │   (Scout)   │  Scans trends, competitors, tech          │
│   └─────────────┘                                           │
│                                                              │
│   ┌─────────────┐                                           │
│   │ CHALLENGER  │  Haiku/Opus — The Critic                  │
│   │ (Strategist)│  "Are we building the right thing?"       │
│   └─────────────┘                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Roles & Models

| Role | Model | Cost | Responsibility |
|------|-------|------|----------------|
| **Manager** | Opus 4.6 | included | Assigns tasks, writes specs, QA, retros |
| **Midday Manager** | Opus 4.5 | included | Operational check-ins |
| **Builder** | Grok | $0.20/M | Executes specs, writes code |
| **QA** | Haiku | included | Validates output |
| **Researcher** | Grok + Perplexity | $0.20/M | Scans external trends |
| **Challenger** | Haiku (daily) / Opus 4.6 (weekly) | included | Strategy questions |

---

## Daily Rhythm

| Time | Who | What |
|------|-----|------|
| 8:00 AM | Manager (Opus 4.6) | Assign 3 tasks for the day |
| 8:00-12:00 | Builder (Grok) | Execute task #1 |
| 12:00 PM | Manager (Opus 4.5) | QA task #1, assign task #2 |
| 12:00-4:00 | Builder (Grok) | Execute task #2 |
| 4:00-6:00 | Builder (Grok) | Execute task #3 |
| 6:00 PM | Manager (Opus 4.6) | Evening retro, log learnings |
| 7:00 PM | Challenger (Haiku) | "Did today move the needle?" |

---

## Weekly Rhythm

| Day | What |
|-----|------|
| Mon/Wed/Fri 9am | Trend Scanner (deep research) |
| Every 4 hours | Alert Scanner (quick checks) |
| Sunday 10am | Weekly Strategy Review (PERSIST/PIVOT/KILL) |
| Sunday 10am | Model Evaluation (test better models) |

---

## Repos Under Management

```
~/.openclaw/workspace/github/
├── holus/                       ← Orchestrator
├── social-media-automatization/ ← Multi-platform posting
├── content_ai_generation/       ← Genpelli (video→clips)
├── reachout/                    ← Outreach/CRM
└── invoz/                       ← Voice coaching
```

---

## Task Flow

```
BACKLOG.md
    │
    ▼
Manager picks top 3 tasks
    │
    ▼
Manager writes detailed specs
    │
    ▼
Builder executes spec
    │
    ▼
Manager QAs output
    │
    ├─► PASS → Mark done, log learnings
    │
    └─► FAIL → Send back with feedback
    │
    ▼
Evening retro: what shipped, what learned
    │
    ▼
Update backlog for tomorrow
```

---

## Feedback Loops

### Per-Task (immediate)
- Builder logs what was built
- QA checks against acceptance criteria
- Results saved to build logs

### Daily (6pm retro)
- Acknowledge what shipped
- Analyze what blocked
- Calculate velocity
- Plan tomorrow

### Weekly (Sunday review)
- Score each product (demand, timing, moat)
- PERSIST / PIVOT / KILL decisions
- Evaluate model performance
- Research better approaches

---

## Research Approach

### Sources (Quality > Quantity)
- **arXiv** — academic papers
- **Official blogs** — OpenAI, Anthropic, Google
- **Tech news** — TechCrunch, The Verge, Wired
- **Perplexity** — synthesized answers with citations

### What We Track
- AI agent developments
- Video AI updates (Runway, Sora, etc.)
- Competitor moves (Opus Clip, Descript)
- Creator economy trends
- MCP protocol updates

---

## Self-Optimization

### The System Can:
- ✅ Update model choices if better found
- ✅ Add new tasks to backlog
- ✅ Modify cron schedules
- ✅ Research new tools/APIs
- ✅ Propose pivots (needs human approval)

### The System Cannot:
- ❌ Spend money above threshold
- ❌ Send external communications
- ❌ Delete data
- ❌ Deploy to production (without approval)

---

## Invoz Integration

Invoz uses hybrid analysis:
- **LLM (Gemini)** — subjective assessment, feedback
- **Audio tools (librosa, wav2vec2)** — precise metrics

### 7 Pillars Tracked
1. Intelligibility
2. Fluency
3. Prosody
4. Vocal Variety
5. Articulation
6. Naturalness
7. Confidence

### Metrics Tracked
- Speaking rate (WPM)
- Pitch (Hz)
- Volume (dB)
- Intonation patterns
- Phoneme errors

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2026-02-10 | Initial approach — Manager/Worker system |

---

## Next Iteration Ideas

*To be filled based on week 1 results:*
- [ ] Faster loops?
- [ ] Different model assignments?
- [ ] More/fewer crons?
- [ ] Different task sizes?

---

*This document will evolve. Sunday reviews update it.*
