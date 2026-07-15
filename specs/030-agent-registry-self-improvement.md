# Spec 030: Agent Registry & Self-Improvement Wiring

**Status:** planned
**Phase:** Phase 2
**Author:** Juan
**Created:** 2026-03-12
**Updated:** 2026-03-12

## Problem

The self-improvement machinery exists (`judge.py`, `learning_loop.py`, `reflexion.py`, `prompt_optimizer.py`) but none of it runs in production. Agents define their system prompts as hardcoded Python strings and have no way to receive improved prompts. There is no programmatic view of the agent fleet — you have to read `AGENTS.yaml` by hand. And Langfuse tracing exists as a lazy property on `BaseAgent` but is never called during `run()`, so there is zero observability on what agents actually cost or how long they take.

The result: we are generating content with agents we cannot observe, cannot evaluate systematically, and cannot improve. That defeats the point of having a self-improvement system at all.

## Goals

- `AgentRegistry.list_agents()` returns all 32 agents from `AGENTS.yaml` without hardcoding anything
- Agent prompt files (`.md`) are the single source of truth; Python strings are the fallback, not the default
- Every agent evaluation is routed to the correct domain-expert judge (not the generic judge) based on content type
- `BaseAgent.run()` creates a Langfuse trace automatically when `LANGFUSE_PUBLIC_KEY` is set — zero opt-in required
- `BaseAgent._evaluate_self()` is called after every `run()` and stores the result in trajectory metadata
- `just evaluate` and `just costs` work as documented in `justfile`
- All 606 existing tests keep passing after this change

## Non-Goals

- DSPy integration — DSPy optimizes prompts automatically but requires 30+ labeled examples first. We do not have that data yet.
- Automated prompt promotion — the prompt optimizer exists but should not auto-promote variants without human review. That comes in Phase 3.
- Moving `self_improvement/` Python files — they live where they live. This spec wires them in, not reorganizes them.
- A UI for the registry — the registry is a Python API, not a dashboard.

## Solution

Four loosely-coupled additions to the existing codebase:

```
agentic/agents/AGENTS.yaml
      │
      ▼
AgentRegistry          ← reads YAML, returns AgentInfo objects
      │
      ├── get_agent_prompt(id) ──► PromptLoader
      │                                 │
      │             ┌──────────────────┐│
      │             │ 1. config/prompts/││ optimizer variant
      │             │ 2. agents/{role}/ ││ .md file (default)
      │             │ 3. Python string  ││ hardcoded fallback
      │             └──────────────────┘│
      │
      └── get_evaluator_for(content_type) ──► EVALUATOR_ROUTING dict

BaseAgent.run()
      │
      ├── [before] check_kill_switch()
      ├── [during] Langfuse trace wraps app.ainvoke()
      ├── [after]  _evaluate_self() → JudgeAgent → trajectory entry
      └── returns final_state
```

The `AgentRegistry` is stateless and cheap — it reads the YAML at import time (or lazily, once). `PromptLoader` checks three locations in order; the first hit wins. The evaluator routing is a plain dict — no database, no service, just `EVALUATOR_ROUTING[content_type]`.

### Prompt Resolution (three layers)

```
Layer 1 — optimizer variant
  config/prompts/{agent_id}/current.md
  (written by prompt_optimizer.py when a variant graduates)

Layer 2 — canonical .md file (default)
  agents/{role}/{agent_id}.md
  (written by humans, follows KERNEL template)

Layer 3 — hardcoded Python constant
  agent.system_prompt property
  (last resort; should only fire for new agents before their .md is written)
```

Layer 2 is where all agents currently live. Layer 1 is empty until the optimizer has run. Layer 3 exists so nothing breaks during bootstrapping.

### Judge Routing

Domain-expert judges replace the generic judge for content evaluation. The routing is based on `content_type`, which maps directly to the `evaluated_by` field already in `AGENTS.yaml`:

```python
EVALUATOR_ROUTING = {
    "TUTORIAL":     ["written-content-judge", "brand-safety-judge"],
    "CAROUSEL":     ["visual-content-judge",  "brand-safety-judge"],
    "VIDEO_REEL":   ["video-content-judge",   "brand-safety-judge"],
    "THREAD":       ["written-content-judge", "platform-fit-judge"],
    "DEMO":         ["video-content-judge",   "brand-safety-judge"],
    "TIPS":         ["written-content-judge", "brand-safety-judge"],
    "CASE_STUDY":   ["written-content-judge", "brand-safety-judge"],
    "ANNOUNCEMENT": ["written-content-judge", "brand-safety-judge"],
    "EDUCATIONAL":  ["written-content-judge", "seo-judge"],
}
```

