# Security Checklist — Holus Autonomous Content Engine

## API Keys & Credentials

- [ ] All API keys in `.env` only (never in code, never in git)
- [ ] `.env` is in `.gitignore`
- [ ] Social media OAuth tokens stored in social-media-automatization DB (not in Holus)
- [ ] LLM proxy token is `Bearer local` (localhost only, no external exposure)
- [ ] Telegram bot token in env var `TELEGRAM_BOT_TOKEN`

## Publishing Permissions

- [ ] Brand-safety judge is a HARD gate (cannot be bypassed)
- [ ] `guardrails.yaml` requires human approval to modify
- [ ] Kill switch activates on 3+ consecutive failures
- [ ] Auto-publish only for judge score >= 0.8 (PASS threshold)
- [ ] PARTIAL content (0.5-0.8) ALWAYS requires human review
- [ ] No content about trading, financial advice, or investment
- [ ] Forbidden topics list in `quality_score.py` CONTENT_ANTI_PATTERNS

## Agent Boundaries

- [ ] Agents cannot modify `guardrails.yaml`
- [ ] Agents cannot access pythia/milo (trading repos)
- [ ] Agents cannot force-push to git
- [ ] Agents cannot modify their own judge rubrics
- [ ] Judge is frozen for 90 days from activation

## Data Isolation (Multi-Tenant)

- [ ] Each tenant's trajectory is isolated (separate files/directories)
- [ ] Tenant config cannot be read by other tenants
- [ ] Global aggregation uses patterns only (never raw content)
- [ ] OAuth tokens are per-tenant, never shared

## Network

- [ ] LLM proxy only on localhost:8080 (not exposed externally)
- [ ] Observatory API on localhost:8000 (not exposed externally)
- [ ] Social-media API on localhost:8000 (separate service, localhost only)
- [ ] No CORS for production (localhost:3000 + localhost:5173 for dev only)

## Prompt Injection Prevention

- [ ] User-provided ideas are wrapped in XML tags (`<idea>...</idea>`)
- [ ] Agent outputs are evaluated by independent judge (different model)
- [ ] Content queue items are validated before publishing
- [ ] No dynamic code execution from LLM output

## Cost Protection

- [ ] Daily spend limit in `guardrails.yaml` ($50/day)
- [ ] Monthly spend limit ($500/month)
- [ ] Circuit breaker opens after 5 consecutive API failures
- [ ] Reflexion loop capped at 3 attempts (no infinite retry)
