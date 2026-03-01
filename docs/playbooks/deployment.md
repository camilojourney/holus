# Playbook: Deployment

How to deploy and operate Holus on the Mac Mini M4.

---

## Infrastructure Overview

Holus runs entirely on a Mac Mini M4 via OrbStack (Docker). The Mac Mini hosts infrastructure and orchestration. All LLM reasoning happens via cloud APIs (Anthropic).

```
Mac Mini M4 (16-24GB RAM)
├── OrbStack + Docker containers (~2-3GB)
│   ├── PostgreSQL + pgvector
│   ├── Redis
│   ├── n8n
│   ├── Temporal.io
│   └── Langfuse
├── Holus agents (Python processes, ~1-2GB total)
├── ComfyUI (native, uses Metal GPU when active, ~4-8GB)
└── OS + headroom (~4GB)
```

## Deploying Services

### First-Time Setup

```bash
# 1. Install OrbStack (replaces Docker Desktop)
brew install --cask orbstack

# 2. Clone the repo
git clone git@github.com:camilomartinez/holus.git
cd holus

# 3. Copy environment template
cp .env.example .env
# Edit .env with production secrets

# 4. Start all infrastructure
docker compose -f infrastructure/docker-compose.yml up -d

# 5. Run database migrations
python -m holus db migrate

# 6. Start agents
python -m holus agent run all
```

### Updating an Existing Deployment

```bash
cd holus
git pull origin main
uv sync                    # Update dependencies
docker compose -f infrastructure/docker-compose.yml up -d  # Restart services if compose changed
python -m holus db migrate # Run any new migrations
python -m holus agent restart all
```

## Service Health Checks

Run these periodically (n8n monitors them automatically):

| Service | Check | Expected |
|---------|-------|----------|
| PostgreSQL | `pg_isready -h localhost -p 5432` | "accepting connections" |
| Redis | `redis-cli ping` | "PONG" |
| n8n | `curl -s http://localhost:5678/healthz` | HTTP 200 |
| Langfuse | `curl -s http://localhost:3000/api/public/health` | HTTP 200 |
| Marketing agent | `redis-cli GET holus:agent:marketing:heartbeat` | Timestamp < 5 min ago |

### Automated Health Check

```bash
# Run the built-in health check
python -m holus health --all

# Or use the shell script
bash infrastructure/scripts/health_check.sh
```

## Monitoring with Langfuse

Langfuse runs locally at `http://localhost:3000`.

**Key dashboards:**

- **Traces:** Every agent action with full reasoning chain
- **Generations:** LLM calls with input/output, token counts, latency
- **Scores:** Quality scores from Judge agent evaluations
- **Cost:** Daily/weekly API cost breakdown per agent

**What to monitor weekly:**

1. Token usage per agent (watch for unexpected spikes)
2. Latency trends (p50, p95 per agent)
3. Error rates per agent
4. Prompt cache hit rates (should be >80% for established agents)

## Backup Strategy

### Automated Daily Backup

```bash
# Run via n8n schedule trigger (daily at 2 AM)
# Or manually:
bash infrastructure/scripts/backup.sh
```

The backup script:

1. **PostgreSQL:** `pg_dump` to compressed SQL file
2. **Redis:** `redis-cli BGSAVE` + copy RDB file
3. **Agent memory:** Copy `.self-improvement/` and `.claude/agent-memory/`
4. **Configuration:** Copy `config/` directory
5. **Upload:** Sync to cloud storage (iCloud Drive or S3)

### Recovery Procedure

```bash
# 1. Start fresh infrastructure
docker compose -f infrastructure/docker-compose.yml up -d

# 2. Restore PostgreSQL
pg_restore -h localhost -p 5432 -U holus -d holus < backup/holus_YYYY-MM-DD.sql.gz

# 3. Restore Redis
cp backup/redis_YYYY-MM-DD.rdb /var/lib/redis/dump.rdb
docker compose restart redis

# 4. Restore agent memory
cp -r backup/.self-improvement/ .self-improvement/
cp -r backup/.claude/agent-memory/ .claude/agent-memory/

# 5. Start agents
python -m holus agent run all
```

## Emergency Procedures

### Kill All Agents

```bash
# Fastest method (from any device with SSH access):
redis-cli SET holus:kill:global '{"reason":"emergency","activated_at":"now"}'

# Via CLI:
python -m holus kill --scope global --reason "emergency"

# Via phone (SSH):
ssh macmini 'redis-cli SET holus:kill:global "{\"reason\":\"emergency\"}"'
```

### Kill One Agent

```bash
redis-cli SET holus:kill:agent:marketing-agent '{"reason":"investigating anomaly"}'
```

### Resume After Kill

```bash
# Remove specific kill switch
redis-cli DEL holus:kill:agent:marketing-agent

# Remove global kill switch
redis-cli DEL holus:kill:global

# Verify no kill switches remain
redis-cli KEYS "holus:kill:*"
```

### Service Won't Start

```bash
# Check logs
docker compose logs --tail=50 [service-name]

# Restart a single service
docker compose restart [service-name]

# Nuclear option: recreate everything
docker compose down && docker compose up -d
```

## Resource Monitoring

```bash
# OrbStack resource usage
orb top

# Per-container stats
docker stats --no-stream

# Mac Mini system resources
top -l 1 -s 0 | head -20
```

**Memory budget:**

| Component | Expected RAM |
|-----------|-------------|
| OrbStack + Docker | 2-3 GB |
| PostgreSQL + Redis + n8n | 2-3 GB |
| Temporal.io | 2-3 GB |
| Langfuse + Mem0 + pgvector | 2 GB |
| Holus agents (all) | 1-2 GB |
| OS + headroom | 4 GB |
| **Total** | **~13-17 GB** |

---

**Last updated:** 2026-02-24
