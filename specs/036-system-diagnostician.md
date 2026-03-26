# SPEC-036: System Diagnostician

**Status:** Not Started
**Author:** Camilo + Claude
**Date:** 2026-03-26
**Depends on:** SPEC-030 (Agent Registry), SPEC-031 (LinkedIn Pipeline)

---

## Problem

Holus generates content and evaluates it, but nobody watches the machine itself.
The 7 domain evaluators were silently broken for 2 months (registry path bug) and
no system detected it. Judge feedback never flows back to producing agents. The
prompt optimizer exists but never triggers. Pattern data is collected but never acted on.

Individual judges evaluate individual pieces. But systemic failures — broken code paths,
misconfigured prompts, missing agents, disconnected feedback loops — require a higher-level
view that reads the codebase, trajectory patterns, and evaluator output together.

## Solution

A **System Diagnostician** agent that runs after every content cycle (or weekly).
It does NOT evaluate content. It evaluates the machine that makes content.

It reads the whole repo — code, prompts, trajectory, content output — and produces
actionable tasks for the human to implement.

## Architecture

```
                    SYSTEM DIAGNOSTICIAN (Opus, weekly)
                    Reads: code + prompts + trajectory + output
                    Writes: diagnostic report + NEXT.md tasks
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              CODE ISSUES  PROMPT GAPS  SYSTEM GAPS
              (bug fixes)  (rewrites)   (new agents/tools)
```

### What the Diagnostician Does

1. **Reads trajectory data** (last 30 days)
   - Groups failures by agent, platform, content type, dimension
   - Detects patterns: "hook_strength < 6 on 70% of pieces"
   - Detects anomalies: "judge_verdict is null on all 5 pieces this cycle"

2. **Reads the code** that produced failures
   - When hook_strength is low → reads the idea-generator prompt and code
   - When format is wrong → reads repurpose.py
   - When judges don't run → reads judge.py evaluate_with_routing()

3. **Traces root causes** to one of 5 categories:
   - **CODE_BUG**: Something in Python is broken (registry path, truncation logic)
   - **PROMPT_GAP**: Agent prompt is missing instructions (no hook emphasis, no thread format)
   - **MISSING_AGENT**: Pipeline needs a specialist that doesn't exist (fact-checker, hook rewriter)
   - **MISSING_TOOL**: Agent needs a tool it doesn't have (web search for fact-checking)
   - **CONFIG_ISSUE**: brand.yaml, products.yaml, or knowledge files are stale/wrong

4. **Produces tasks** in NEXT.md format:
   ```
   - [ ] [FIX] {description}
         Root cause: {traced to file:line}
         Evidence: {N failures in trajectory with pattern X}
         Suggested fix: {concrete change}
   ```

### What the Diagnostician Does NOT Do

- Does NOT fix code (proposes fixes, human implements)
- Does NOT evaluate individual content pieces (judges do that)
- Does NOT replace the learning loop (reads its output)
- Does NOT run during content generation (runs after, on a schedule)

## Model Choice

**Opus** for the diagnostician. It needs to:
- Read and understand Python code
- Read agent prompts and identify what's missing
- Correlate trajectory patterns with code behavior
- Generate specific, implementable task descriptions

Sonnet is insufficient for code reasoning + pattern synthesis at this scale.

## Input Contract

The diagnostician receives:

```python
@dataclass
class DiagnosticContext:
    trajectory_entries: list[dict]      # Last 30 days from trajectory.jsonl
    content_queue: list[Path]           # Recent content files
    source_files: dict[str, str]        # Key source files (agent.py, repurpose.py, judge.py, etc.)
    agent_prompts: dict[str, str]       # All agent .md files
    config: dict[str, Any]             # brand.yaml, products.yaml
    evaluator_rubrics: dict[str, list]  # Per-evaluator dimension lists from AGENTS.yaml
    previous_diagnostic: str | None     # Last diagnostic report (to check if fixes landed)
```

## Output Contract

