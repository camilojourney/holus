# Company Content Desk Output Contract

Append one JSONL row to
`.self-improvement/automations/brand-content/events.jsonl`.

Required fields:

- `schema_version`: `1`
- `source`: `company-content-desk`
- `status`: `PASS`, `WARNING`, `NEEDS_MORE_EVIDENCE`, or `HALT`
- `summary`: concise content finding
- `kpis`: object with `pipeline_depth`, `genpeli_jobs_completed`, and
  `queue_depth`
- `approval_boundary`: `NONE` or `HUMAN_IC_REQUIRED`
- `human_ic_required`: boolean
- `silo_handoff`: includes the Genpeli `/consult-editing genpeli` handoff
- `notion_milestone`: local Notion journal handoff metadata
- `next`: smallest safe next action
- `evidence_paths`: repo-relative paths read during the run

Do not publish, schedule, cross-post, or approve content.