Each evaluator has its own `.md` prompt in `agentic/agents/evaluators/`. `JudgeAgent.evaluate()` is extended to accept an optional `evaluator_id` that overrides the system prompt with the domain expert's rubric.

### Self-Evaluation Hook

`BaseAgent._evaluate_self()` is called at the end of `run()`. It is opt-out, not opt-in:

```python
async def run(self, ...) -> dict[str, Any]:
    self.check_kill_switch()
    app = self.compile(checkpointer=checkpointer)
    initial = state or self.default_state()
    ...
    final_state = await app.ainvoke(initial, config=config)

    # NEW: evaluate output quality
    await self._evaluate_self(task=..., output=final_state)

    return final_state
```

`_evaluate_self()` is async and non-blocking — it appends to trajectory.jsonl but does not raise on judge failure. If the judge is unavailable (no API key, rate limit), it logs a warning and continues.

### Langfuse Wiring

`BaseAgent.run()` wraps `app.ainvoke()` in a Langfuse trace:

```python
trace = self.langfuse.trace(name=self.agent_name, tags=["agent_run"])
generation = trace.generation(
    name="graph_invoke",
    model=self.agent_config.default_model_tier,
    input=initial,
)
final_state = await app.ainvoke(initial, config=config)
generation.end(output=final_state)
trace.update(metadata={"pipeline_run_id": pipeline_run_id})
```

When `LANGFUSE_PUBLIC_KEY` is not set, `langfuse` returns a no-op client (`NullLangfuse`) — no change in behavior, no crash.

## Implementation Notes

### AgentRegistry (`src/holus/agents/registry.py`)

```python
@dataclass
class AgentInfo:
    agent_id: str
    role: str
    type: str          # manager | specialist | evaluator | ops
    category: str | None
    model_tier: str
    status: str        # active | planned | deprecated
    version: str
    prompt_path: str
    evaluated_by: list[str]
    evaluates_with: list[str]
    rubric: list[str]
    is_gate: bool

class AgentRegistry:
    def __init__(self, yaml_path: Path = AGENTS_YAML_PATH): ...
    def list_agents(self, *, type=None, status=None, category=None) -> list[AgentInfo]: ...
    def get_agent(self, agent_id: str) -> AgentInfo: ...
    def get_active_agents(self) -> list[AgentInfo]: ...
    def get_evaluators(self) -> list[AgentInfo]: ...
    def get_evaluator_for(self, content_type: str) -> list[str]: ...
    def get_agent_prompt(self, agent_id: str) -> str: ...
```

`AGENTS_YAML_PATH` defaults to `Path(__file__).parents[3] / "agents" / "AGENTS.yaml"` — relative to the source file, not CWD.

### PromptLoader (`src/holus/core/prompt_loader.py`)

```python
class PromptLoader:
    def get_prompt(self, agent_id: str, fallback: str = "") -> str: ...
    def get_ab_split(self, agent_id: str) -> tuple[str, str, float] | None: ...
    def list_optimizer_variants(self, agent_id: str) -> list[Path]: ...
```

`get_ab_split()` returns `None` when no A/B variant is configured. The content loop checks for this before splitting traffic.

### JudgeAgent extensions (`src/holus/self_improvement/judge.py`)

Two additions to the existing `JudgeAgent.evaluate()` signature:

```python
def evaluate(
    self,
    task: str,
    task_type: str,
    output: str,
    *,
    evaluator_id: str | None = None,   # NEW: use domain-expert rubric
    custom_rubric: str | None = None,
) -> JudgeEvaluation:
```

When `evaluator_id` is set, `PromptLoader` resolves the evaluator's `.md` prompt and uses it as the system prompt instead of `JUDGE_SYSTEM_PROMPT`. This keeps existing behavior for callers that pass neither.

New class method for dispatch:

```python
@classmethod
def route_evaluators(cls, content_type: str) -> list[str]:
    """Return evaluator IDs for this content type."""
    return EVALUATOR_ROUTING.get(content_type.upper(), ["written-content-judge"])
```

### BaseAgent additions (`src/holus/agents/base.py`)

