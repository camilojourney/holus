# Observability Playbook — Holus

Three-layer observability stack for monitoring the multi-agent marketing system.

## The Three Layers

### Layer 1: Structured Logging (structlog)
- Every agent action logged with structured fields
- Fields: `agent_id`, `action`, `timestamp`, `duration_ms`, `error`
- Log level: INFO for actions, WARNING for retries, ERROR for failures
- Logs to stdout (captured by launchd) and `.self-improvement/logs/`

### Layer 2: LLM Tracing (Langfuse)
- Every LLM call traced with: model, tokens (in/out), cost, latency
- Traces tagged with: `agent_id`, `pipeline_run_id`, `content_type`
- Tool calls (MCP) logged as trace steps
- Self-hosted at `http://localhost:3100` — no data leaves the stack
- Integration: `BaseAgent.langfuse` property (lazy-loaded via `create_langfuse_client`)
- Decorator: `@trace_agent_call(agent_id, task_type, tier)` wraps full task execution
- LangGraph integration gives near-zero setup for graph traces

### Layer 3: Trajectory (JSONL)
- Every agent decision logged to `.self-improvement/memory/trajectory.jsonl`
- Fields: timestamp, agent_id, decision_type, content_type, quality_score, cost_usd, tokens
- Trajectory is the primary data source for the Observatory dashboard
- Append-only — never delete trajectory entries

## Per-Agent Metrics

Every agent tracked on these dimensions:

| Metric | Source | Frequency |
|---|---|---|
| Quality score (avg) | trajectory.jsonl | Per-run |
| Cost (USD) | Langfuse / trajectory | Per-run |
| Token usage (in/out) | Langfuse / trajectory | Per-run |
| Success rate | trajectory.jsonl | Weekly aggregate |
| Latency (p50, p95) | Langfuse | Per-run |
| Retry count | structlog | Per-run |
| Error rate | structlog | Daily aggregate |

## Cost Tracking

### Tagging Strategy
Every LLM call MUST include metadata:
```python
metadata = {
    "agent_id": "hook-architect",
    "pipeline_run_id": "run-20260312-abc123",
    "content_type": "TUTORIAL",
    "model": "claude-sonnet-4-6"
}
```

Tag every LLM call from day one. Retroactively attributing costs without tags is impossible.

### Cost Attribution
- Per-agent: sum of all LLM calls tagged with `agent_id`
- Per-content-piece: sum of all calls sharing a `pipeline_run_id`
- Per-model: sum grouped by model field
- Daily/weekly: time-windowed aggregation via Langfuse Metrics API

### Cache Token Tracking
Claude prompt caching is tracked explicitly:
- `cache_read_tokens` — tokens served from cache (discounted cost)
- `cache_write_tokens` — tokens written to cache
Both fields logged via `trace_llm_call` in `langfuse_client.py`.

### Budget Alerts
- Per-agent daily cap: $5 (configurable in `config/guardrails.yaml`)
- Total daily cap: $50
- Alert threshold: 80% of cap triggers WARNING log

## Judge-Driven Quality Loop

Langfuse is the backbone of the self-improvement loop:

1. Agents run and produce traces
2. Judge agents score traces via `record_judge_score(trace_id, verdict, score, dimension_scores)`
3. Scored traces become DSPy training data via `LangfuseDatasetManager`
4. `create_optimization_dataset(agent_id, task_type, min_score=0.7)` extracts high-quality examples
5. MIPROv2 uses these datasets to optimize agent prompts

### Verdict Categories
- `PASS` → score 1.0
- `PARTIAL` → score 0.5
- `FAIL` → score 0.0

Per-dimension scores stored as `dim_<name>` in Langfuse for drill-down analysis.

## Agent Rubrics (what judges score)

