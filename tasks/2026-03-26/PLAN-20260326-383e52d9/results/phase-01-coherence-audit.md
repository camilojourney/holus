# Phase 1: Coherence Audit Results

**Clusters completed:** 33/41 (8 hit rate limits on sub-agents)
**Files audited:** ~115 of 130 Python files + 35 agent prompts + partial frontend

---

## VERDICT SUMMARY

### ORPHAN FILES (dead code — zero production callers)

| File | LOC | Why Dead |
|------|-----|----------|
| `core/resilience.py` | 175 | 3 primitives, zero callers. Duplicates `retry.py` |
| `core/retry.py` | 75 | Re-exported but never called. Duplicates `resilience.py` |
| `core/multi_tenant.py` | 191 | Single-user system, no tenants dir |
| `core/process_manager.py` | 249 | Complete supervisor, never wired |
| `core/quality_gate.py` | 202 | Superseded by `marketing/quality_score.py` |
| `agents/coding/agent.py` | 298 | Not in AGENTS.yaml, not imported |
| `agents/content/agent.py` | 285 | Superseded by marketing pipeline |
| `agents/coordinator/agent.py` | 281 | Phase 3 — not activated |
| `agents/pilaster/agent.py` | 313 | Not in AGENTS.yaml, not imported |
| `agents/marketing/platform_adapter.py` | 184 | Zero production callers |
| `agents/marketing/telegram_sender.py` | 129 | Zero callers, no callback handler |
| `agents/marketing/quality_compounding.py` | 260 | Zero imports anywhere |
| `agents/marketing/image_workflow.py` | 548 | Not called from agent/orchestrator |
| `agents/marketing/video_workflow.py` | 424 | Not called from agent/orchestrator |
| `agents/marketing/performance_loop.py` | 110 | Never instantiated |
| `integrations/comfyui/__init__.py` | 1 | Empty stub |
| `integrations/n8n/__init__.py` | 1 | Empty stub |
| `integrations/genpeli/client.py` | 226 | Zero importers in Python |
| `integrations/genpeli/__init__.py` | 21 | Zero importers |
| `integrations/pilaster/client.py` | 253 | Duplicate of inline client in image_workflow |
| `integrations/pilaster/__init__.py` | 21 | Zero importers |
| `memory/mem0_client.py` | 265 | Property exists but never accessed |
| `self_improvement/reflexion.py` | 421 | Exported but never invoked |
| `self_improvement/judge_calibration.py` | 202 | Never instantiated |
| `self_improvement/analytics.py` | 285 | 4 functions, none called |
| `self_improvement/dspy_bridge.py` | 248 | Only test imports it |
| `self_improvement/dspy_optimizer.py` | 145 | Never imported |
| `self_improvement/prompt_optimizer.py` | 333 | Exported but never called |
| `self_improvement/trajectory_db.py` | 179 | JSONL is sole production store |
| `observability/otel.py` | 227 | Zero integration points |
| `visual/gif_encoder.py` | 160 | Never called in production |
| `visual/infographic.py` | 297 | Tests only |
| `visual/infographic_layout.py` | 411 | Tests only |
| `visual/icon_registry.py` | 105 | Serves orphaned infographic |
| `api/routes/alerts.py` | 264 | No frontend consumer |
| `api/routes/config.py` | 89 | No frontend consumer + path bug |

**TOTAL ORPHAN LOC: ~7,424** (out of ~30,169 total = **24.6% dead code**)

---

## DUPLICATE PAIRS (consolidate or choose one)

1. **`resilience.py` vs `retry.py`** — two retry implementations, zero callers
2. **`bandit.py` vs `strategy_bandit.py`** — NOT duplicates (visual vs strategy). Keep both.
3. **`charts.py` vs `chart.py`** — NOT duplicates (carousel vs single-image). Rename for clarity.
4. **`dspy_bridge.py` vs `dspy_optimizer.py` vs `prompt_optimizer.py` vs `prompt_evolution.py`** — 4 files for prompt optimization. Only `prompt_evolution.py` has a production caller.
5. **`image_workflow.PilasterClient` vs `integrations/pilaster/client.py`** — two Pilaster clients with incompatible auth headers
6. **`video_workflow.GenpeliClient` vs `integrations/genpeli/client.py`** — two Genpeli clients

