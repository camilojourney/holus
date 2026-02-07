# Security Baseline

## Non-Negotiables

- No secrets in repository, logs, or client bundles
- Validate all external and user input
- Enforce authentication and authorization on protected actions
- Principle of least privilege for services and data access

## Data Protection

- Encrypt data in transit
- Apply data minimization for stored PII
- Use parameterized queries / safe ORM patterns
- Protect destructive operations with explicit confirmation paths

## Dependency Hygiene

- Track dependency vulnerabilities
- Patch critical/high issues promptly
- Remove unused dependencies regularly

## Operational Security

- Keep audit logs for sensitive actions
- Rotate credentials on suspected compromise
- Maintain incident response and rollback procedures

## Escalation Triggers

Escalate immediately for:
- suspected data exposure
- authorization bypass
- secret leakage
- critical vulnerability with known exploit

## Security Checklist

- [ ] Input validation present
- [ ] Auth checks enforced
- [ ] Authorization boundaries enforced
- [ ] No sensitive data leakage in errors/logs
- [ ] Dependency audit reviewed
