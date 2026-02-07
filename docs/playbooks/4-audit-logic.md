# Phase 4: Logic Audit

Perform adversarial review for correctness and security.

## Checklist

- requirement coverage vs specs
- null/empty/error path handling
- race/concurrency risks
- authorization and data access boundaries
- input validation and output safety
- regression risk from changed code paths

## Output

- critical findings
- warnings
- suggested minimal fixes
- verdict: READY / NEEDS WORK / NOT READY

## Prompt Template

```text
Audit this implementation like a hostile reviewer.
Find correctness and security issues with concrete evidence.
```
