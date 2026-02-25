# Directory Structure Rules

## Source Code Layout
```
src/holus/
├── core/              ← Shared infrastructure (config, events, kill switch)
├── agents/            ← One package per domain agent
│   ├── base.py        ← Abstract base class all agents inherit
│   ├── trading/       ← Trading agent (LangGraph + Temporal)
│   ├── content/       ← Content pipeline agent
│   ├── coding/        ← Claude Code integration agent
│   ├── pilaster/      ← ComfyUI workflow agent
│   └── coordinator/   ← Cross-project coordinator (Phase 3)
├── integrations/      ← One package per external service
│   ├── claude_api/    ← Anthropic API client with caching
│   ├── alpaca/        ← Alpaca trading API
│   ├── n8n/           ← n8n webhook triggers
│   ├── comfyui/       ← ComfyUI JSON API
│   └── late_api/      ← Late API content distribution
├── memory/            ← Mem0 + pgvector + trajectory logging
├── observability/     ← Langfuse tracing + metrics
└── self_improvement/  ← Judge, Prompt Optimizer, Reflexion
```

## Where New Code Goes

| Type of code | Location | Example |
|---|---|---|
| New agent | `src/holus/agents/{name}/` | `agents/research/agent.py` |
| External API client | `src/holus/integrations/{service}/` | `integrations/stripe/client.py` |
| Shared utility | `src/holus/core/` | `core/rate_limiter.py` |
| Data model | Same package as its consumer | `agents/trading/models.py` |
| Test | `tests/unit/{package}/test_{module}.py` | `tests/unit/core/test_config.py` |

## File Naming
- Python modules: `snake_case.py`
- Config files: `kebab-case.yaml` or `snake_case.yaml`
- Specs: `NNN-feature-name.md` (zero-padded 3 digits)
- ADRs: `NNNN-decision-name.md` (zero-padded 4 digits)
- Reports: `YYYY-MM-DD.md`

## What Goes Where (Non-Code)
| Content | Location |
|---|---|
| Feature specs | `specs/NNN-name.md` |
| Architecture decisions | `docs/decisions/NNNN-name.md` |
| Operational guides | `docs/playbooks/` |
| Worker configs | `.self-improvement/workers.yaml` |
| Agent reports | `.self-improvement/reports/{agent}/` |
| Run logs | `.self-improvement/memory/trajectory*.jsonl` |
| Dev journal | `devlog/YYYY-MM-DD.md` |
| Session tasks | `tasks/` (temporary, delete when done) |
