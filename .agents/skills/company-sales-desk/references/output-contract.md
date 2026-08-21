# Company Sales Desk Output Contract

Append one JSONL row to `.self-improvement/automations/brand-sales/events.jsonl`.

Required fields:

- `schema_version`: `1`
- `source`: `company-sales-desk`
- `status`: `PASS`, `WARNING`, `NEEDS_MORE_EVIDENCE`, or `HALT`
- `summary`: concise sales finding
- `kpis`: object with `outreach_sent`, `reply_rate`, `qualified_leads`, and
  `meetings_booked`
- `approval_boundary`: `NONE` or `HUMAN_IC_REQUIRED`
- `human_ic_required`: boolean
- `silo_handoff`: includes Notion lead-capture validation metadata
- `notion_milestone`: local Notion journal handoff metadata
- `next`: smallest safe next action
- `evidence_paths`: repo-relative paths read during the run

Do not send outreach, book meetings, mutate a CRM, or approve a sales action.
