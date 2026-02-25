# Spec 001: Core Infrastructure

## Feature: Shared infrastructure layer for all Holus agents

### Overview

The core infrastructure provides the foundational services that every Holus agent depends on: database, caching, event bus, observability, configuration management, Claude API integration, and safety controls. This is the Phase 1 deliverable -- everything must be running before any agent is built. See [ADR-0001](../docs/decisions/0001-federated-over-unified.md) for the federated architecture rationale and [ADR-0002](../docs/decisions/0002-claude-first-intelligence.md) for the Claude-first intelligence decision.

### User Stories

- As a developer, I want a single `docker compose up` command that starts all infrastructure services so that I can begin agent development immediately.
- As an agent, I want a configuration system that loads YAML defaults, agent-specific overrides, and environment variable secrets so that I can run in any environment without code changes.
- As a founder, I want a kill switch accessible from phone/laptop/CLI so that I can stop any agent within seconds from any device.
- As an agent, I want an event bus so that I can publish domain events without knowing which other agents (if any) consume them.

---

### Core Specifications

**SPEC-001: Docker Compose Service Stack**

| Field | Value |
|-------|-------|
| Description | Docker Compose configuration that starts PostgreSQL (+ pgvector), Redis, n8n, Temporal.io, and Langfuse as containerized services |
| Trigger | `docker compose up -d` from project root or `infrastructure/` directory |
| Input | `infrastructure/docker-compose.yml` + `.env` for secrets |
| Output | 5 running containers with health checks, persistent volumes, and networking |
| Validation | All containers report healthy within 60 seconds of startup |
| Auth Required | No (local services) |

Service definitions:

```yaml
# infrastructure/docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: holus
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-holus}
      POSTGRES_DB: holus
    ports:
      - "5432:5432"
    volumes:
      - holus_postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U holus"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD:-}
    ports:
      - "6379:6379"
    volumes:
      - holus_redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  n8n:
    image: n8nio/n8n:latest
    environment:
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: ${N8N_USER:-admin}
      N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD:-admin}
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: postgres
      DB_POSTGRESDB_DATABASE: n8n
      DB_POSTGRESDB_USER: holus
      DB_POSTGRESDB_PASSWORD: ${POSTGRES_PASSWORD:-holus}
    ports:
      - "5678:5678"
    volumes:
      - holus_n8n:/home/node/.n8n
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:5678/healthz || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  temporal:
    image: temporalio/auto-setup:latest
    environment:
      DB: postgresql
      DB_PORT: 5432
      POSTGRES_USER: holus
      POSTGRES_PWD: ${POSTGRES_PASSWORD:-holus}
      POSTGRES_SEEDS: postgres
    ports:
      - "7233:7233"   # gRPC
    depends_on:
      postgres:
        condition: service_healthy

  temporal-ui:
    image: temporalio/ui:latest
    environment:
      TEMPORAL_ADDRESS: temporal:7233
    ports:
      - "8233:8080"
    depends_on:
      - temporal

  langfuse:
    image: langfuse/langfuse:latest
    environment:
      DATABASE_URL: postgresql://holus:${POSTGRES_PASSWORD:-holus}@postgres:5432/langfuse
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET:-changeme}
      NEXTAUTH_URL: http://localhost:3000
      SALT: ${LANGFUSE_SALT:-changeme}
    ports:
      - "3000:3000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:3000/api/public/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  holus_postgres:
  holus_redis:
  holus_n8n:
```

Acceptance Criteria:
- [ ] `docker compose up -d` starts all 6 containers (postgres, redis, n8n, temporal, temporal-ui, langfuse) without errors
- [ ] All health checks pass within 60 seconds
- [ ] PostgreSQL accepts connections with pgvector extension enabled (`CREATE EXTENSION IF NOT EXISTS vector`)
- [ ] Redis responds to `PING` with `PONG`
- [ ] n8n UI is accessible at `http://localhost:5678`
- [ ] Temporal UI is accessible at `http://localhost:8233`
- [ ] Langfuse UI is accessible at `http://localhost:3000`
- [ ] Data persists across `docker compose down && docker compose up -d` (volumes are not destroyed)
- [ ] `.env.example` documents every required environment variable with descriptions

---

**SPEC-002: Configuration Management**

