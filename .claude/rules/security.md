# Security Rules

## Secrets Management
- NEVER commit secrets, API keys, or credentials to the repository
- ALL secrets live in environment variables, loaded via pydantic-settings
- `.env` is in `.gitignore` — only `.env.example` is committed (with placeholder values)
- Never pass secrets as CLI arguments (visible in process list)
- Never put secrets in YAML config files

## Input Validation
- Validate ALL external input with Pydantic before processing
- External input = API requests, webhook payloads, user commands, file uploads
- Internal data (between Holus modules) uses dataclasses — trust within the system boundary

## Kill Switch
- Check kill switch BEFORE every agent action that has side effects
- Kill switch is checked via `@check_kill_switch` decorator or explicit call
- Three scopes: per-agent, per-domain, global — all must pass

## Trading Agent Security
- Signal Generator has ZERO access to broker APIs
- Execution Handler has ZERO AI reasoning capability
- Risk Manager ALWAYS runs on Opus (highest intelligence for safety-critical decisions)
- Maximum 2% risk per trade, 30% total portfolio exposure — enforced in code, not just prompts
- Circuit breaker: automatic shutdown on >5% drawdown in any 24-hour period
- All trades logged to append-only audit trail

## Agent Authority
- Follow the Agent Authority Matrix in AGENTS.md
- Autonomous actions: only within explicitly listed boundaries
- Ask First: always propose, never execute without approval
- Never: hard stop, escalate immediately, no exceptions

## Memory Isolation
- Each agent's Mem0 scope is isolated — agents cannot read each other's memory
- Cross-agent communication ONLY through the Redis event bus
- No agent can modify another agent's configuration or prompts

## Audit Trail
- All agent actions with side effects are logged to trajectory.jsonl (append-only)
- Financial actions get a separate audit log
- Logs include: agent_id, action, timestamp, input, output, verdict
- Never edit or delete audit entries

## Dependencies
- Pin all dependency versions in uv.lock
- Review new dependencies before adding (check maintenance status, security history)
- Prefer well-maintained packages with active security response teams