```python
async def _evaluate_self(
    self,
    task: str,
    output: dict[str, Any],
    content_type: str = "default",
    pipeline_run_id: str | None = None,
) -> list[JudgeEvaluation]:
    """Evaluate this agent's last output. Non-fatal — logs on error."""
    ...

async def run(self, ...) -> dict[str, Any]:
    # existing logic unchanged up to ainvoke
    with self._langfuse_trace(pipeline_run_id=pipeline_run_id) as trace:
        final_state = await app.ainvoke(initial, config=config)
    await self._evaluate_self(
        task=self._describe_task(initial),
        output=final_state,
        content_type=self._content_type(final_state),
        pipeline_run_id=pipeline_run_id,
    )
    return final_state
```

`_describe_task()` and `_content_type()` are overridable hooks with sensible defaults.

### Justfile commands

```makefile
evaluate:
    uv run python -m holus.cli evaluate --days 7

learn:
    uv run python -m holus.cli learn

costs:
    uv run python -m holus.cli costs --group-by agent
```

`holus.cli` is a thin Typer CLI that dispatches to `LearningLoop`, `TrajectoryStore`, and `JudgeAgent`. Does not require a running Redis or Anthropic key for `costs` (reads trajectory.jsonl directly).

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `PASS_THRESHOLD` | 0.8 | Existing judge threshold — do not change |
| `MIN_EVALS_FOR_OPTIMIZATION` | 30 | DSPy needs statistical signal; below 30 is noise |
| `JUDGE_MODEL` | `claude-haiku-3-5-20241022` | Haiku is independent from worker models (Sonnet/Opus) |
| `LANGFUSE_FLUSH_ON_CLOSE` | true | Flush buffer when `BaseAgent.close()` is called |
| `EVALUATE_SELF_TIMEOUT_S` | 10 | Max seconds for self-eval before timeout — non-fatal |
| `AB_SPLIT_RATIO` | 0.5 | Default 50/50 when optimizer has a challenger variant |

### Dependencies

- Depends on: Spec 012 (Knowledge & Learning — trajectory.jsonl format, LearningLoop)
- Depends on: Spec 017 (Authority Engine — agent prompt files in `agents/`)
- Depends on: Spec 027 (Resilient Agent Loop — BaseAgent.run() structure)
- Depended on by: Spec 025 (Content Loop — uses registry to get active specialists)
- Depended on by: Spec 026 (Reviewer Pool — uses registry to get evaluators)

## Alternatives Considered

### Alternative A: Hardcode routing in JudgeAgent

Keep `EVALUATOR_ROUTING` inside `judge.py` and treat it as a first-class feature of the judge.

Trade-off: Simpler location, but the routing logically belongs to the registry since `evaluated_by` is already in `AGENTS.yaml`.
Rejected because: Splits the source of truth. If someone adds an agent to AGENTS.yaml and changes its `evaluated_by`, they also have to remember to update the hardcoded dict in `judge.py`. Registry owns it, judge dispatches.

### Alternative B: Agent evaluates itself using its own model

Use the agent's own Claude client to run evaluation instead of `JudgeAgent`.

Trade-off: Saves one LLM call.
Rejected because: Self-evaluation bias is the key design constraint in `judge.py` (see module docstring). An agent that grades its own output will inflate scores. The independence of the judge (Haiku, separate call) is intentional.

### Alternative C: Lazy registry (read YAML on every call)

Parse `AGENTS.yaml` on each `list_agents()` call instead of caching at init.

