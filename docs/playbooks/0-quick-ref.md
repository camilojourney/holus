# Quick Reference

## Flow

SPEC -> REVIEW -> IMPLEMENT -> LOGIC AUDIT -> INTENT AUDIT -> FIX -> SHIP

## Prompt Starters

- Spec: "Read 1-spec-create.md and help me spec [feature]"
- Review: "Read 2-spec-review.md and audit this spec"
- Implement: "Read 3-implement.md and implement SPEC-001"
- Logic audit: "Read 4-audit-logic.md and find bugs"
- Intent audit: "Read 5-audit-intent.md and verify user intent"
- Fix: "Read 6-fix-iterate.md and apply only listed fixes"
- Hotfix: "Read hotfix.md and fix this production bug"

## Always Check

- Acceptance criteria are binary and testable
- Loading/empty/error/success states are defined
- Security and authorization boundaries are explicit
- Lint, tests, and build pass
