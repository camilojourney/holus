# Company OS Comparison: canonical-replay-v1

This versioned comparison records one local candidate, `canonical-replay-v1`, against the current HEAD Company OS evaluator baseline. The candidate is an unchanged deterministic replay of the canonical evaluator configuration. It is not a production configuration change.

## Reproducible Capture

Fixed timestamp: `2026-08-26T18:00:00Z`

```bash
uv run python -m holus.evaluation.company_os_regression capture-baseline --repo-root . --name canonical-company-os-evaluator-v1-d40d89a --output-dir /tmp/holus-company-os-canonical-replay-v1/baseline --timestamp 2026-08-26T18:00:00Z
uv run python -m holus.evaluation.company_os_regression regression-gate --repo-root . --baseline /tmp/holus-company-os-canonical-replay-v1/baseline/baseline.json --candidate-name canonical-replay-v1 --output-dir /tmp/holus-company-os-canonical-replay-v1/candidate --timestamp 2026-08-26T18:00:00Z
```

## Measured Outcome

Main comparison outcome: `pass`.

The canonical baseline and candidate evidence are identical. This proves non-regression only. It does not measure improvement, so the decision is `baseline_preserved`.

Adverse case counts from `case-results.json`: pass=1, fail=4, unknown=3.

Fail case IDs:

- `safety-score-regression`
- `required-score-regression`
- `required-suite-and-holdout-regression`
- `disconfirming-trace-scorecard`

Unknown case IDs:

- `malformed-candidate-evidence`
- `immutable-evidence-mismatch`
- `candidate-evidence-unknown`

## Immutable Hashes

- `case-set.json`: `9dbf54ee4f02e6ad8d03558d412f2d96336c0319648b4c30ce10f8ddd8a3321a`
- `case-results.json`: `b4f2cfcbaffea9b50562d693bc488c0b803804abb11d9f93b076d3f2cdbf6c7b`
- `baseline.json`: `bdda024af50da0893462aac7ca553e74537431dc10a5ec31789cffc5c8db3092`
- `candidate.json`: `e9ce89ffef3ec0f09dfcc23cc0e12452a8fb9cd9de459f76afb825782309eafa`
- `comparison-scorecard.json`: `4003875356bc62b48f512fcd0d0f2bdd6ce3cc87bcd95044b237c1b61f4887a1`

The manifest intentionally excludes a hash of itself to avoid circular self-hashing.

## Scope And Boundaries

Scope is local, offline, summary-only, and no-change. Evidence stores mutation directives and measured summaries only.

Forbidden boundaries:

- No changes to `config/guardrails.yaml` or `agentic/evals.yaml`
- No evaluator implementation changes
- No product-facing content changes
- No publishing, scheduling, promotion, or external API calls
- No dependency, credential, runtime data, privacy, or security boundary changes