| Field | Value |
|-------|-------|
| Description | Layered configuration system using pydantic-settings: YAML defaults -> agent-specific YAML -> environment variables (secrets win) |
| Trigger | `HolusSettings.load(agent_name="trading")` at agent startup |
| Input | `config/base.yaml` + `config/{agent_name}.yaml` + environment variables |
| Output | Validated `HolusSettings` instance with all configuration resolved |
| Validation | Pydantic validates types, ranges, required fields. Missing secrets raise `EnvironmentError` with descriptive message. |
| Auth Required | No |

```python
# src/holus/core/config.py

from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import yaml

class HolusSettings(BaseSettings):
    """
    Layered configuration:
    1. config/base.yaml (defaults, committed to git)
    2. config/{agent_name}.yaml (agent-specific, committed to git)
    3. Environment variables (secrets, NEVER committed)

    Environment variables ALWAYS win.
    """

    # Secrets (from environment only)
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    alpaca_api_key: str = Field("", alias="ALPACA_API_KEY")
    alpaca_secret_key: str = Field("", alias="ALPACA_SECRET_KEY")
    redis_url: str = Field("redis://localhost:6379", alias="REDIS_URL")
    postgres_url: str = Field(
        "postgresql://holus:holus@localhost:5432/holus",
        alias="DATABASE_URL",
    )
    langfuse_secret_key: str = Field("", alias="LANGFUSE_SECRET_KEY")
    langfuse_public_key: str = Field("", alias="LANGFUSE_PUBLIC_KEY")
    late_api_key: str = Field("", alias="LATE_API_KEY")

    # Non-secret config (from YAML, overridable by env)
    log_level: str = "INFO"
    agent_name: str = Field("holus", alias="HOLUS_AGENT_NAME")

    model_config = {"env_prefix": "HOLUS_", "env_file": ".env"}

    @classmethod
    def load(cls, agent_name: str | None = None) -> "HolusSettings":
        config_dir = Path("config")
        base_config = {}
        if (config_dir / "base.yaml").exists():
            base_config = yaml.safe_load((config_dir / "base.yaml").read_text()) or {}
        if agent_name:
            agent_path = config_dir / f"{agent_name}.yaml"
            if agent_path.exists():
                agent_config = yaml.safe_load(agent_path.read_text()) or {}
                base_config.update(agent_config)
        return cls(**base_config)
```

```yaml
# config/base.yaml
log_level: INFO
redis_url: redis://localhost:6379
postgres_url: postgresql://holus:holus@localhost:5432/holus

models:
  strategic: claude-opus-4-6
  operational: claude-sonnet-4-6

prompt_cache:
  enabled: true
  min_prefix_tokens: 1024  # Sonnet minimum
```

```yaml
# config/trading_agent.yaml
agent_name: trading-agent
log_level: DEBUG

guardrails:
  max_position_pct: 0.02
  max_portfolio_exposure: 0.30
  max_single_trade_usd: 500.0
  daily_loss_limit_pct: 0.05
  max_trades_per_day: 10

graduation_criteria:
  minimum_paper_days: 30
  minimum_trades: 50
  sharpe_ratio_min: 1.0
  max_drawdown_max: 0.10
  win_rate_min: 0.45
  profit_factor_min: 1.2
  human_review: required
```

Acceptance Criteria:
- [ ] `HolusSettings.load("trading")` returns a validated config with base + trading overlay
- [ ] Missing `ANTHROPIC_API_KEY` raises `EnvironmentError` with message "Required secret ANTHROPIC_API_KEY not found..."
- [ ] Environment variables override YAML values (e.g., `HOLUS_LOG_LEVEL=DEBUG` overrides YAML `log_level: INFO`)
- [ ] All YAML config files pass `yamllint` with no errors
- [ ] `.env.example` contains every secret with a description and placeholder value
- [ ] `config/base.yaml` contains no secrets (verified by pre-commit hook)

---

**SPEC-003: Claude API Client with Prompt Caching**

| Field | Value |
|-------|-------|
| Description | Wrapper around the Anthropic Python SDK that enforces prompt caching, Opus/Sonnet routing, and Langfuse tracing on every call |
| Trigger | Any agent needing to call Claude for reasoning |
| Input | Task type (determines model), system prompt, messages, tools |
| Output | Claude API response with usage metrics logged to Langfuse |
| Validation | Task type must be in known set; system prompt must exceed minimum cacheable tokens |
| Auth Required | `ANTHROPIC_API_KEY` |

