# Company Brand Desk Output Contract

Append one JSONL row to
`.self-improvement/automations/brand-marketing/events.jsonl`.

Required fields:

- `schema_version`: `1`
- `source`: `company-brand-desk`
- `status`: `PASS`, `WARNING`, `NEEDS_MORE_EVIDENCE`, or `HALT`
- `summary`: concise desk finding
- `kpis`: object with `share_of_voice`, `sentiment`, `follower_delta`, and
  `voice_consistency_score` when evidence exists; otherwise use `null` values
- `approval_boundary`: `NONE` or `HUMAN_IC_REQUIRED`
- `human_ic_required`: boolean
- `silo_handoff`: includes the `taste` deep `brand-strategist` invoke path
- `notion_milestone`: local Notion journal handoff metadata
- `next`: smallest safe next action
- `evidence_paths`: repo-relative paths read during the run

Never write publish, outreach, spend, or approval rows. Route those to the
Company supervisor.
