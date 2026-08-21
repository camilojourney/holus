---
name: company-content-desk
description: "Company OS content desk. Review pipeline depth and publish readiness before routing."
compatibility: [python>=3.12]
prompt_version: 2
agentic_eval: default-7-pillars
---

# Company Content Desk

This Holus-owned Company OS skill reads content pipeline evidence and writes a desk event. It
does not publish, schedule, send, or approve content.

## Inputs

- `.self-improvement/automations/COMPANY_OS.md`
- `.self-improvement/COMPANY_KILL`
- `.self-improvement/automations/brand-content/events.jsonl`
- `.self-improvement/hub/ic_decisions.jsonl`
- Genpeli evidence when supplied by the caller

## Workflow

1. Stop with `HALT` when `COMPANY_KILL` is tripped or unreadable.
2. Review content KPI placeholders: `pipeline_depth`,
   `genpeli_jobs_completed`, and `queue_depth`.
3. Include a Genpeli `consult-editing` handoff payload for content pipeline
   jobs, and keep Holus/post publish readiness behind the IC ledger.
4. Route publish, schedule, or cross-post actions to `human_ic_required`.
5. Append one event to `.self-improvement/automations/brand-content/events.jsonl`.
6. Follow `references/output-contract.md`.

## Deterministic Commands

- `python3 build_content_context.py --repo-path <holus-root> --out /tmp/company-content-context.json`
- `python3 render_content_outputs.py --repo-path <holus-root> --context-file /tmp/company-content-context.json`

## Silo Invoke Paths

- Genpeli editing consultation: `/consult-editing genpeli`
- Holus publish gate: `/post holus --dry-run` after supervisor IC approval
- Notion milestone journal: `/notion log Company OS funnel milestone`

Unattended runs emit these as explicit handoff payloads. `DRY_RUN=1` guarantees
the publish path remains queue-review-only and never calls live APIs.

## Agents

- `content-pipeline-reviewer`
- `publish-gate-auditor`
