# Testing Standards

## Test Strategy

Use a balanced pyramid:

- Unit tests: pure functions and domain logic
- Integration tests: module boundaries, API handlers, data flow
- E2E tests: critical user journeys only

## Rules

- Every bug fix gets a regression test
- Tests must be deterministic and isolated
- Avoid brittle tests coupled to implementation details
- Prefer behavior assertions over internal state assertions

## Structure (AAA)

- Arrange: setup inputs and dependencies
- Act: execute behavior
- Assert: verify outcomes

## What to Cover

- Happy paths
- Validation failures
- Permission/security boundaries
- Timeout/retry behavior
- Concurrency/race-sensitive paths (when relevant)

## Pull Request Gate

- [ ] New behavior covered by tests
- [ ] Existing tests still pass
- [ ] Test names describe intent clearly
- [ ] Flaky tests removed or fixed before merge
