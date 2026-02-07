# Investigate Bug Workflow

> Bug report → Triage → Root cause → Fix → Verify → Ship

## Trigger

- Bug report received (any source)
- Error spike in monitoring
- User complaint

---

## Phase 1: Triage

**Agent:** Strategist (severity assessment)

### Inputs Required
- [ ] Bug description
- [ ] Reproduction steps (if available)
- [ ] Error logs/screenshots (if available)

### Activities

1. **Assess severity:**

   | Severity | Definition | Response Time |
   |----------|------------|---------------|
   | **P0** | Site down, data loss, auth bypass | Immediate |
   | **P1** | Core feature broken for all users | < 4 hours |
   | **P2** | Feature broken for some users | < 1 day |
   | **P3** | Minor issue, workaround exists | This sprint |

2. **Gather context:**
   - When did this start?
   - Who is affected?
   - Is there a workaround?

3. **Route to Builder:**
   - Assign priority
   - Provide all context gathered

### Outputs
- [ ] Severity assigned (P0-P3)
- [ ] Context documented
- [ ] Routed to Builder

### Escalate If
- P0 or P1 severity
- Data at risk
- Security issue suspected

---

## Phase 2: Investigate

**Agent:** Builder

### Inputs Required
- [ ] Bug report with severity
- [ ] Reproduction steps (or best guess)

### Activities

1. **Reproduce the bug:**
   - Try to reproduce locally
   - Check different browsers/conditions
   - Document exact reproduction steps

2. **Find root cause:**
   - Check recent changes (git log)
   - Trace code path
   - Check error logs

3. **Document findings:**
   - What's the root cause?
   - What's the impact?
   - What's the fix approach?

### Outputs
- [ ] Bug reproduced (or confirmed unreproducible)
- [ ] Root cause identified
- [ ] Fix approach documented

### Escalate If
- Cannot reproduce after 30 minutes
- Root cause unclear after 1 hour
- Fix requires architectural change
- Bug is actually a security issue

---

## Phase 3: Fix

**Agent:** Builder

### Inputs Required
- [ ] Root cause identified
- [ ] Fix approach approved (if escalated)

### Activities

1. **Create fix:**
   - Write minimal fix for the issue
   - Don't fix unrelated things (scope creep)

2. **Write regression test:**
   - Test must fail without fix
   - Test must pass with fix
   - Prevents bug from recurring

3. **Self-review:**
   - Security checklist
   - Does fix introduce new issues?
   - Edge cases covered?

### Outputs
- [ ] Fix implemented
- [ ] Regression test written
- [ ] Self-review complete

### Escalate If
- Fix is more complex than expected
- Fix might break other things
- Uncertain about approach

---

## Phase 4: Verify & Ship

**Agent:** Builder + Operator

### Activities

1. **Verify fix:**
   ```bash
   flake8 core/ agents/ tools/
   python -m pytest tests/
   No build step (runtime Python app)
   ```

2. **Deploy based on severity:**

   | Severity | Deployment Path |
   |----------|-----------------|
   | P0 | Hotfix directly to main |
   | P1 | Fast-track PR, deploy same day |
   | P2 | Normal PR, deploy when ready |
   | P3 | Normal PR, batch with other changes |

3. **Confirm fix in production:**
   - Verify bug is fixed
   - Monitor for side effects
   - Close the bug report

### Outputs
- [ ] Fix deployed
- [ ] Bug confirmed fixed in production
- [ ] Bug report closed

---

## Post-Mortem (P0/P1 only)

For P0 and P1 bugs, document:

```markdown
## Bug Post-Mortem: [Bug Title]

### What happened?
[Description of the bug and its impact]

### Timeline
- [Time]: Issue reported
- [Time]: Investigation started
- [Time]: Root cause identified
- [Time]: Fix deployed

### Root cause
[Technical explanation]

### Fix
[What was changed]

### Prevention
- [ ] [Action to prevent recurrence]
- [ ] [Test added]
- [ ] [Process change if needed]

### Learnings
[What we learned]
```

---

## Quick Reference

### Reproduction Checklist
- [ ] Which browser/device?
- [ ] Logged in or anonymous?
- [ ] Specific user data?
- [ ] Network conditions?
- [ ] Time-dependent?

### Common Root Causes
- Race condition
- Null/undefined not handled
- API contract changed
- Environment variable missing
- Caching issue
- Third-party API failure

### Fix Quality Checklist
- [ ] Addresses root cause (not just symptom)
- [ ] Has regression test
- [ ] Doesn't break other things
- [ ] Is minimal (no scope creep)
