---
name: company-marketing-desk
description: "Company OS marketing desk. Review reach, CTR, and campaign evidence before routing."
compatibility: [python>=3.12]
prompt_version: 2
agentic_eval: default-7-pillars
---

# Company Marketing Desk

This Holus-owned Company OS skill reads marketing evidence and writes a desk event. It never
launches campaigns, spends money, publishes content, or grants approval.

## Inputs

- `.self-improvement/automations/COMPANY_OS.md`
- `.self-improvement/COMPANY_KILL`
- `.self-improvement/config/spend-cap.yaml`
- `.self-improvement/automations/brand-marketing/events.jsonl`
- `.self-improvement/hub/ic_decisions.jsonl`

## Workflow

1. Stop with `HALT` when `COMPANY_KILL` is tripped or unreadable.
2. Review marketing KPI placeholders: `reach`, `content_shipped`, `ctr`,
   `top_of_funnel_leads`, and `channel_cac`.
3. Read Beehiiv REST API or webhook evidence when present for email reach and
   CTR; stale or unreachable Beehiiv evidence creates a fix-required item
   rather than a live API mutation.
4. Route spend, launch, publish, or outbound actions to `human_ic_required`.
5. Append one event to `.self-improvement/automations/brand-marketing/events.jsonl`.
6. Follow `references/output-contract.md`.

## Deterministic Commands

- `python3 build_marketing_context.py --repo-path <holus-root> --out /tmp/company-marketing-context.json`
- `python3 render_marketing_outputs.py --repo-path <holus-root> --context-file /tmp/company-marketing-context.json`

## Silo Invoke Paths

- Holus queue review: `/post holus --dry-run`
- Notion milestone journal: `/notion log Company OS funnel milestone`

The Holus path reads the local `data/content-queue` and requires a matched
`APPROVED` row in `.self-improvement/hub/ic_decisions.jsonl` before routing a
publish intent beyond `human_ic_required`. With `DRY_RUN=1`, the route stops at
Holus queue review and never calls a live publish API.

## Agents

- `campaign-evidence-auditor`
- `funnel-metrics-analyst`