Trade-off: Always fresh, but 32-agent parse on every content loop iteration.
Rejected because: YAML changes require a process restart anyway (we don't hot-reload prompts mid-run). Cache at init is correct; add a `reload()` method for tests.

## Edge Cases & Failure Modes

- **AGENTS.yaml missing or malformed:** `AgentRegistry.__init__` raises `FileNotFoundError` or `yaml.YAMLError` at import time — fail fast, do not silently fall back.
- **Prompt .md file missing for active agent:** `PromptLoader.get_prompt()` falls back to Layer 3 (Python string) and emits a `WARNING` log. This is expected during bootstrapping; it is a bug in production.
- **JudgeAgent API error during `_evaluate_self()`:** Log at `WARNING` level, do not raise. The agent output has already been returned. The missing evaluation is noted in trajectory metadata as `evaluation_status: "failed"`.
- **Langfuse not configured:** `langfuse` property returns `NullLangfuse`. All `trace()` and `generation()` calls are no-ops. Zero performance impact.
- **`content_type` not in `EVALUATOR_ROUTING`:** Fall back to `["written-content-judge"]`. Log at `DEBUG` level. Never raise.
- **Trajectory.jsonl unwritable (disk full, permissions):** Log at `ERROR` level and continue. Self-evaluation failure must never block content output.
- **`just evaluate` with zero trajectory entries:** Print "No trajectory entries in the last 7 days." and exit 0.

## Observability

**Langfuse traces (when configured):**
- Trace name: `{agent_name}` (e.g., `hook-architect`)
- Tags: `["agent_run", content_type, pipeline_run_id]`
- Generation span captures: input tokens, output tokens, model tier, latency
- Evaluation span captures: judge verdict, score, evaluator IDs used

**Structured log events:**
```
INFO  registry: loaded agents from agentic/agents/AGENTS.yaml
INFO  prompt_loader: resolved hook-architect → agentic/agents/specialists/written-authority/hook-architect.md (layer 2)
INFO  judge_dispatch: TUTORIAL → [written-content-judge, brand-safety-judge]
WARN  self_eval: judge timed out after 10s — marking as evaluation_status=failed
WARN  prompt_loader: no .md file for security-sentinel — falling back to Python string (layer 3)
```

**`just costs` output format:**
```
Agent Cost Breakdown (last 7 days)
===================================
hook-architect         $0.0042  (84 runs)
storyteller            $0.0038  (76 runs)
voice-guardian         $0.0011  (22 runs, classification)
...
Total                  $0.0312
```

## Rollback Plan

All changes are additive:
- `AgentRegistry` is a new file — delete it if broken.
- `PromptLoader` is a new file — delete it; `BaseAgent.system_prompt` continues to serve the Python string.
- `BaseAgent._evaluate_self()` — wrap the call in `try/except Exception` with `pass` to disable instantly.
- `BaseAgent.run()` Langfuse wiring — already guarded by `NullLangfuse`; no behavior change if Langfuse is not configured.
- `JudgeAgent` extensions — backward-compatible (new params are keyword-only with defaults).

No data migration needed. No schema changes. Rollback is `git revert`.

## Open Questions

- [ ] Should `_evaluate_self()` be async or sync? `JudgeAgent.evaluate()` is currently sync (blocking HTTP). If we make it async, we need `asyncio.to_thread()`. — @Juan
- [ ] Should the registry cache be invalidated when `agentic/agents/AGENTS.yaml` is modified? Currently requires process restart. — @Juan
- [ ] Do we want per-evaluator score tracking in trajectory.jsonl (separate entry per evaluator) or one merged entry? Separate is more queryable; merged is simpler. — @Juan

## Acceptance Criteria

- [ ] `AgentRegistry.list_agents()` returns exactly 32 agents when called on the current `AGENTS.yaml`
- [ ] `AgentRegistry.list_agents(type="evaluator")` returns 7 agents
- [ ] `AgentRegistry.list_agents(status="active")` excludes `planned` and `deprecated` agents
- [ ] `AgentRegistry.get_agent_prompt("hook-architect")` resolves to the `.md` file content (layer 2) without a layer-1 override present
- [ ] `PromptLoader` returns layer-1 content when `config/prompts/{agent_id}/current.md` exists
- [ ] `PromptLoader` returns layer-3 string and emits `WARNING` log when no `.md` file exists
- [ ] `JudgeAgent.evaluate(evaluator_id="written-content-judge")` uses the evaluator's `.md` as the system prompt
- [ ] `JudgeAgent.route_evaluators("TUTORIAL")` returns `["written-content-judge", "brand-safety-judge"]`
- [ ] `JudgeAgent.route_evaluators("UNKNOWN_TYPE")` returns `["written-content-judge"]` without raising
- [ ] `BaseAgent._evaluate_self()` appends a trajectory entry with `evaluation_status: "ok"` on success
- [ ] `BaseAgent._evaluate_self()` appends `evaluation_status: "failed"` and does NOT raise when judge errors
- [ ] `BaseAgent.run()` creates a Langfuse trace when `LANGFUSE_PUBLIC_KEY` is set in environment
- [ ] `BaseAgent.run()` completes normally (no crash, no warning) when `LANGFUSE_PUBLIC_KEY` is not set
- [ ] `just evaluate` prints a summary table of judge scores for the last 7 days
- [ ] `just costs` prints per-agent cost breakdown sourced from trajectory.jsonl
- [ ] `uv run pytest -q` passes with 606+ tests after all changes are applied
