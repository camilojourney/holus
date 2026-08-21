# Company Supervisor Output Contract

Write `.self-improvement/hub/company_docket.json` with:

- `schema_version`: `1`
- `updated_at_utc`: UTC ISO-8601 timestamp
- `queues`: object containing `human_ic_required`, `ready_for_code`, and
  `needs_more_evidence`
- `source_counts`: counts of desk events and fix-required rows read
- `output_paths`: paths written by the run

Append one JSONL row to
`.self-improvement/automations/supervisor/events.jsonl` with:

- `schema_version`: `1`
- `source`: `company-supervisor`
- `status`: `PASS`, `WARNING`, `NEEDS_MORE_EVIDENCE`, or `HALT`
- `pending_human_ic`: count of human-gated items
- `docket_queue_depth`: total open queue items
- `selected_ready_for_code`: selected lane object or `null`
- `next`: smallest safe next action

Never create approval rows. `ready_for_code` must contain zero or one item.