```python
# src/holus/integrations/claude_api/client.py

import anthropic
from enum import Enum
from langfuse import Langfuse

class ModelTier(Enum):
    OPUS = "claude-opus-4-6"
    SONNET = "claude-sonnet-4-6"

OPUS_TASKS = {
    "risk_validation", "strategic_planning", "cross_project_synthesis",
    "complex_debugging", "architecture_decisions", "weekly_review",
    "prompt_optimization", "novel_problem_solving",
}

class HolusClaudeClient:
    def __init__(self, api_key: str, langfuse: Langfuse | None = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.langfuse = langfuse

    def route_model(self, task_type: str) -> str:
        if task_type in OPUS_TASKS:
            return ModelTier.OPUS.value
        return ModelTier.SONNET.value

    def create_cached_message(
        self,
        task_type: str,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        model = self.route_model(task_type)
        system_blocks = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_blocks,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        # Log to Langfuse
        if self.langfuse:
            self.langfuse.generation(
                name=task_type,
                model=model,
                input=messages,
                output=response.content,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "cache_read_input_tokens": getattr(
                        response.usage, "cache_read_input_tokens", 0
                    ),
                    "cache_creation_input_tokens": getattr(
                        response.usage, "cache_creation_input_tokens", 0
                    ),
                },
            )

        return response
```

Acceptance Criteria:
- [ ] All Claude API calls include `cache_control: {"type": "ephemeral"}` on the system prompt block
- [ ] `risk_validation` task routes to Opus; `content_generation` task routes to Sonnet
- [ ] Every API call is logged to Langfuse with model, token counts, and cache hit metrics
- [ ] Cache read tokens appear in Langfuse traces (verify prompt caching is working)
- [ ] Client raises a descriptive error if `ANTHROPIC_API_KEY` is missing or invalid
- [ ] Batch API wrapper exists for non-urgent tasks (50% cost discount)

---

**SPEC-004: Kill Switch System**

| Field | Value |
|-------|-------|
| Description | Three-level kill switch (per-agent, per-domain, global) stored in Redis, checked before every agent action |
| Trigger | Manual activation via CLI, SSH, n8n webhook, Slack, or automatic circuit breaker |
| Input | Scope (agent name, domain, or "global") + reason string |
| Output | Redis key set/deleted. All agents in scope halt their action loops. |
| Validation | Scope must be a known agent name, known domain, or "global" |
| Auth Required | No (intentionally -- must work from any SSH session or Redis client) |

```python
# src/holus/core/kill_switch.py

import redis
import json
from datetime import datetime, timezone

class KillSwitch:
    """
    Three levels:
    1. Per-agent:  holus:kill:{agent_name}   -- stops one agent
    2. Per-domain: holus:kill:domain:{name}  -- stops all agents in a domain
    3. Global:     holus:kill:global          -- stops everything

    Every agent checks before every action:
        if kill_switch.is_active(self.agent_name, self.domain):
            return  # Do nothing, log, wait
    """
    GLOBAL_KEY = "holus:kill:global"
    AGENT_PREFIX = "holus:kill:"
    DOMAIN_PREFIX = "holus:kill:domain:"

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def activate(self, scope: str, reason: str, activated_by: str = "manual"):
        if scope == "global":
            key = self.GLOBAL_KEY
        elif scope.startswith("domain:"):
            key = f"{self.DOMAIN_PREFIX}{scope.removeprefix('domain:')}"
        else:
            key = f"{self.AGENT_PREFIX}{scope}"

        self.redis.set(key, json.dumps({
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "activated_by": activated_by,
        }))

    def deactivate(self, scope: str):
        if scope == "global":
            key = self.GLOBAL_KEY
        elif scope.startswith("domain:"):
            key = f"{self.DOMAIN_PREFIX}{scope.removeprefix('domain:')}"
        else:
            key = f"{self.AGENT_PREFIX}{scope}"
        self.redis.delete(key)

    def is_active(self, agent_name: str, domain: str | None = None) -> bool:
        if self.redis.exists(self.GLOBAL_KEY):
            return True
        if domain and self.redis.exists(f"{self.DOMAIN_PREFIX}{domain}"):
            return True
        if self.redis.exists(f"{self.AGENT_PREFIX}{agent_name}"):
            return True
        return False

    def status(self) -> dict:
        keys = self.redis.keys("holus:kill:*")
        result = {}
        for key in keys:
            val = self.redis.get(key)
            if val:
                result[key.decode()] = json.loads(val)
        return result
```

