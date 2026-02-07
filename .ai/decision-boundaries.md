# Decision Boundaries: Authority Matrix

> This document defines what each agent can decide autonomously vs. when they must ask for human approval.

## Authority Levels

| Level | Meaning | Example |
|-------|---------|---------|
| **AUTONOMOUS** | Decide and execute immediately | Write unit tests for new function |
| **ASK FIRST** | Propose solution, wait for approval | Add new npm dependency |
| **ESCALATE** | Must involve human, too risky alone | Deploy database migration to production |
| **NEVER** | Forbidden, will cause problems | Commit secrets to repository |

---

## Builder Agent

| Decision | Authority Level | Example | Rationale |
|----------|----------------|---------|-----------|
| Choose between functional vs class components | **AUTONOMOUS** | Use functional + hooks for React | Established pattern in modern React |
| Add lodash for one utility function | **ASK FIRST** | "Should I add lodash for debounce, or write custom?" | Dependency cost (bundle size, maintenance) |
| Refactor 5+ files for consistency | **ASK FIRST** | "Refactor all API routes to use new middleware?" | Blast radius, risk of introducing bugs |
| Write unit tests for pure functions | **AUTONOMOUS** | Tests for validation logic, formatters | Standard practice, low risk |
| Skip tests for prototype/experiment | **ASK FIRST** | "Skip tests for this quick experiment?" | Risk assessment depends on context |
| Use `any` type in TypeScript | **NEVER** | Don't bypass type safety | Defeats purpose of TypeScript |
| Fix typo in variable name | **AUTONOMOUS** | Rename `usrName` to `userName` | Low-risk refactor |
| Rename core domain entity | **ASK FIRST** | Rename `Project` to `Workspace` throughout | High blast radius, affects mental model |
| Add console.log for debugging | **AUTONOMOUS** | Temporary debugging, removed before commit | Low risk if cleaned up |
| Disable linter rule project-wide | **ASK FIRST** | "Disable no-explicit-any rule?" | Affects code quality standards |
| Bypass authorization policy for admin dashboard | **ESCALATE** | Security decision | Security severity HIGH |
| Optimize database query with index | **AUTONOMOUS** | Add index to frequently queried column | Performance improvement, standard practice |
| Change database schema (new column) | **ASK FIRST** | Add optional column with migration | Requires migration, can affect production |
| Change database schema (remove column) | **ESCALATE** | Remove column (data loss risk) | Irreversible, data at risk |
| Use third-party API client library | **ASK FIRST** | "Use official SDK or write custom?" | Dependency decision |
| Implement caching for slow endpoint | **AUTONOMOUS** | Add Redis cache with TTL | Standard performance optimization |
| Change authentication flow | **ESCALATE** | Switch from JWT to sessions | Security + breaking change |
| Add feature flag for new feature | **AUTONOMOUS** | Wrap feature in flag for gradual rollout | Best practice for safe deploys |
| Remove feature flag after rollout | **ASK FIRST** | "Feature stable, remove flag?" | Cleanup decision |

---

## Operator Agent

| Decision | Authority Level | Example | Rationale |
|----------|----------------|---------|-----------|
| Deploy to staging | **AUTONOMOUS** | Deploy PR to staging after tests pass | Standard flow, low risk |
| Deploy to production | **ASK FIRST** | "Ready to ship v1.2 to production?" | Irreversible action, affects users |
| Roll back production deploy (P0 incident) | **AUTONOMOUS** | Critical bug detected, immediate rollback | Incident response, time-sensitive |
| Roll back production deploy (no incident) | **ASK FIRST** | "Revert last deploy due to performance concerns?" | Non-critical, can discuss approach |
| Modify Dockerfile | **ASK FIRST** | "Add Redis to Docker compose?" | Infrastructure change, affects all devs |
| Increase serverless timeout 10s → 30s | **AUTONOMOUS** | Fix timeout errors | Within reasonable limits |
| Increase serverless timeout 30s → 5min | **ASK FIRST** | "Lambda needs 5min timeout for batch job?" | Cost/architecture concern |
| Add monitoring alert | **AUTONOMOUS** | Alert when error rate >1% | Observability improvement |
| Change alert thresholds | **AUTONOMOUS** | Reduce noise by tuning thresholds | Operational improvement |
| Disable noisy alert | **ASK FIRST** | "Disable alert that's 90% false positive?" | Might miss real issues |
| Rotate API keys after leak | **AUTONOMOUS** | Security incident response | Time-sensitive security action |
| Change API rate limits | **ASK FIRST** | "Increase rate limit for enterprise tier?" | Affects user experience + costs |
| Apply security patch | **AUTONOMOUS** | Update dependency with CVE fix | Security best practice |
| Upgrade framework major version | **ASK FIRST** | "Upgrade framework major version?" | Breaking changes likely |
| Scale up servers during traffic spike | **AUTONOMOUS** | Auto-scaling or manual scaling | Operational response |
| Add new third-party service | **ASK FIRST** | "Add Sentry for error tracking?" | Cost + vendor lock-in |
| Run database backup manually | **AUTONOMOUS** | Extra backup before risky operation | Safety measure |
| Restore from backup | **ESCALATE** | Data restoration needed | Data integrity critical |
| Enable feature flag for 100% users | **ASK FIRST** | "Roll out feature to everyone?" | Affects all users |
| Kill feature flag (emergency) | **AUTONOMOUS** | Feature causing P0, disable immediately | Incident response |

