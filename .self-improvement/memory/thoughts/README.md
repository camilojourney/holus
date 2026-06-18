# Thought Evolution Memory

This folder is the operating memory for the `$thought` loop. It tracks how one
raw thought improves Holus itself: app UX, content quality, pipeline logic,
agent prompts, creative systems, variable weights, and harness readiness.

Every `$thought` run should update at least one file here when it learns
something durable.

## Files

- `update-backlog.yaml`: prioritized improvements for app UX, pipeline, agents,
  prompts, harness, evals, and skills.
- `variable-weight-ledger.yaml`: the variables Holus judges, their weights, and
  what evidence changes them.
- `agent-harness-registry.yaml`: agents, models, prompts, reviewers, and when to
  add/change them.
- `creative-diversity-ledger.yaml`: how Holus avoids generating the same content
  shape every time.
- `skill-update-backlog.yaml`: improvements needed in Codex skills, especially
  `$thought`, `/ux`, `/taste`, `/code`, and reviewer skills.
- `change-log.jsonl`: append-only trace of important `$thought` improvements.

## Run Rule

For each `$thought` run, record:

- what the app made
- what did not make sense
- what was changed or should change next
- which variable weights were used or questioned
- which UX/app surfaces need review
- which agents/prompts/harness pieces need updates
- whether the output was novel enough or too same-y