---

## CRITICAL COHERENCE ISSUES

### 1. JSON vs YAML Queue Mismatch
`idea_runner.py` writes **JSON** to `data/content-queue/`. `content_queue.py` reads **YAML**. These cannot interoperate.

### 2. Dual Pipeline Divergence
`agent.py` (ReAct loop) and `orchestrator.py` (cron pipeline) are two independent content generation paths that don't share generation code.

### 3. CORS GET-only Blocks PATCH
`app.py` CORS allows only GET, but `content.py` and `config.py` expose PATCH/PUT endpoints.

### 4. Evaluator Mismatch
All 5 written-authority agent prompts declare `evaluated_by: voice-guardian` but AGENTS.yaml routes them to `written-content-judge`.

### 5. Events Bus Unused by Marketing
`EventBus` is constructed every cycle but marketing agent never publishes events.

### 6. Observability 90% Dead
Langfuse traces are empty shells. OTEL is completely unwired.

### 7. Broken Feedback Loop
`performance_loop.py` (bandit reward update) has no caller — bandits never learn.

### 8. Two Parallel Specialist Architectures
`specialist_dispatch.py` routes to written-authority agents (decomposed pipeline). Content specialists (`idea-injector`, `context-builder`, `voice-writer`) form a separate monolithic pipeline. Both are "active" but serve different code paths.

---

## ACTIVE FILE COUNT BY MODULE

| Module | Active | Orphan | Total |
|--------|--------|--------|-------|
| core/ | 10 | 5 | 15 |
| agents/marketing/ | 22 | 6 | 28 |
| agents/other/ | 3 | 4 | 7 |
| api/ | 10 | 2 | 12 |
| integrations/ | 3 | 5 | 8 |
| memory/ | 4 | 1 | 5 |
| self_improvement/ | 5 | 7 | 12 |
| visual/ | 10 | 4 | 14 |
| observability/ | 1 | 1 | 2 |
| mcp/ | 1 | 0 | 1 |
| data/ | 2 | 0 | 2 |
| root/ | 5 | 0 | 5 |
| **TOTAL** | **76** | **35** | **111** |

---

## PARTIALLY DEAD (some methods orphaned)

- `observability/langfuse_client.py` — 5 of 6 functions dead (only `create_langfuse_client` used)
- `core/kill_switch.py` — `auto_trigger_on_loss` (trading concept), `auto_trigger_on_crash_count`, `check_kill_switch` decorator unused
- `core/events.py` — ~50% of EventType enum has no publishers
- `agents/marketing/humanize.py` — Layer 2 active, Layer 3 (`humanize_text`, `turing_test`) orphaned
- `agents/marketing/revision_loop.py` — 2 dead functions
- `self_improvement/gap_detector.py` — `classify_failure` dead
- `visual/engine.py` — `_combine_carousel_html` + `_extract_body` dead (~100 LOC)

---

## API ENDPOINT ORPHANS (8 of 16 in clusters 06-08)

| Endpoint | Route File | Reason |
|----------|-----------|--------|
| `GET /agents/{id}/metrics` | agents.py | No frontend caller |
| `GET /alerts` (entire file) | alerts.py | No frontend consumer |
| `GET/PUT /config/*` (entire file) | config.py | No frontend consumer |
| `GET /content/calendar` | content.py | No frontend caller |
| `GET /evaluations/summary` | evaluations.py | No frontend caller |
| `POST /api/holus/ingest` | ingest.py | CORS blocks POST + no caller |
| `GET /improvement/*` (5 endpoints) | improvement.py | No frontend pages wired |
| `POST /api/telegram/*` (5 endpoints) | telegram_gate.py | No webhook handler |
