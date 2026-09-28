---
name: holusight
description: >
  Hybrid BM25 + vector + structural search over any project's code and
  docs, with provenance/freshness/egress attached to every answer -- not
  a fluent guess. Self-installs `holus` on first use, in any project.
  Trigger: /holusight.
---

# /holusight - install-anywhere Holusight-AXI search

Ask this project for evidence before trusting or editing a spec, ADR, or the code it governs -- "where is X enforced", "has this spec drifted from its implementation", "is the structural graph stale". Works per-project: run it from inside any repository's checkout, and it indexes and evidences that repository.

## Step 0 -- Ensure `holus` is installed

```bash
PYTHON=""
# 1. Already on PATH from a prior install in this shell
if command -v holus >/dev/null 2>&1; then
    PYTHON="__PATH__"
fi
# 2. uv tool install -- most reliable on modern Mac/Linux, isolated venv
if [ "$PYTHON" != "__PATH__" ] && command -v uv >/dev/null 2>&1; then
    _UV_PY=$(uv tool run --from holusight python -c "import sys; print(sys.executable)" 2>/dev/null)
    if [ -n "$_UV_PY" ] && "$_UV_PY" -c "import holusight" 2>/dev/null; then PYTHON="$_UV_PY"; fi
fi
# 3. Fall back to python3 and check for an existing install
if [ -z "$PYTHON" ]; then PYTHON="python3"; fi
if [ "$PYTHON" != "__PATH__" ] && ! "$PYTHON" -c "import holusight" 2>/dev/null; then
    if command -v uv >/dev/null 2>&1; then
        uv tool install --upgrade "git+https://github.com/camilojourney/holusight" -q 2>&1 | tail -5
        _UV_PY=$(uv tool run --from holusight python \
            -c "import sys; print(sys.executable)" 2>/dev/null)
        if [ -n "$_UV_PY" ]; then PYTHON="$_UV_PY"; fi
    else
        "$PYTHON" -m pip install "git+https://github.com/camilojourney/holusight" -q 2>/dev/null \
          || "$PYTHON" -m pip install "git+https://github.com/camilojourney/holusight" -q --break-system-packages 2>&1 | tail -5
    fi
fi
mkdir -p .holusight
if [ "$PYTHON" != "__PATH__" ]; then
    "$PYTHON" -c "
import sys
open('.holusight/.holusight_python', 'w', encoding='utf-8').write(sys.executable)
"
fi
```

If `holus` was already on PATH (case 1), skip straight to Step 1 -- no
install output to print. Otherwise print nothing on success and move to
Step 1.

**In every subsequent bash block below, prefer the bare `holus` command.**
Only fall back to `$(cat .holusight/.holusight_python) -m holusight.cli_axi`
when `holus` is not found on PATH (a fresh `uv tool install` shim may not
be visible until a new shell) -- and to
`$(cat .holusight/.holusight_python) -m holusight index .` for Step 1's
`index` subcommand, which `python -m holusight` (not `holus`) exposes.

## Step 1 -- Build the search index (first run, or after significant changes)

`holus evidence`/`check`/`status` work with no index (exact + structural +
consistency providers only). The `semantic` provider -- needed for
fuzzy/conceptual search across this project -- requires an index built
once, ahead of time; it is never built as a side effect of a read-only
`holus` call:

```bash
holus_python="$(cat .holusight/.holusight_python 2>/dev/null || echo python3)"
"$holus_python" -m holusight index . 2>&1 | tail -10
```

Re-run this after substantial content changes (`--force` to rebuild from
scratch). Skip it entirely for a quick first look -- `holus evidence`
already works without it, just without the semantic provider.

## Step 1 -- Ensure this project's `/holusight` skill exists

The project-local skill is the source of truth for this checkout. Install it
only when absent; never replace an existing `.agents/skills/holusight` or write
any harness-global skill directory:

```bash
holusight-install-skill --project-local
```

The command is local-only and fails closed if `.agents/skills/holusight` would
escape the current project through a symlink. If the skill already exists, it
is left unchanged.

Schema version: `0.8.0` (generated from `src/holusight/axi_schema.py` - do not hand-edit the command reference below; run `python -m holusight.axi_skill_gen` after changing the schema).

## When to use this

1. Use native/exact search for exact identifiers and known file questions - `holus` is for uncertain, conceptual, or cross-file/mixed code-and-docs questions.
2. Call `holus evidence "<question>"` when the relevant location is uncertain.
3. Call `holus check [scope]` when the question concerns whether a spec/ADR has drifted from what it governs.
4. Never treat a `stale`, `partial`, or `unavailable` provider state as if it were current, authoritative evidence - surface the state to the user instead of a confident answer.

## Commands

### `holus`

Content-first repository home view: identity, snapshot, provider freshness, egress, contract summary.