---

## Communicator Agent

| Decision | Authority Level | Example | Rationale |
|----------|----------------|---------|-----------|
| Fix typo in documentation | **AUTONOMOUS** | Correct spelling error | Low risk, improves quality |
| Rewrite documentation section | **AUTONOMOUS** | Improve clarity of getting-started guide | Content improvement within scope |
| Add new documentation page | **AUTONOMOUS** | Document new feature | Standard process |
| Remove documentation page | **ASK FIRST** | "Remove outdated tutorial?" | Might break existing links/workflows |
| Change button label text | **AUTONOMOUS** | "Submit" → "Save Changes" | UI microcopy improvement |
| Change core terminology | **ASK FIRST** | Rename "Snapshots" to "Versions" throughout | Affects mental model, can confuse users |
| Write standard support response | **AUTONOMOUS** | Reply to how-to question | Routine support |
| Offer refund to customer | **ASK FIRST** | "Issue refund for billing error?" | Financial decision |
| Write blog post | **ASK FIRST** | "Publish tutorial on our blog?" | Public-facing content |
| Update error message | **AUTONOMOUS** | Make error message clearer | UX improvement |
| Change 404 page design | **AUTONOMOUS** | Improve empty state | Non-critical page |
| Change homepage hero text | **ASK FIRST** | "Update value proposition on homepage?" | First impression, affects conversions |
| Create social media post | **ASK FIRST** | "Tweet about new feature?" | Brand voice, public statement |
| Respond to negative review | **ASK FIRST** | Negative review needs response | Sensitive, public |
| Update legal disclaimers | **ESCALATE** | Change privacy policy, ToS | Legal implications |
| Change accessibility features | **AUTONOMOUS** | Add alt text, improve contrast | Compliance + UX improvement |
| Redesign entire UI | **ESCALATE** | Major design overhaul | Huge user impact |
| A/B test new headline | **ASK FIRST** | "Test two different headlines?" | Experiment needs approval |

---

## Strategist Agent

| Decision | Authority Level | Example | Rationale |
|----------|----------------|---------|-----------|
| Prioritize P1 bugs over P2 features | **AUTONOMOUS** | Bug in onboarding flow blocks users | Clear severity hierarchy |
| Prioritize P2 feature over P2 bug | **ASK FIRST** | "Ship feature X before fixing bug Y?" | Business judgment call |
| Add feature to backlog | **AUTONOMOUS** | User-requested feature, log for later | Doesn't commit to building |
| Commit to building major feature | **ASK FIRST** | "Build workflow comparison view next quarter?" | Resource commitment |
| Calculate CAC from attribution data | **AUTONOMOUS** | Sum ad spend / new signups | Deterministic math |
| Recommend pricing change | **ESCALATE** | "Should we raise prices 20%?" | Business-critical decision |
| Kill failed experiment | **AUTONOMOUS** | Experiment hit kill criteria, no impact | Data-driven decision |
| Kill successful feature | **ESCALATE** | "Remove popular feature that loses money?" | Major decision, user impact |
| Synthesize weekly user feedback | **AUTONOMOUS** | Summarize support tickets + feedback | Information gathering |
| File bug from user report | **AUTONOMOUS** | User reported crash, create issue | Routine triage |
| Deprioritize founder's feature idea | **ASK FIRST** | "User data suggests different priority?" | Potential disagreement |
| Run growth experiment (no code) | **AUTONOMOUS** | Test email subject lines | Low-risk experiment |
| Run growth experiment (requires build) | **ASK FIRST** | "Build referral program to test viral growth?" | Resource commitment |
| Allocate budget to marketing channel | **ASK FIRST** | "$5k/month to Google Ads?" | Financial decision |
| Define success metrics for feature | **AUTONOMOUS** | Feature should increase retention 10% | Accountability setting |
| Change North Star metric | **ESCALATE** | Switch from DAU to revenue | Strategic pivot |
| Approve customer case study | **ASK FIRST** | "Feature customer in marketing?" | Public commitment |
| Sunset low-usage feature | **ASK FIRST** | "Remove feature used by <5% users?" | User impact, potential backlash |
| Scope down feature to ship faster | **AUTONOMOUS** | Cut nice-to-haves to hit deadline | Pragmatic tradeoff |

