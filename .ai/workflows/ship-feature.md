# Ship Feature Workflow

> End-to-end feature delivery: Plan → Build → Verify → Ship

## Trigger

- New spec exists in `/specs/`
- Priority assigned (P0-P3)
- Acceptance criteria defined

---

## Phase 1: Plan

**Agent:** Strategist (if spec incomplete) + Builder (for technical plan)

### Inputs Required
- [ ] Spec file in `/specs/`
- [ ] User story or problem statement
- [ ] Acceptance criteria
- [ ] Priority (P0-P3)

### Activities

1. **Review spec for completeness**
   - Does it have clear acceptance criteria?
   - Are edge cases defined?
   - Is scope bounded?

2. **Create implementation plan** (if work > 2 hours)
   - Components to create/modify
   - Database changes (if any)
   - API contracts
   - Test cases

3. **Estimate and validate**
   - How long will this take?
   - Are there dependencies?
   - Any blockers?

### Outputs
- [ ] Implementation plan (if needed)
- [ ] Estimate confirmed
- [ ] Dependencies identified

### Escalate If
- Spec is ambiguous
- Estimate > 2 days
- Database schema change required
- Breaking API change required

---

## Phase 2: Build

**Agent:** Builder

### Inputs Required
- [ ] Approved spec
- [ ] Implementation plan (if created)
- [ ] Branch created: `feature/[name]`

### Activities

1. **Implement in order:**
   - Database schema (if needed)
   - Types/interfaces
   - Business logic
   - API routes
   - UI components

2. **Write tests alongside:**
   - Unit tests for business logic
   - Integration tests for API
   - Component tests for UI

3. **Self-review:**
   - Security checklist
   - Performance checklist
   - Code quality checklist

### Outputs
- [ ] Feature code complete
- [ ] Tests written and passing
- [ ] Self-review checklist complete

### Escalate If
- Security concern discovered
- Performance issue identified
- Scope creep detected
- Blocked by technical issue

---

## Phase 3: Verify

**Agent:** Builder + Operator

### Inputs Required
- [ ] Code complete
- [ ] Tests passing locally

### Activities

1. **Run full verification:**
   ```bash
   flake8 core/ agents/ tools/
   python -m pytest tests/
   No build step (runtime Python app)
   ```

2. **Deploy to staging:**
   - Merge to staging branch or use preview
   - Verify feature works end-to-end
   - Test edge cases

3. **Code review** (self-review with fresh eyes):
   - Wait 1 hour if possible
   - Review with security checklist
   - Check for missed edge cases

### Outputs
- [ ] All checks passing
- [ ] Staging verified
- [ ] Ready for production

### Escalate If
- Tests failing
- Build broken
- Staging reveals issues

---

## Phase 4: Ship

**Agent:** Operator + Communicator

### Inputs Required
- [ ] Verification complete
- [ ] PR approved (self-reviewed)

### Activities

1. **Merge and deploy:**
   - Merge to main
   - Verify deployment pipeline succeeds
   - Monitor for 30 minutes

2. **Document:**
   - Changelog entry (use `templates/changelog-entry.md`)
   - Update docs if user-facing (Communicator)

3. **Monitor:**
   - Watch error rates
   - Check key metrics
   - Verify feature accessible

### Outputs
- [ ] Feature deployed to production
- [ ] Changelog updated
- [ ] Documentation updated (if needed)
- [ ] No errors in monitoring

### Escalate If
- Deploy fails
- Errors in production
- Rollback needed

---

## Rollback Plan

If something goes wrong after deploy:

1. **Quick rollback:**
   ```bash
   git revert HEAD
   git push
   ```
   Or use your deployment platform UI to roll back to the previous release.

2. **If data migration was involved:**
   - Execute down migration
   - Verify data integrity

3. **Communicate:**
   - If user-facing issue, post status update
   - Document what happened for post-mortem

---

## Definition of Done

Feature is **not done** until:

- [ ] Code merged to main
- [ ] Tests passing in CI
- [ ] Deployed to production
- [ ] Monitored for 30 minutes (no errors)
- [ ] Changelog entry added
- [ ] Documentation updated (if user-facing)
- [ ] Rollback plan documented

---

## Timeline Guidelines

| Priority | Target Completion |
|----------|-------------------|
| P0 | Same day |
| P1 | 1-2 days |
| P2 | 3-5 days |
| P3 | This sprint |
