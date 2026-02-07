# API Design Standards

## Design Principles

- Consistent resource naming
- Explicit auth requirements per endpoint
- Input validation at boundaries
- Stable, documented response shapes
- Backward compatibility by default

## Request/Response Rules

- Validate request payloads and query params
- Return machine-readable error codes plus human-readable messages
- Include trace/request id in error responses when possible
- Never leak internals/secrets in responses

## Versioning

- Prefer additive changes
- Mark deprecated fields before removal
- Document breaking changes and migration path

## Status Codes

- `2xx` success
- `4xx` client validation/auth/permission issues
- `5xx` unexpected server failures

## Security Baseline

- Authn/authz checks before data access
- Rate limit sensitive endpoints
- Verify webhook signatures
- Enforce least-privilege data access

## Endpoint Checklist

- [ ] Auth requirement documented
- [ ] Input validation defined
- [ ] Errors documented with examples
- [ ] Idempotency/retry behavior considered (if write endpoint)
