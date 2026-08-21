# Company OS ownership

## Decision

Holus is the canonical owner of Company OS domain skills and their
project-specific evaluation contracts.

## Scope of this migration

This is an additive migration. The canonical skill packages live in
`.agents/skills/`; the discovery manifest is `agentic/manifest.yaml`; and the
project evaluation manifest is `agentic/evals.yaml`.

The shared helper is intentionally local to Holus. It retains deterministic
desk behavior while emitting only local artifacts and non-mutating handoff
payloads. It does not import generic evaluation, telemetry, dispatcher, or
orchestration machinery.

## Safety boundary

Company OS skills preserve Holus's review-before-post policy. Publishing,
scheduling, outreach, external contact, spend, CRM changes, credentials,
deployment, and production changes remain unavailable without separate explicit
authority. A tripped or unreadable `COMPANY_KILL` halts desk work.

## Fleet cleanup gate

Fleet retains its existing copies until all consumer updates and parity proofs
listed in `agentic/company-os-migration.yaml` are complete. That later removal
is intentionally not part of this change.