---

## Cross-Agent Examples

### Scenario: Database is slow

| Agent | Decision | Authority | Rationale |
|-------|----------|-----------|-----------|
| **Builder** | Add database index | AUTONOMOUS | Standard optimization |
| **Builder** | Rewrite query using raw SQL | AUTONOMOUS | Performance fix |
| **Operator** | Scale up database tier | ASK FIRST | Cost impact |
| **Strategist** | Deprioritize features until fixed | AUTONOMOUS | Resource allocation |

### Scenario: Customer requests feature

| Agent | Decision | Authority | Rationale |
|-------|----------|-----------|-----------|
| **Communicator** | Respond to customer | AUTONOMOUS | Standard support |
| **Strategist** | Add to backlog | AUTONOMOUS | Information gathering |
| **Strategist** | Prioritize for next sprint | ASK FIRST | Resource commitment |
| **Builder** | Build the feature | AUTONOMOUS (after approval) | Implementation |

### Scenario: Security vulnerability found

| Agent | Decision | Authority | Rationale |
|-------|----------|-----------|-----------|
| **Builder** | Fix vulnerability | ESCALATE | Security severity HIGH |
| **Operator** | Deploy patch immediately | AUTONOMOUS (after fix) | Security incident |
| **Communicator** | Draft disclosure notice | ASK FIRST | Legal + brand implications |
| **Strategist** | Allocate time for security audit | AUTONOMOUS | Resource allocation |

---

## Escalation Triggers (All Agents)

**ALWAYS escalate when:**
- Security vulnerability (Medium severity or higher)
- Data loss risk
- Breaking change to user-facing API
- Work estimate > 1 day without prior approval
- Legal/compliance implications
- Affects >50% of users
- Cost impact > $500 / month
- Confidence level is low (<70% sure)

**NEVER escalate trivially:**
- Standard bug fixes
- Documentation updates
- Code formatting
- Adding tests
- Performance optimizations (unless architecture change)

---

## How to Escalate

1. **Stop work immediately** - Don't proceed until resolved
2. **Document the decision needed:**
   - What are we deciding?
   - What are the options?
   - What do you recommend and why?
   - What happens if we don't decide?
3. **Provide context:**
   - Link to relevant specs, issues, or code
   - Data supporting your recommendation
   - Time sensitivity (how long can this wait?)
4. **Propose next steps** - Make it easy to approve
5. **Wait for explicit approval** - Don't assume silence is consent

---

## When Humans Disagree with Agent Decision

If agent made autonomous decision and human disagrees:

1. **Roll back if possible** - Undo the change
2. **Document the disagreement** - Update this file if recurring
3. **Learn the pattern** - Adjust decision boundaries
4. **Update agent rules** - Prevent similar issues

This is a living document - update as you discover new edge cases.

---

## Special Cases

### Working Hours

Agents may operate autonomously during off-hours for:
- Incident response (P0/P1)
- Security patches
- Automated deployments (if configured)

But must still escalate for:
- Irreversible changes
- Customer-facing communication
- Financial decisions

### Beta/Experimental Features

For features marked as beta:
- Agents have MORE autonomy (faster iteration)
- But must still respect security boundaries
- Can break things in beta, not in stable

### Compliance-Regulated Features

For features under compliance (GDPR, HIPAA, etc.):
- ALWAYS escalate any changes
- Legal review required
- Documentation updates required
- Audit trail required

---

## Version History

- **v1.0** - Initial decision boundaries
- Update this when boundaries change based on learnings
