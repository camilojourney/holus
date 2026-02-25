# Holus Priority Queue

What to work on next. Ordered by priority. Updated by the manager agent (or human).

---

## P0 — Critical Path (This Week)

- [ ] Set up core infrastructure: Docker services running (Postgres, Redis, n8n, Temporal, Langfuse)
- [ ] Implement `src/holus/core/config.py` — settings loading from .env via pydantic-settings
- [ ] Implement `src/holus/core/kill_switch.py` — Redis-backed global and per-agent kill switch
- [ ] Implement `src/holus/core/event_bus.py` — Redis pub/sub + streams for inter-agent events
- [ ] Wire up `src/holus/__main__.py` — CLI entrypoint for starting agents

## P1 — High Priority (Weeks 2-3)

- [ ] Implement trading agent (paper mode) — signal generator + risk manager + execution handler
- [ ] Alpaca integration — paper trading client with guardrails
- [ ] Integrate Claude Code for coding agent — self-improvement cycle runner
- [ ] Set up Langfuse tracing for all LLM calls

## P2 — Medium Priority (Weeks 3-5)

- [ ] Build content pipeline — strategy planner + text generation + Late API distribution
- [ ] Build Pilaster agent — ComfyUI workflow optimization
- [ ] Implement Mem0 memory integration — per-agent scoped memory
- [ ] Build n8n webhook triggers for content and notification workflows

## P3 — Lower Priority (Month 2)

- [ ] Implement self-improvement loop — judge agent + prompt optimizer
- [ ] Build trajectory logging (`.self-improvement/memory/trajectory.jsonl`)
- [ ] Weekly improvement cycle automation

## P4 — Future (90+ Days)

- [ ] Build coordinator agent (requires all domain agents operational)
- [ ] Cross-project intelligence synthesis
- [ ] Paper-to-live trading graduation review

---

**Last updated:** 2026-02-24
**Updated by:** Human (initial setup)
