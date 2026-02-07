# Phase 1: Specification Creation

Create implementation-ready specs that are precise and testable.

## Output Structure

- Feature name and overview
- User stories
- Numbered specs (`SPEC-001`, `SPEC-002`...)
- Acceptance criteria per spec (binary)
- Data/API changes (if any)
- Edge cases (`EDGE-001`, `EDGE-002`...)
- State definitions (loading/empty/error/success)
- Security considerations
- Out of scope
- Open questions

## Prompt Template

```text
Write a detailed specification for [feature].
Use numbered specs and binary acceptance criteria.
Do not include implementation details.
Include edge cases, error messages, and security considerations.
```

## Done When

- All critical behavior is covered
- No vague language remains
- Error cases and recovery paths are explicit
