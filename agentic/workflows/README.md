# Holus - Content Workflows

One workflow per platform. Each workflow is a complete spec:
input → agents → output → evaluation → post → learn.

## Status

| Platform | Workflow | Status |
|----------|----------|--------|
| LinkedIn | [linkedin.md](linkedin.md) | 🟡 Spec written - not built |
| Instagram | instagram.md | ⬜ Not started |
| Twitter/X | twitter.md | ⬜ Not started |
| Threads | threads.md | ⬜ Not started |
| Facebook | facebook.md | ⬜ Not started |

## Rule

**One platform at a time. Make it right before moving to the next.**

LinkedIn ships first. Everything else waits until LinkedIn is producing
3 posts/week consistently with measurable engagement growth.

## Shared Infrastructure

All workflows share:
- `brand.yaml` - voice, anti-patterns, positioning
- `brand-visual.yaml` - visual identity
- `config/products.yaml` - product proof points
- `agentic/agents/AGENTS.yaml` - agent registry
- `self_improvement/` - evaluation + learning loop
- Multi-armed bandit - visual diversity algorithm (shared across platforms)
