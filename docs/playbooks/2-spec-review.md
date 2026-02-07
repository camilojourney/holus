# Phase 2: Specification Review

Audit specs before implementation.

## Review Goals

- detect ambiguity and contradictions
- find missing edge cases
- verify security/access assumptions
- identify implementation order/dependencies

## Output

- completeness matrix
- ambiguity list with rewrite suggestions
- missing edge cases with impact
- blocking vs non-blocking issues
- verdict: READY / NEEDS CLARIFICATION / NOT READY

## Prompt Template

```text
Review this spec for ambiguity, missing edge cases, and security gaps.
Return a blocking/non-blocking issue list and a clear verdict.
```
