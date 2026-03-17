# Autonomous Operations Runbook

## Overview

Holus runs autonomously via 3 cron cycles. This runbook covers
monitoring, troubleshooting, and manual intervention.

## The 3 Cron Cycles

| Cycle | Schedule | Command | What it does |
|-------|----------|---------|-------------|
| Content | Every 6h | `python -m holus.agents.marketing.orchestrator content` | Generate → Judge → Auto-publish |
| Analytics | Daily 6am | `python -m holus.agents.marketing.orchestrator analytics` | Fetch engagement → Compute rewards |
| Improvement | Weekly Sun | `python -m holus.agents.marketing.orchestrator improve` | Learn → Evolve prompts → Evaluate A/B |

## Daily Monitoring (5 min)

1. **Check Telegram** — any gap alerts or rejection notifications?
2. **Check Observatory** — `localhost:3000/improvement`
   - Score trends: is average score trending up?
   - Drift alerts: any agents degrading?
   - Activation gates: which mechanisms are active?
3. **Check gaps** — `just gaps` or browse `capability-requests/`

## Weekly Review (15 min)

1. **Review PARTIAL content** — approve or reject with reason
2. **Check learning report** — `cat .self-improvement/MEMORY.md | tail -50`
3. **Check prompt evolution** — `ls config/prompts/*/population.json`
4. **Review gap requests** — decide build/skip/defer for each

## Troubleshooting

### Content not generating
1. Check proxy: `curl localhost:8080/v1/models`
2. Check kill switch: `cat .self-improvement/kill_switch.json`
3. Check marketing plist: `launchctl list | grep holus`
4. Check logs: `tail -50 logs/marketing.log`

### Judge scoring 0 for everything
1. Check Haiku API: does the proxy route to Haiku?
2. Check rubric: `cat agents/evaluators/written-content-judge.md`
3. Check trajectory: `tail -5 .self-improvement/memory/trajectory.jsonl | python3 -m json.tool`

### Analytics not collecting
1. Check social-media API: `curl localhost:8000/api/v1/health`
2. Check published pieces have post_id: `grep post_id data/content-queue/*.json`
3. Check analytics plist: `launchctl list | grep holus.analytics`

### System spending too much
1. Check guardrails: `cat config/guardrails.yaml`
2. Check trajectory cost: `python -m holus.agents.marketing.orchestrator costs`
3. Reduce content cycle from 6h to 12h in plist

## Emergency Stop

```bash
# Activate kill switch (stops all content generation)
echo '{"active": true, "reason": "manual stop"}' > .self-improvement/kill_switch.json

# Or unload all plists
launchctl unload infra/launchd/com.holus.marketing.plist
launchctl unload infra/launchd/com.holus.analytics.plist
launchctl unload infra/launchd/com.holus.improve.plist
```

## Cold Start Protocol

First 30 days after activation:
1. Run cold-start calendar: `config/cold-start-calendar.yaml` (20 pieces in 4 days)
2. Judge + Reflexion only (no Thompson Sampling, no prompt evolution)
3. Manually review ALL content (no auto-publish for first 2 weeks)
4. After 30 days: enable auto-publish for PASS content
5. After 100 paired observations: enable blended reward
6. After 500 entries: enable prompt evolution

## Activation Gates

| Mechanism | Gate | Current | Status |
|-----------|------|---------|--------|
| Thompson Sampling | n ≥ 30 per arm | Check `bandit_arms.json` | |
| Prompt Evolution | n ≥ 500 total | Check trajectory line count | |
| Blended Reward | n ≥ 100 paired | Check paired observations in trajectory | |
| Judge Recalibration | 90 days frozen | Check judge activation date | |