Access methods:

| Method | Command | Latency |
|--------|---------|---------|
| CLI | `python -m holus kill --scope trading-agent --reason "investigating"` | Instant |
| Redis CLI | `redis-cli SET holus:kill:global '{"reason":"emergency"}'` | Instant |
| SSH from phone | `ssh macmini 'redis-cli SET holus:kill:global ...'` | ~2s |
| n8n webhook | POST `/webhook/kill-switch` `{"scope":"trading-agent","reason":"..."}` | ~1s |
| Slack | `/holus kill trading-agent` via n8n Slack integration | ~2s |
| Circuit breaker | Automatic when drawdown exceeds threshold | Automatic |

Acceptance Criteria:
- [ ] `kill_switch.activate("trading-agent", "test")` sets Redis key `holus:kill:trading-agent`
- [ ] `kill_switch.is_active("trading-agent")` returns `True` when agent-specific OR global switch is active
- [ ] `kill_switch.is_active("trading-agent", domain="trading")` returns `True` when domain switch is active
- [ ] `kill_switch.deactivate("global")` removes the global key and agents resume
- [ ] `kill_switch.status()` returns all active kill switches with reason and timestamp
- [ ] CLI command `python -m holus kill --scope global --reason "test"` works
- [ ] Kill switch check adds <1ms latency per agent action (single Redis `EXISTS` call)

---

**SPEC-005: Event Bus (Redis Pub/Sub + Streams)**

| Field | Value |
|-------|-------|
| Description | Event bus for inter-agent communication. Agents publish domain events via Redis pub/sub (real-time) and Redis Streams (persistent replay). No agent reads another agent's state directly. |
| Trigger | Any agent publishes a significant domain event |
| Input | `HolusEvent` with source_agent, event_type, timestamp, payload, optional correlation_id |
| Output | Event delivered to all subscribers (pub/sub) AND persisted to replay stream (Streams) |
| Validation | Event must conform to Pydantic schema. Channel must be in registered schema (`config/events.yaml`). |
| Auth Required | No (Redis is internal) |

```python
# src/holus/core/event_bus.py

import redis
import json
from datetime import datetime, timezone
from pydantic import BaseModel

class HolusEvent(BaseModel):
    source_agent: str
    event_type: str
    timestamp: datetime
    payload: dict
    correlation_id: str | None = None

class EventBus:
    STREAM_PREFIX = "holus:stream:"
    MAX_STREAM_LEN = 10_000  # Rolling window per channel

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()

    def publish(self, channel: str, event: HolusEvent):
        event_json = event.model_dump_json()
        # Real-time delivery
        self.redis.publish(channel, event_json)
        # Persistent replay (Redis Streams)
        self.redis.xadd(
            f"{self.STREAM_PREFIX}{channel}",
            {"data": event_json},
            maxlen=self.MAX_STREAM_LEN,
        )

    def subscribe(self, channels: list[str], callback):
        for ch in channels:
            self.pubsub.subscribe(**{ch: callback})
        self.pubsub.run_in_thread(sleep_time=0.1)

    def read_stream(
        self, channel: str, count: int = 100, since: str = "0-0"
    ) -> list[HolusEvent]:
        entries = self.redis.xrange(
            f"{self.STREAM_PREFIX}{channel}", min=since, count=count
        )
        events = []
        for entry_id, data in entries:
            events.append(HolusEvent.model_validate_json(data[b"data"]))
        return events
```

```yaml
# config/events.yaml -- Schema registry
trading_agent:
  publishes:
    - channel: holus.trading.signals
      events:
        - signal_generated
        - trade_executed
        - risk_alert
        - market_regime_shift
        - daily_pnl

content_agent:
  publishes:
    - channel: holus.content.performance
      events:
        - content_published
        - engagement_update
        - seo_ranking_change
        - topic_trending

coding_agent:
  publishes:
    - channel: holus.coding.deploys
      events:
        - pr_merged
        - ci_failure
        - dependency_alert
        - self_improvement_cycle

pilaster_agent:
  publishes:
    - channel: holus.pilaster.workflows
      events:
        - workflow_optimized
        - quality_threshold_met
        - generation_batch_complete
        - model_performance_report

system:
  publishes:
    - channel: holus.system.alerts
      events:
        - agent_crash
        - guardrail_violation
        - kill_switch_activated
        - health_check_failed
```

Example event payload:

