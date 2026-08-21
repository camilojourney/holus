---
name: company-evolve
description: "Company OS evolve stub. Summarize desk events and append improvement experiment reports."
compatibility: [python>=3.12]
prompt_version: 2
agentic_eval: default-7-pillars
---

# Company Evolve

This Holus-owned Company OS skill reads Company OS desk events and appends one improvement
report. It does not launch experiments, mutate desk config, spend money,
publish, send outreach, or approve work.

## Inputs

- `.self-improvement/automations/COMPANY_OS.md`
- `.self-improvement/COMPANY_KILL`
- `.self-improvement/automations/{brand-marketing,brand-sales,brand-content,supervisor}/events.jsonl`
- `.self-improvement/hub/experiment_reports.jsonl`

## Workflow

1. Stop with `HALT` when `COMPANY_KILL` is tripped or unreadable.
2. Read recent desk events from all Company OS automations.
3. Identify one safe, testable improvement recommendation.
4. Append one row to `.self-improvement/hub/experiment_reports.jsonl` with
   `schema_version=1`, `source=company-evolve`, `status`, and
   `what_to_improve`.
5. Follow `references/output-contract.md`.

## Deterministic Commands

- `python3 build_evolve_context.py --repo-path <holus-root> --out /tmp/company-evolve-context.json`
- `python3 render_evolve_outputs.py --repo-path <holus-root> --context-file /tmp/company-evolve-context.json`

## Agents

- `experiment-report-writer`
- `improvement-prioritizer`