Flags:
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus
python -m holusight.cli_axi
```

### `holus evidence "<question>"`

Return the smallest current evidence packet for a question, routed across the exact, structural, consistency, and (if already indexed) semantic providers.

Flags:
- `--mode` (auto/exact/semantic/structure) [default: auto] - Restrict which providers run.
- `--provider` (exact/structural/consistency/semantic) - Restrict to exactly one named provider.
- `--explain-route` - Include route_reason per provider.
- `--allow-egress` - Permit the semantic provider to query a Voyage-embedded index (external API call). Off by default.
- `--full` - Disable excerpt truncation.
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus evidence "where is retry policy enforced?"
python -m holusight.cli_axi evidence "where is retry policy enforced?"
holus evidence "where is retry policy enforced?" --mode exact
python -m holusight.cli_axi evidence "where is retry policy enforced?" --mode exact
holus evidence "<question>" --fields snapshot,evidence.source,evidence.location
python -m holusight.cli_axi evidence "<question>" --fields snapshot,evidence.source,evidence.location
```

### `holus research-urls "<question>" --url <https-url> --url <https-url> [--url <https-url>] --allow-egress`

Fetch 2-3 supplied public HTTPS pages for one question; write a dated Markdown report and JSON receipt to gitignored derived state. Claims are exact verified excerpts, not inferred facts.

Flags:
- `--url` - Public HTTPS source URL (repeat 2-3 times).
- `--allow-egress` - Explicitly permit public HTTPS fetches.
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus research-urls "What does the policy say?" --url https://example.org/a --url https://example.org/b --allow-egress
python -m holusight.cli_axi research-urls "What does the policy say?" --url https://example.org/a --url https://example.org/b --allow-egress
```

### `holus check [scope]`

Post-change consistency check: has the canonical spec/ADR at `scope`, or every concept if `scope` is omitted, drifted from its linked artifacts since the cache was last refreshed?

Flags:
- `--refresh` - Refresh the consistency cache to current disk state before checking (resets the drift baseline).
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus check
python -m holusight.cli_axi check
holus check specs/013-holusight-axi-consistency-architecture.md
python -m holusight.cli_axi check specs/013-holusight-axi-consistency-architecture.md
holus check --refresh
python -m holusight.cli_axi check --refresh
```

### `holus status`

Repository snapshot, per-provider freshness/egress, contract (claim) pass/fail counts, and open health-flag counts by severity.

Flags:
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus status
python -m holusight.cli_axi status
```

### `holus providers`

List each provider's availability, version/model, freshness, and egress class.

Flags:
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus providers
python -m holusight.cli_axi providers
```

### `holus usage-summary`

Summarize local content-minimized usage events, coverage, measured deltas, and feedback outcomes.

Flags:
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus usage-summary --format json
python -m holusight.cli_axi usage-summary --format json
```

### `holus improve-status`

Continuous-improvement lifecycle status: frozen-case corpus summary, status-quo coverage, and placement-guard capabilities.

Flags:
- `--cases` - Path to the frozen case corpus JSONL file.
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-status
python -m holusight.cli_axi improve-status
holus improve-status --cases tests/fixtures/holusight_eval_pilot_cases.jsonl
python -m holusight.cli_axi improve-status --cases tests/fixtures/holusight_eval_pilot_cases.jsonl
```

### `holus improve-intake "<summary>"`

Produce an explicit, sanitized, content-minimized proposed regression case for human-reviewed admission. No files are written.

Flags:
- `--origin` - Case origin.
- `--kind` (regression/comparative) [default: regression] - Case kind.
- `--diagnosis-ref` - Reference path for reproduced findings.
- `--fix-ref` - Reference to the fix commit/PR for a reproduced gap.
- `--cases` - Path to the frozen case corpus JSONL file.
- `--admitted-by` - Approver name or team in plain text.
- `--admitted-at` - YYYY-MM-DD date for the admission record.
- `--case-id` - Explicit candidate case id to propose.
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-intake "holus evidence can starve structural evidence" --origin reproduced_usage_gap --kind comparative --admitted-by team-x
python -m holusight.cli_axi improve-intake "holus evidence can starve structural evidence" --origin reproduced_usage_gap --kind comparative --admitted-by team-x
python -m holusight.cli_axi improve-intake "structural graph stale case" --origin spec_documented_finding --admitted-by team-x
python -m python -m holusight.cli_axiight.cli_axi improve-intake "structural graph stale case" --origin spec_documented_finding --admitted-by team-x
```

### `holus improve-run`

Run the frozen continuous-improvement corpus with explicit lineage and machine-readable lifecycle outcome.

Flags:
- `--cases` - Path to the frozen case corpus JSONL file.
- `--workflow` - Execution workflow label.
- `--tool` - Tool that produced this run.
- `--model` - LLM model name used by the run.
- `--compare-result` - Previous pilot result JSON path. Promotion-relevant comparison requires a clean tracked evaluated manifest that pins its exact bytes; all other comparisons fail closed.
- `--candidate-id` - Stable candidate identifier for this run.
- `--output` - Write the full PilotRunResult JSON only to gitignored derived state or a safe external path.
- `--allow-egress` - Allow egress-only pilot operations when a case explicitly requires it.
- `--allow-semantic` - Allow semantic providers while running cases that require them.
- `--scorecard` - Also print the Fleet aggregate scorecard preview.
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-run
python -m holusight.cli_axi improve-run
holus improve-run --candidate-id run-42 --workflow crewmate --model claude-sonnet-5
python -m holusight.cli_axi improve-run --candidate-id run-42 --workflow crewmate --model claude-sonnet-5
holus improve-run --cases tests/fixtures/holusight_eval_pilot_cases.jsonl --compare-result /tmp/last-run.json
python -m holusight.cli_axi improve-run --cases tests/fixtures/holusight_eval_pilot_cases.jsonl --compare-result /tmp/last-run.json
```