```json
{
  "source_agent": "trading-agent",
  "event_type": "trade_executed",
  "timestamp": "2026-03-15T14:30:00Z",
  "payload": {
    "symbol": "AAPL",
    "direction": "long",
    "quantity": 10,
    "price": 185.50,
    "order_id": "abc123",
    "risk_score": 0.65
  },
  "correlation_id": "signal-20260315-001"
}
```

Acceptance Criteria:
- [ ] `event_bus.publish("holus.trading.signals", event)` delivers to all pub/sub subscribers AND persists to Redis Stream
- [ ] `event_bus.read_stream("holus.trading.signals", count=10)` returns the last 10 events from the stream
- [ ] Stream is capped at 10,000 entries per channel (MAXLEN)
- [ ] Events with invalid schema (missing required fields) raise `ValidationError` before publishing
- [ ] `config/events.yaml` documents every channel and event type
- [ ] Subscriber callback receives deserialized `HolusEvent` objects
- [ ] Publishing is fire-and-forget (never blocks the publishing agent)

---

### Data Structures

```python
# src/holus/core/models.py -- Shared models across all agents

from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class AgentStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    CRASHED = "crashed"
    RATE_LIMITED = "rate_limited"
    KILLED = "killed"

class AgentHeartbeat(BaseModel):
    agent_name: str
    status: AgentStatus
    last_action_at: datetime
    uptime_seconds: int
    actions_today: int
    errors_today: int

class HolusEvent(BaseModel):
    source_agent: str
    event_type: str
    timestamp: datetime
    payload: dict
    correlation_id: str | None = None
```

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `infrastructure/docker-compose.yml` | New | All service definitions |
| `infrastructure/docker-compose.prod.yml` | New | Production overrides (resource limits) |
| `.env.example` | New | Template with all required environment variables |
| `config/base.yaml` | New | Shared configuration defaults |
| `config/trading_agent.yaml` | New | Trading agent configuration |
| `config/content_agent.yaml` | New | Content agent configuration |
| `config/coding_agent.yaml` | New | Coding agent configuration |
| `config/pilaster_agent.yaml` | New | Pilaster agent configuration |
| `config/events.yaml` | New | Event bus schema registry |
| `config/guardrails.yaml` | New | Agent authority matrix |
| `src/holus/core/__init__.py` | New | Core module init |
| `src/holus/core/config.py` | New | Configuration loading |
| `src/holus/core/event_bus.py` | New | Redis pub/sub + Streams event bus |
| `src/holus/core/kill_switch.py` | New | Kill switch system |
| `src/holus/core/logging.py` | New | Structured logging with Langfuse |
| `src/holus/core/models.py` | New | Shared Pydantic models |
| `src/holus/integrations/claude_api/__init__.py` | New | Claude API module init |
| `src/holus/integrations/claude_api/client.py` | New | Cached Claude client with routing |
| `src/holus/integrations/claude_api/batch.py` | New | Batch API wrapper |
| `src/holus/observability/langfuse_client.py` | New | Langfuse initialization and helpers |
| `tests/unit/core/test_config.py` | New | Config loading tests |
| `tests/unit/core/test_event_bus.py` | New | Event bus unit tests (mocked Redis) |
| `tests/unit/core/test_kill_switch.py` | New | Kill switch unit tests |
| `tests/integration/test_event_flow.py` | New | End-to-end event publish/subscribe |
| `infrastructure/scripts/setup.sh` | New | First-time setup script |
| `infrastructure/scripts/backup.sh` | New | Daily backup script |
| `infrastructure/scripts/health_check.sh` | New | Service health verification |

---

### Edge Cases & Error Handling

**EDGE-001: Redis unavailable at startup**
- Scenario: Agent starts but Redis is not running or unreachable
- Expected behavior: Agent logs error, retries connection 3 times with exponential backoff (1s, 2s, 4s), then exits with status code 1
- Error message: `FATAL: Cannot connect to Redis at {redis_url} after 3 retries. Is docker compose running?`
- Recovery: Run `docker compose up -d redis` and restart the agent

**EDGE-002: PostgreSQL connection pool exhausted**
- Scenario: All database connections are in use (max_connections reached)
- Expected behavior: Agent logs warning, waits up to 30 seconds for a connection, then fails the current action gracefully (does not crash)
- Error message: `WARN: Database connection pool exhausted. Waiting up to 30s for available connection.`
- Recovery: Automatic once connections are freed. If persistent, increase `max_connections` in docker-compose or investigate connection leaks.

