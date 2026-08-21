---
name: company-sales-desk
description: "Company OS sales desk. Review outreach and qualified-lead evidence before routing."
compatibility: [python>=3.12]
prompt_version: 2
agentic_eval: default-7-pillars
---

# Company Sales Desk

This Holus-owned Company OS skill reads sales evidence and writes a desk event. It does not
send messages, approve outreach, update external CRMs, or spend money.

## Inputs

- `.self-improvement/automations/COMPANY_OS.md`
- `.self-improvement/COMPANY_KILL`
- `.self-improvement/automations/brand-sales/events.jsonl`
- `.self-improvement/hub/ic_decisions.jsonl`

## Workflow

1. Stop with `HALT` when `COMPANY_KILL` is tripped or unreadable.
2. Review sales KPI placeholders: `outreach_sent`, `reply_rate`,
   `qualified_leads`, and `meetings_booked`.
3. Read Notion API lead-capture evidence when present, with manual-review spam
   flags and 3 requests/second rate-limit awareness.
4. Route any outbound send, follow-up, or CRM mutation to `human_ic_required`.
5. Append one event to `.self-improvement/automations/brand-sales/events.jsonl`.
6. Follow `references/output-contract.md`.

## Deterministic Commands

- `python3 build_sales_context.py --repo-path <holus-root> --out /tmp/company-sales-context.json`
- `python3 render_sales_outputs.py --repo-path <holus-root> --context-file /tmp/company-sales-context.json`

## Silo Invoke Paths

- Notion lead capture validation: official Notion API read path, mirrored to
  the local handoff payload with `rate_limit_requests_per_second=3`
- Notion milestone journal: `/notion log Company OS funnel milestone`

Live outreach or CRM mutation remains blocked unless
`.self-improvement/hub/ic_decisions.jsonl` contains a matching `APPROVED` row;
`DRY_RUN=1` keeps verification on local ledgers only.

## Agents

- `lead-quality-reviewer`
- `outreach-boundary-auditor`
