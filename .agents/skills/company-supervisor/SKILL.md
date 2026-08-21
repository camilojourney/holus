---
name: company-supervisor
description: "Company OS supervisor. Reconcile desk events into IC and ready-for-code queues."
compatibility: [python>=3.12]
prompt_version: 2
agentic_eval: default-7-pillars
---

# Company Supervisor

This Holus-owned Company OS skill routes Company OS desk work. It does not approve human-gated
actions, publish, send outreach, spend money, or implement fixes.

## Inputs

- `.self-improvement/automations/COMPANY_OS.md`
- `.self-improvement/COMPANY_KILL`
- `.self-improvement/automations/{brand-marketing,brand-sales,brand-content,supervisor}/events.jsonl`
- `.self-improvement/automations/*/fix_required.jsonl`
- `.self-improvement/hub/ic_decisions.jsonl`
- `.self-improvement/hub/company_docket.json`

## Workflow

1. Stop with `HALT` when `COMPANY_KILL` is tripped or unreadable.
2. Read desk events and fix-required rows.
3. Reconcile every item into exactly one queue:
   `human_ic_required`, `ready_for_code`, or `needs_more_evidence`.
4. Keep `ready_for_code` to at most one lane.
5. Write the updated docket to `.self-improvement/hub/company_docket.json` and
   append a supervisor event to
   `.self-improvement/automations/supervisor/events.jsonl`.
6. Follow `references/output-contract.md`.

## Deterministic Commands

- `python3 build_supervisor_context.py --repo-path <holus-root> --out /tmp/company-supervisor-context.json`
- `python3 render_supervisor_outputs.py --repo-path <holus-root> --context-file /tmp/company-supervisor-context.json`

## Agents

- `approval-ledger-auditor`
- `docket-router`
- `ready-for-code-selector`