### `holus improve-placement`

Validate a proposed artifact path against structure, canonical locations, and existing duplicates. Never edits files.

Flags:
- `--artifact-type` (case/fixture/test/spec/adr/decision/playbook/source/skill/agent/docs) - Logical placement kind for a proposed artifact.
- `--proposed-path` - Proposed artifact path to validate.
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-placement --artifact-type case --proposed-path tests/fixtures/my_case.jsonl
python -m holusight.cli_axi improve-placement --artifact-type case --proposed-path tests/fixtures/my_case.jsonl
holus improve-placement --artifact-type spec --proposed-path specs/018-new-idea.md
python -m holusight.cli_axi improve-placement --artifact-type spec --proposed-path specs/018-new-idea.md
```

### `holus improve-variation-run`

Run the fixed, local evidence-display variation baseline and two controlled candidates. Hard constraints and rewards stay separate; promotion is always human-guarded.

Flags:
- `--record` - Opt in to a content-minimized derived review record under .holusight/.
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-variation-run
python -m holusight.cli_axi improve-variation-run
holus improve-variation-run --record --format json
python -m holusight.cli_axi improve-variation-run --record --format json
```

### `holus improve-variation-feedback`

Queue only an aggregate, privacy-safe real-use signal for human fixture-admission review. It never changes a case, threshold, evaluator, or authority.

Flags:
- `--signal` (failure_case/aggregate_outcome) - Privacy-safe aggregate real-use signal for human review.
- `--count` - Positive aggregate signal count.
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-variation-feedback --signal failure_case --count 2
python -m holusight.cli_axi improve-variation-feedback --signal failure_case --count 2
```

### `holus improve-review <change-manifest.json>`

Deterministically classify one tracked change, verify its canonical links, and return stage, missing evidence, next permitted action, and promotion blockers.

Flags:
- `--phase` (before_change/after_implementation/after_test/pre_promotion) [default: before_change] - Deterministic review phase.
- `--record` - Opt in to a content-minimized derived review record under .holusight/.
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-review specs/019-example.change.json --phase before_change
python -m holusight.cli_axi improve-review specs/019-example.change.json --phase before_change
holus improve-review specs/019-example.change.json --phase pre_promotion --record
python -m holusight.cli_axi improve-review specs/019-example.change.json --phase pre_promotion --record
```

### `holus improve-history <change-id>`

Inspect content-minimized, opt-in derived stage history for a change. Deleting derived records never changes canonical truth.

Flags:
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-history example-change
python -m holusight.cli_axi improve-history example-change
```

### `holus improve-integration <change-manifest.json>`

Emit the stable local advisory review contract for a future No Mistakes or Fleet consumer. It performs no integration, promotion, or egress.

Flags:
- `--phase` (before_change/after_implementation/after_test/pre_promotion) [default: before_change] - Deterministic review phase.
- `--fields` - Comma-separated dotted-path projection (e.g. snapshot,evidence.source).
- `--format` (toon/json/text) [default: toon] - Output encoding.

Examples:
```
holus improve-integration specs/019-example.change.json --phase pre_promotion
python -m holusight.cli_axi improve-integration specs/019-example.change.json --phase pre_promotion
```

## Output formats

`--format toon` (default, compact agent-facing) · `--format json` (lossless canonical interchange) · `--format text` (human-readable). `--fields a,b.c` projects a payload down to just those dotted paths before rendering.

## Getting help

`--help` works on every command, including with no command (`holus --help`) for the full command list. Unknown flags and commands are rejected with exit code 2 and the valid set listed inline - never silently ignored.

## Exit codes

`0` success, including a definitive "no evidence" or "already up to date" answer · `1` runtime error · `2` usage error (unknown command/flag, missing required argument).
