# Holus System Memory

Accumulated knowledge from agent operations. Updated by agents after each cycle.
Human-readable summary of what the system has learned.

---

## Domain Knowledge

### Trading
- Paper trading only. Alpaca paper API at `https://paper-api.alpaca.markets`.
- Guardrails: 2% max per-trade, 25% max exposure, 5% weekly drawdown circuit breaker.
- Signal generator runs on Sonnet. Risk manager always runs on Opus.
- Graduation to live requires: 30+ days paper, 50+ trades, Sharpe > 1.0, max drawdown < 10%.

### Content
- Distribution via Late API to 13 platforms.
- Visual generation via ComfyUI (local) or Replicate (Flux Schnell).
- Strategy planning monthly on Opus, execution on Sonnet.

### Coding
- Self-improvement cycles run weekly (Sunday 2am).
- Target: increase test coverage, reduce lint warnings, update dependencies.
- All PRs require passing CI before merge.

### Pilaster
- ComfyUI workflow optimization for image generation quality.
- Quality gate: images must pass automated quality scoring before distribution.

---

## Lessons Learned

_No lessons yet. This section is populated after agents begin operating._

---

## Cross-Project Patterns

_No cross-project patterns yet. The coordinator agent will populate this after Phase 3 activation._

---

## System Incidents

_No incidents recorded yet._

---

**Last updated:** 2026-02-24
**Updated by:** Human (initial template)