**EDGE-003: Kill switch activated during active operation**
- Scenario: Kill switch is set while an agent is mid-action (e.g., trading agent has submitted an order)
- Expected behavior: Current action completes (no mid-action abort), then agent halts before the next action. For trading, the ExecutionHandler completes the current order lifecycle.
- Error message: `INFO: Kill switch active for {agent_name}. Completing current action, then halting.`
- Recovery: Deactivate kill switch via `redis-cli DEL holus:kill:{scope}`

**EDGE-004: Event bus receives malformed event**
- Scenario: A subscriber receives a JSON payload that does not match the `HolusEvent` schema
- Expected behavior: Subscriber logs the malformed event, increments an error counter, continues processing. Does not crash.
- Error message: `WARN: Malformed event on channel {channel}: {validation_error}. Skipping.`
- Recovery: Fix the publishing agent's event format. Malformed events are logged for debugging.

**EDGE-005: Docker volume corruption after unclean shutdown**
- Scenario: Mac Mini power loss or forced shutdown while services are writing
- Expected behavior: PostgreSQL runs WAL recovery on next startup. Redis replays AOF or loads last RDB snapshot.
- Error message: PostgreSQL logs `LOG: database system was not properly shut down; automatic recovery in progress`
- Recovery: Automatic. If data is corrupted beyond recovery, restore from daily backup (see `docs/playbooks/deployment.md`).

**EDGE-006: Anthropic API rate limit exceeded**
- Scenario: Agent exceeds Anthropic rate limits (429 response)
- Expected behavior: Claude client retries with exponential backoff (built into `anthropic` SDK). After 3 retries, publishes `holus.system.alerts` event with `rate_limit_exceeded` type. Agent continues with degraded functionality (queues actions for later).
- Error message: `WARN: Anthropic API rate limit hit for {model}. Retrying in {backoff}s.`
- Recovery: Automatic via SDK retry. If persistent, check token budget and agent call frequency.

**EDGE-007: Configuration YAML syntax error**
- Scenario: A YAML config file has invalid syntax (bad indentation, missing colon)
- Expected behavior: Agent fails to start with a clear error pointing to the file and line number
- Error message: `FATAL: Cannot parse config/trading_agent.yaml: {yaml_error}. Fix the YAML syntax and restart.`
- Recovery: Fix the YAML syntax error and restart the agent

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Docker Compose startup | < 60s to all-healthy | Time from `docker compose up` to all health checks passing |
| Config loading | < 100ms | Timestamp `HolusSettings.load()` call |
| Kill switch check | < 1ms | Single Redis `EXISTS` command latency |
| Event publish | < 5ms | Redis `PUBLISH` + `XADD` round-trip |
| Event stream read (100 events) | < 10ms | Redis `XRANGE` latency |
| Claude API call (cached prefix) | < 3s p95 | Langfuse trace duration |
| Claude API call (cold prefix) | < 5s p95 | Langfuse trace duration |

---

### Security Considerations

- All secrets live in `.env` (never committed). `.env.example` contains only placeholders.
- YAML config files in `config/` contain no secrets. A pre-commit hook verifies this.
- Redis requires no authentication in local dev. In production, `REDIS_PASSWORD` is set.
- PostgreSQL uses a dedicated `holus` user with minimum required privileges.
- Kill switch is intentionally unauthenticated -- accessibility from any device is more important than preventing unauthorized deactivation in a single-user system.
- Langfuse stores trace data locally. No agent reasoning data leaves the Mac Mini except via Anthropic API calls (covered by their API privacy guarantees).

---

### Out of Scope

- Agent-specific logic (trading, content, coding, Pilaster) -- those are specs 002, 003, and future specs
- Mem0 memory system -- will be its own spec when Phase 2 begins
- Cognee knowledge graph -- Phase 3
- n8n workflow definitions -- each agent's n8n workflows are documented in their own spec
- CI/CD pipeline -- separate spec
- Monitoring dashboards and alerting rules -- separate spec

---

### Related Specs

- [002-trading-agent.md](./002-trading-agent.md) -- depends on this infrastructure (Redis, Temporal, Claude client, kill switch)
- [003-content-pipeline.md](./003-content-pipeline.md) -- depends on this infrastructure (Redis, n8n, Claude client)

---

**Last Updated:** 2026-02-24
**Status:** Not Started
**Owner:** Camilo Martinez