| Agent type | Rubric dimensions |
|---|---|
| Written content | hook_strength, narrative_arc, voice_fidelity, authority_signal, readability_score |
| Visual content | visual_hierarchy, brand_alignment, info_clarity, scroll_stop_power, slide_pacing |
| Video content | hook_timing, pacing_score, retention_prediction, caption_quality, cta_strength |
| Growth/engagement | conversion_potential, authenticity_score, brand_safety, audience_match, frequency_compliance |
| SEO/research | keyword_relevance, search_intent_match, topical_authority, competitive_gap_fill, uniqueness |
| Platform fit | algorithm_signal_strength, format_compliance, native_feel, timing_appropriateness |
| Brand safety (gate) | voice_deviation_score, anti_pattern_count, reputation_risk, forbidden_content_check |

## Observatory Dashboard

The Observatory reads from all three layers:
- **Layer 1** (logs) → System health page, error rate charts
- **Layer 2** (Langfuse) → Cost tracking, latency charts, token usage
- **Layer 3** (trajectory) → Agent performance, content pipeline, evaluations

Langfuse is a backend data source for the Observatory — not the UI. The Observatory calls Langfuse's Metrics API and renders custom charts via Tremor.

### Key Dashboard Views
1. **System Health** — Service status, kill switch, error rate
2. **Agent Grid** — 32 agents with status/score/cost at a glance
3. **Trajectory Timeline** — Real-time feed of agent decisions (SSE)
4. **Cost Breakdown** — Per-agent, per-model, per-day charts
5. **Quality Trends** — Evaluation scores over time by category

### Key Metrics That Matter
- Eval score pass rate (quality health)
- Cost per approved asset (efficiency)
- Agent retry rate (prompt instability signal)
- Time-to-publish (pipeline throughput)
- Per-agent token spend (cost attribution)

## Setting Up Langfuse

```bash
# Required environment variables
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=http://localhost:3100  # self-hosted default
```

Langfuse is optional — if keys are not set, tracing is silently disabled (ImportError caught in `trace_agent_call` decorator). The system works without it, using trajectory.jsonl as the primary data source.

### Using the Decorator
```python
from holus.observability.langfuse_client import trace_agent_call

@trace_agent_call("hook-architect", "write_hook", tier="operational")
def write_hook(brief: str, context: str) -> str:
    ...
```

### Using the Client Directly
```python
# In BaseAgent subclasses, use self.langfuse (lazy-loaded)
from holus.observability.langfuse_client import trace_llm_call, trace_tool_call

trace_llm_call(
    self.langfuse, trace_id, self.agent_name,
    model="claude-sonnet-4-6",
    input_messages=messages,
    output_text=response,
    usage={"input_tokens": 450, "output_tokens": 280},
    cost_usd=0.0021,
)
```

## Debugging Runbook

### Agent producing low-quality content
1. Check trajectory: `just evaluate` — which rubric dimensions are low?
2. Check Langfuse: was the prompt loaded correctly? Token count reasonable?
3. Check knowledge files: are they stale? (`just agents metrics`)

### High costs
1. Check Langfuse Metrics API — which agent_id is expensive?
2. Look for retry loops: same `agent_id`, many traces in a short window
3. Check `model_tier` assignment in `agents/AGENTS.yaml` — Opus is strategic-only, Sonnet for content, classification models for gates
4. Review `config/guardrails.yaml` for per-agent budget caps

### Agent not running
1. Check kill switch: `cat config/guardrails.yaml | grep kill_switch`
2. Check health: `just health`
3. Check logs for errors: `tail -100 .self-improvement/logs/latest.log`

### Missing traces in Langfuse
1. Verify env vars are set: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
2. Check if Langfuse container is running: `curl http://localhost:3100/health`
3. Call `self.langfuse.flush()` — the client buffers events asynchronously (`BaseAgent.close()` flushes on shutdown)

### DSPy dataset is empty or low quality
1. Check judge scores in Langfuse: filter by `judge_verdict` score name
2. Verify `min_score` threshold in `create_optimization_dataset` — default is 0.7
3. Check if judge agents are running and producing `PASS` verdicts
