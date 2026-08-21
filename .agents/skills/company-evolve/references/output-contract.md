# Company Evolve Output Contract

Append one JSONL row to `.self-improvement/hub/experiment_reports.jsonl`.

Required fields:

- `schema_version`: `1`
- `source`: `company-evolve`
- `status`: `PASS`, `WARNING`, `NEEDS_MORE_EVIDENCE`, or `HALT`
- `what_to_improve`: one safe improvement recommendation
- `why_now`: evidence-based reason for the recommendation
- `source_event_paths`: desk event paths read
- `approval_boundary`: `NONE` or `HUMAN_IC_REQUIRED`
- `next`: smallest safe next action

Recommendations must be advisory. Do not change desk configs, launch
experiments, publish, send outreach, spend, or approve anything.
