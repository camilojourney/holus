# Company Marketing Desk Output Contract

Append one JSONL row to
`.self-improvement/automations/brand-marketing/events.jsonl`.

Required fields:

- `schema_version`: `1`
- `source`: `company-marketing-desk`
- `status`: `PASS`, `WARNING`, `NEEDS_MORE_EVIDENCE`, or `HALT`
- `summary`: concise marketing finding
- `kpis`: object with `reach`, `content_shipped`, `ctr`,
  `top_of_funnel_leads`, and `channel_cac`
- `spend_cap_status`: `WITHIN_CAP`, `HUMAN_IC_REQUIRED`, or `UNKNOWN`
- `approval_boundary`: `NONE` or `HUMAN_IC_REQUIRED`
- `human_ic_required`: boolean
- `silo_handoff`: includes Beehiiv evidence metadata and Holus `/post` dry-run
  queue review routing
- `notion_milestone`: local Notion journal handoff metadata
- `next`: smallest safe next action
- `evidence_paths`: repo-relative paths read during the run

Do not spend, launch paid campaigns, publish, or approve outreach.
