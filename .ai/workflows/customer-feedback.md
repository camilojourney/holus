# Customer Feedback Workflow

> Feedback → Categorize → Synthesize → Route → Act

## Trigger

- Weekly cadence (every Monday)
- Support ticket volume spike
- User churn signal

---

## Phase 1: Collect

**Agent:** Strategist

### Sources

Gather feedback from all channels:

- [ ] Support tickets/emails
- [ ] In-app feedback
- [ ] Social media mentions
- [ ] Community/Discord
- [ ] Analytics (behavior patterns)
- [ ] Churn surveys

### Time Period
- Default: Last 7 days
- For monthly review: Last 30 days

---

## Phase 2: Categorize

**Agent:** Strategist

### Categories

| Category | Definition | Route To |
|----------|------------|----------|
| **Bug** | Something is broken | Builder |
| **Feature Request** | New capability wanted | Strategist (prioritize) |
| **UX Issue** | Works but confusing | Communicator + Builder |
| **Documentation Gap** | Can't find how to do X | Communicator |
| **Praise** | Positive feedback | Save for marketing |
| **Churn Signal** | Unhappy, might leave | Immediate attention |

### For Each Feedback Item

Document:
- Source (where it came from)
- Category (from above)
- Frequency (how many users mentioned this?)
- Urgency (is someone blocked?)
- Quote (verbatim user words)

---

## Phase 3: Synthesize

**Agent:** Strategist

### Pattern Recognition

Ask:
- What are the top 3 pain points this week?
- What feature requests are recurring?
- Are there clusters of similar issues?
- Is there a trend compared to last week?

### Quantify Impact

For each significant pattern:
- How many users affected?
- What's the severity (annoying vs blocking)?
- What's the churn risk?

---

## Phase 4: Route

**Agent:** Strategist

### Immediate Actions

| Signal | Action |
|--------|--------|
| Bug blocking users | Create P1 bug report → Builder |
| Churn risk (unhappy user) | Personal outreach → Founder |
| Quick doc fix | Create doc task → Communicator |
| UX confusion (multiple users) | Create UX improvement → Builder |

### Backlog Updates

For feature requests:
1. Add to backlog if new
2. Increment count if existing
3. Re-prioritize based on frequency

---

## Phase 5: Act

**Agent:** Varies by route

### For Bugs
Follow [investigate-bug.md](./investigate-bug.md) workflow

### For Feature Requests
1. Add to backlog with context
2. ICE score if promising
3. Create spec if prioritized

### For Documentation Gaps
1. Create doc improvement task
2. Assign to Communicator
3. Update within 1 week

### For Churn Risk
1. Immediate outreach
2. Understand root cause
3. Offer solution or workaround
4. Log outcome

---

## Weekly Summary Output

Use this format for the weekly synthesis:

```markdown
## Customer Feedback Summary: Week of [Date]

### Top Pain Points
1. **[Pain point]** - [X users] - [Category] - [Action]
2. **[Pain point]** - [X users] - [Category] - [Action]
3. **[Pain point]** - [X users] - [Category] - [Action]

### Recurring Feature Requests
| Request | Count (all time) | This Week | Status |
|---------|------------------|-----------|--------|
| [Request] | [N] | [+X] | [Backlog/Planned/Shipped] |

### Bugs Reported
- [ ] [Bug] - [Severity] - [Assigned/Fixed]

### Churn Signals
- [User]: [Issue] - [Outcome]

### Praise Highlights
> "[Quote]" - [User]

### Trends
- [Comparison to last week]
- [Emerging patterns]

### Action Items
- [ ] [Action] - [Owner] - [Due]
```

---

## Monthly Review

Once per month, deeper analysis:

### Questions to Answer
- What are the top 10 feature requests?
- What's our bug resolution time?
- Is satisfaction trending up or down?
- What's driving churn?
- What's delighting users?

### Metrics to Track
- Support ticket volume
- Time to first response
- Time to resolution
- Satisfaction rating (if collected)
- Churn rate

---

## Feedback Loop Closure

**Critical:** Close the loop with users.

When a requested feature ships:
- [ ] Notify users who requested it
- [ ] Thank them for the feedback
- [ ] Ask for feedback on the implementation

When a bug is fixed:
- [ ] Notify user who reported it
- [ ] Confirm it's resolved for them

This builds trust and encourages more feedback.
