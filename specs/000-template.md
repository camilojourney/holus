# Spec NNN: [Title]

**Status:** planned | in-progress | implemented | deprecated
**Phase:** Phase N
**Author:** [name]
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD

<!-- Guidance: match the spec's depth to the task's complexity.
     A one-day task needs Problem + Solution + Acceptance Criteria.
     A multi-week feature needs every section below.
     Delete any section that genuinely doesn't apply — an honest short
     spec beats a padded long one. -->

## Problem

<!-- Why does this need to be solved, and why now?
     Write from the user's perspective, not the system's.
     "Users cannot X, so they have to Y, which causes Z."
     Not: "The system does not support feature X." -->

## Goals

<!-- 3–7 bullets. Make them measurable where possible.
     "p99 caption burn < 5s" beats "improve caption performance." -->

- Goal 1
- Goal 2
- Goal 3

## Non-Goals

<!-- Things a reasonable reader might assume are in scope, but are explicitly excluded.
     Not negated goals ("the system won't crash") — things you're knowingly choosing
     not to solve here. Explain briefly why each is excluded. -->

- Non-goal 1 — reason
- Non-goal 2 — reason

## Solution

<!-- High-level approach. Focus on trade-offs, not step-by-step instructions.
     A diagram (ASCII or Mermaid) often communicates in 10 seconds what
     3 paragraphs cannot. Answer: "Could another engineer implement this
     correctly without being able to reach me?" If no, write more. -->

## API Contract

<!-- Delete this section for specs that don't introduce or change an endpoint. -->

```
METHOD /v1/endpoint

Request:
  field_name: type — description

Response (200):
  field_name: type — description

Errors:
  400 — when / why
  404 — when / why
  409 — when / why
```

## Implementation Notes

<!-- The technical meat. Use subsections freely:
     ### Phase 1 / Phase 2, ### Step 1, ### Pipeline, etc.
     Include code blocks (ffmpeg, Python, SQL) where they clarify.
     Include parameter tables with rationale columns.
     Keep this section honest — pseudo-code for novel logic,
     references for standard patterns. -->

### Key Parameters

<!-- Use a table when there are thresholds, constants, or config values. -->

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| example   | -35dB | industry standard for speech detection |

### Dependencies

<!-- Which other specs, services, or libraries does this depend on?
     Which specs depend on this one? -->

- Depends on: Spec NNN (reason)
- Depended on by: Spec NNN (reason)

## Alternatives Considered

<!-- For each rejected approach: describe it briefly, state the trade-off,
     explain why the chosen design is better given the stated goals.
     This section proves you explored the design space. -->

### Alternative A: [Name]

Trade-off: ...
Rejected because: ...

## Edge Cases & Failure Modes

<!-- What breaks the happy path? Enumerate explicitly.
     - What happens if the external dependency is unavailable?
     - What happens at the limits (0, 1, max)?
     - What happens if triggered twice concurrently?
     - What does a malformed input look like? -->

- Case 1: ...
- Case 2: ...

## Observability

<!-- How will we know if this is working? How will we know if it breaks?
     - Structured log events at stage boundaries
     - Metrics to track (latency, error rate, throughput)
     - Alert thresholds
     Omit for trivial specs. Required for anything that runs in production. -->

## Rollback Plan

<!-- What happens if this goes wrong after deploy?
     - Feature flag? Revert commit? Data migration undo?
     - What metric triggers rollback?
     - What is the system state if failure happens mid-way?
     Omit for specs that don't touch production. -->

## Open Questions

<!-- Things you don't know yet. This is not weakness — it's the most honest
     and useful part for reviewers. Mark each with who can answer it. -->

- [ ] Question 1 — @who
- [ ] Question 2 — @who

## Acceptance Criteria

<!-- Binary, testable checkboxes. Each verifiable from a test or log output
     without asking anyone. Not "it should be fast" — "p99 < 500ms under
     100 concurrent requests." Cover: happy path, error paths, edge cases. -->

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