```python
@dataclass
class DiagnosticReport:
    timestamp: str
    cycle_analyzed: str

    # Findings grouped by priority
    critical: list[DiagnosticTask]    # P0: system broken, nothing works
    high: list[DiagnosticTask]        # P1: quality systematically poor
    medium: list[DiagnosticTask]      # P2: improvement opportunities
    suggestions: list[DiagnosticTask] # P3: new agents, tools, architecture ideas

    # Health metrics
    judge_coverage: float             # % of pieces that got real (non-fallback) evaluation
    avg_score_trend: str              # "improving" | "declining" | "flat"
    top_failing_dimension: str        # e.g. "hook_strength"
    feedback_loop_status: str         # "connected" | "disconnected"

@dataclass
class DiagnosticTask:
    category: str                     # CODE_BUG | PROMPT_GAP | MISSING_AGENT | MISSING_TOOL | CONFIG_ISSUE
    description: str                  # Human-readable description
    root_cause: str                   # Traced to specific file:line or prompt:section
    evidence: str                     # Trajectory data supporting this finding
    suggested_fix: str                # Concrete change to make
    priority: str                     # P0 | P1 | P2 | P3
    estimated_effort: str             # "5 min" | "1 hour" | "1 day" | "1 sprint"
```

## Schedule

- **After every content_cycle**: Quick diagnostic (check judge coverage, null verdicts, new failures)
- **Weekly (improvement_cycle)**: Full diagnostic (read code, analyze patterns, propose tasks)
- **On demand**: `just diagnose` command

## Integration Points

1. **orchestrator.py**: Add `diagnostic_cycle()` call after `improvement_cycle()`
2. **NEXT.md**: Diagnostician appends tasks to a "## System Diagnostic Tasks" section
3. **trajectory.jsonl**: Diagnostician logs its own findings for trend tracking
4. **Previous diagnostic**: Each run reads the last report to check if past suggestions were implemented

## Example Output

```markdown
# System Diagnostic — 2026-03-26

## Health
- Judge coverage: 0% (CRITICAL — all 5 pieces got null verdicts)
- Score trend: flat (no real scores to trend)
- Top failing dimension: N/A (judges didn't run)
- Feedback loop: disconnected

## P0 — Critical
- [x] Judge registry path off-by-one: parents[2] → parents[3]
  File: src/holus/self_improvement/judge.py:370
  Evidence: 5/5 pieces with judge_verdict=null
  Fix: Change parents[2] to parents[3] ← FIXED in commit 4b3aa2f

## P1 — High
- [ ] Twitter content never formatted as thread
  File: src/holus/agents/marketing/repurpose.py:_claude_adapt()
  Evidence: 3/3 Twitter pieces scored PARTIAL on thread_pacing (0.48 avg)
  Judge feedback: "NOT formatted as a Twitter thread" (entries 222, etc.)
  Fix: Add thread-splitting instruction to Twitter repurpose prompt

- [ ] Judge feedback not fed back to generators
  File: src/holus/agents/marketing/agent.py (observe phase)
  Evidence: No code path reads trajectory feedback before generating
  Fix: In observe(), load last cycle's judge feedback and inject into prompts

## P2 — Medium
- [ ] Threads content truncated mid-word
  File: src/holus/agents/marketing/repurpose.py:_enforce_limit()
  Evidence: 1/3 Threads pieces end with "..." mid-word
  Fix: Already patched (sentence-aware truncation), but prompt should say 480 chars not 500

## P3 — Suggestions
- [ ] Consider: fact-checking agent between generation and evaluation
  Evidence: authority_signal scores are based on claim presence, not truth
  No agent verifies that numbers/tools/timelines mentioned actually exist
  Effort: 1 sprint (new agent + web search tool integration)
```

## Acceptance Criteria

1. `just diagnose` runs the diagnostician and prints a report
2. Report correctly identifies at least 1 real issue from trajectory data
3. Each finding includes: category, file reference, evidence, suggested fix
4. Findings are prioritized (P0-P3) based on impact
5. Report tracks whether previous suggestions were implemented
6. Diagnostician logs its findings to trajectory.jsonl
7. Integration with orchestrator.py improvement_cycle()

## What This Is NOT

- Not a replacement for domain judges (they evaluate content, this evaluates the system)
- Not an auto-fixer (proposes tasks, human implements)
- Not a prompt optimizer (that's prompt_evolution.py — this identifies WHAT to optimize)
- Not a code generator (identifies bugs and suggests fixes, doesn't write code)

## Build Order

Phase 1: Core diagnostician (read trajectory + detect patterns → report)
Phase 2: Code reading (trace failures to specific files/lines)
Phase 3: Prompt analysis (identify gaps in agent prompts vs evaluator rubrics)
Phase 4: Integration (orchestrator, NEXT.md auto-append, trend tracking)
