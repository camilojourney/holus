# Weekly Ops Workflow

> Recurring operational cadence for solo founder

## Schedule

| Day | Activity | Agent | Time |
|-----|----------|-------|------|
| Monday | Plan the week | Strategist | 30 min |
| Daily | Ship and track | All | Ongoing |
| Friday | Review and report | Strategist | 30 min |
| Sunday | Rule maintenance | Strategist | 15 min |

---

## Monday: Plan the Week

**Agent:** Strategist

### Morning Routine

1. **Review last week:**
   - What shipped?
   - What carried over?
   - Any surprises?

2. **Check inputs:**
   - New customer feedback
   - New bug reports
   - New feature requests
   - Business metrics

3. **Set priorities:**
   - Pick top 3-5 items for the week
   - Assign priorities (P0-P3)
   - Ensure each has clear scope

4. **Update current-priorities.md:**
   ```markdown
   # Current Priorities (Week of [Date])
   
   ## This Week
   1. [P1] [Item] - [Why]
   2. [P2] [Item] - [Why]
   3. [P2] [Item] - [Why]
   
   ## Blockers
   - [If any]
   
   ## Carry Over
   - [Items from last week]
   ```

5. **Check calendar:**
   - Any external commitments?
   - Any deadlines?
   - Adjust capacity accordingly

### Output
- [ ] `contexts/current-priorities.md` updated
- [ ] Top 3-5 items identified
- [ ] No blockers (or blockers escalated)

---

## Daily: Ship and Track

**Agents:** All

### Daily Flow

**Morning (5 min):**
- What's the most important thing today?
- Any blockers?
- Check for urgent issues

**During Day:**
- Work on priority items
- Ship when ready
- Update progress as needed

**End of Day (5 min):**
- Did it ship?
- What blocked?
- Are priorities still correct?

### Daily Standup Format (if tracking)

```markdown
## [Date]

### Done
- [x] [Item completed]

### Today
- [ ] [Item planned]

### Blockers
- [If any]
```

---

## Friday: Review and Report

**Agent:** Strategist

### Afternoon Routine

1. **Tally what shipped:**
   - Features
   - Bugs fixed
   - Documentation updated
   - Experiments run

2. **Review metrics:**
   - Check key metrics (if available)
   - Any significant changes?
   - Note learnings

3. **Customer feedback synthesis:**
   - Run [customer-feedback.md](./customer-feedback.md) workflow
   - Document patterns

4. **Kill stale experiments:**
   - Any experiments past kill date?
   - If no success, document and kill

5. **Prepare for next week:**
   - What's carrying over?
   - Any new priorities?
   - Any deadlines approaching?

6. **Write weekly update** (use `templates/weekly-update.md`):
   ```markdown
   # Week of [Date]
   
   ## Shipped
   - [Feature/fix]
   
   ## Metrics
   - [Key metric]: [Value] ([Change])
   
   ## Learned
   - [Insight from feedback/data]
   
   ## Next Week
   - [Priority 1]
   - [Priority 2]
   ```

### Output
- [ ] Weekly update written
- [ ] Metrics reviewed
- [ ] Feedback synthesized
- [ ] Stale experiments killed
- [ ] Next week planned

---

## Sunday: Rule Maintenance

**Agent:** Strategist

### 15-Minute Review

1. **Review AI rule usage:**
   - Did rules help or hinder this week?
   - Any rules unclear or missing?
   - Any escalations that suggest rule changes?

2. **Update rules if needed:**
   - Make changes to `.ai/`
   - Update `CHANGELOG.md`
   - Bump `.version` if MINOR/MAJOR change

3. **Git commit:**
   ```bash
   git add .ai/
   git commit -m "chore(.ai): weekly review, [brief description]"
   git tag v1.0.X  # if version bumped
   ```

### Output
- [ ] Rules reviewed
- [ ] Changes committed (if any)
- [ ] Version bumped (if applicable)

---

## Monthly: Deeper Review

**Agent:** Strategist (with Operator for unit economics)

### Monthly Cadence (First Monday of Month)

1. **Unit economics review:**
   - MRR and trend
   - CAC and LTV calculation
   - Churn rate
   - Runway update

2. **Product review:**
   - What shipped this month?
   - What moved metrics?
   - What didn't work?

3. **Competitive check:**
   - Any new competitors?
   - Any market changes?
   - Adjust strategy if needed

4. **Planning:**
   - Next month's goals
   - OKRs or key results (simple)

### Monthly Output Template

```markdown
# Monthly Review: [Month Year]

## Business Health
| Metric | This Month | Last Month | Trend |
|--------|------------|------------|-------|
| MRR | $X | $Y | ↑/↓ |
| New Users | X | Y | ↑/↓ |
| Churn | X% | Y% | ↑/↓ |
| Runway | X mo | Y mo | ↑/↓ |

## What Shipped
- [Feature 1]
- [Feature 2]

## What Worked
- [Thing that moved metrics]

## What Didn't Work
- [Thing that didn't move metrics]

## Next Month Goals
1. [Goal 1]
2. [Goal 2]
3. [Goal 3]

## Key Decisions Made
- [Decision and rationale]
```

---

## Quick Reference: Recurring Tasks

| Task | Frequency | Agent | Time |
|------|-----------|-------|------|
| Set weekly priorities | Monday | Strategist | 30 min |
| Customer feedback synthesis | Weekly (Friday) | Strategist | 30 min |
| Weekly update | Friday | Strategist | 15 min |
| Dependency audit | Weekly | Operator | 10 min |
| Rule maintenance | Sunday | Strategist | 15 min |
| Unit economics | Monthly | Strategist | 30 min |
| Competitive check | Monthly | Strategist | 30 min |
