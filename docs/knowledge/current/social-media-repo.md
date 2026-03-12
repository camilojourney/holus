# social-media-automatization Repository

**Repository:** `social-media-automatization`  
**Location:** `/Users/mini/.openclaw/workspace/github/social-media-automatization`  
**Purpose:** Multi-platform social media posting service with AI enhancement, multi-language account routing, and intelligent scheduling  
**Tech Stack:** FastAPI, SQLite, SQLAlchemy, Anthropic Claude, OpenAI GPT, Google Translate, Meta Graph API, Twitter API, LinkedIn API

---

## Architecture Overview

### High-Level Pipeline

```
API Client / MCP Agent
        ↓
    FastAPI App (lifespan managed)
        ↓
   Content Intelligence Layer
   (Text Enhancement + Translation)
        ↓
   PlatformQueueManager
   (Per-platform queues + workers)
        ↓
  Platform Publishers (5 platforms)
        ↓
   Platform APIs
```

### Source Directory Structure

```
src/
├── main.py                     # Entry point: starts uvicorn
├── api/
│   ├── app.py                  # FastAPI factory, lifespan, CORS
│   ├── dependencies.py         # X-API-Key auth, MVP user ID
│   └── routes/
│       ├── posting.py          # POST /api/post, /api/post-with-file
│       ├── language_routing.py  # POST /api/post-languages (routes EN to @camiloexperience, ES to @camilojourney)
│       ├── stories.py          # POST /api/post-story
│       ├── schedule.py         # CRUD /api/schedule
│       ├── import_csv.py       # POST /api/import/csv
│       ├── voice_profile.py    # CRUD /api/voice-profile
│       ├── image_gen.py        # POST /api/generate-image
│       └── onboarding.py       # Onboarding endpoints
├── core/
│   ├── queue_manager.py        # Per-platform queues + workers
│   └── scheduler.py            # Cron loop (60s poll)
├── content/
│   ├── text_enhancer.py        # AI enhancement (4 styles)
│   ├── translator.py           # Google Translate (EN<->ES)
│   ├── brand_validator.py      # Brand consistency checks
│   ├── content_adapter.py      # Platform-specific adaptation
│   ├── intelligence.py         # Content analysis
│   ├── smart_router.py         # Routing logic
│   └── twitter_threader.py     # Long-form to thread conversion
├── platforms/
│   ├── base.py                 # BasePlatformPublisher ABC
│   ├── instagram.py            # Meta Graph: feed, reels, stories
│   ├── facebook.py             # Meta Graph: page posts, reels
│   ├── threads.py              # Threads API: text+image+video
│   ├── linkedin.py             # LinkedIn API v2: UGC posts
│   └── twitter.py              # Twitter/X API v2 (Tweepy)
├── services/
│   ├── media_storage.py        # Cloudflare R2 (S3-compatible)
│   ├── image_template_engine.py # Pillow-based templates
│   ├── story_composer.py       # Caption overlay for stories
│   ├── story_translator.py     # Per-account language detection
│   ├── csv_importer.py         # CSV parse, validate, schedule
│   ├── health_checker.py       # Platform health (5-min cache)
│   ├── voice_profile.py        # Voice context loading
│   └── user_publisher.py       # Per-user publisher factory
├── db/
│   ├── database.py             # Async engine, session factory
│   ├── models.py               # SQLAlchemy ORM (9 tables)
│   └── operations.py           # CRUD for all tables
├── auth/
│   ├── encryption.py           # Fernet encryption for tokens
│   └── providers/              # OAuth: LinkedIn, Twitter, Meta
└── utils/
    ├── logger.py               # Logging setup
    └── helpers.py              # Retry, URL validation, helpers
```

---

## Component Details

### 1. Content Intelligence

**Text Enhancement** (`src/content/text_enhancer.py`)

4 enhancement styles:
- `raw` — Grammar/formatting only, zero voice alteration
- `polished` — Light clarity, preserves author voice
- `enhanced` — Full hook + metadata (default)
- `platform_native` — Max engagement with CTA

Provider chain: Claude (primary) → GPT (fallback) → original text

Returns structured JSON: `{improved_post, emotions[], category}`

**Voice Profiles** (SPEC-006): 3-10 example posts teach AI writing style

**Translation** (`src/content/translator.py`): Google Translate via `deep-translator` (no API key)

---

### 2. Platform Publishers

**Base Contract** (`src/platforms/base.py`):
```python
class BasePlatformPublisher(ABC):
    def publish_text(content, account_id) -> PublishResult
    def publish_image(image_url, caption, account_id) -> PublishResult
    def publish_video(video_url, caption, account_id) -> PublishResult
    def validate_credentials() -> bool
```

**Platforms:**
- Instagram: Feed posts, reels, stories (Meta Graph v20.0)
- Facebook: Page posts, reels (Meta Graph v20.0)
- Threads: Text + image + video posts
- LinkedIn: UGC posts (LinkedIn API v2)
- Twitter: Tweets, media (Twitter API v2 via Tweepy)

All use `httpx.AsyncClient` for API calls

---

### 3. Queue Manager

**File:** `src/core/queue_manager.py`

One `asyncio.Queue` + worker task per platform

**Rate Limits (daily caps):**

| Platform | Max/Day | Min Interval |
|----------|---------|--------------|
| LinkedIn | 20      | 5s           |
| Instagram| 25      | 3s           |
| Facebook | 25      | 3s           |
| Threads  | 50      | 2s           |
| Twitter  | 15      | 5s           |

**Retry Policy:**
- 3 retries with exponential backoff (2s, 4s, 8s)
- HTTP 429/5xx are retryable
- 400/401/403/404 fail immediately
- Network errors always retry

**Crash Recovery:** On startup, `recover_pending_tasks()` re-enqueues any PostResults in `pending` state

**Concurrency Safety:** Per-platform `asyncio.Lock` prevents TOCTOU races

---

### 4. Multi-Language Account Routing

**File:** `src/api/routes/language_routing.py`

POST `/api/post-languages`:
1. Translate content EN ↔ ES (Google Translate)
2. Enhance both language versions via TextEnhancer
3. Route EN → @camiloexperience accounts (IG/FB/Threads)
4. Route ES → @camilojourney accounts (IG/FB/Threads)
5. LinkedIn and Twitter receive source-language version only

Creates two Post records (EN + ES), returns composite `routing_job_id`

---

### 5. Scheduler

**File:** `src/core/scheduler.py`

Cron loop polls every 60s for `ScheduledPost` where `scheduled_at <= NOW()`

Each due post → `Post` record → standard `_process_post()` pipeline

On startup, catches up any posts missed during downtime

---

### 6. Database Schema

**Engine:** SQLite via SQLAlchemy async + aiosqlite

**Tables (9):**

| Table | Purpose |
|-------|---------|
| `users` | Telegram users (user_id as PK) |
| `user_platforms` | Connected platform accounts with Fernet-encrypted tokens |
| `posts` | Post content, enhancement results, lifecycle status |
| `post_results` | Per-platform publish outcome (success/fail/pending) |
| `voice_profiles` | 3-10 example posts for AI voice matching |
| `scheduled_posts` | Future-dated posts for cron publishing |
| `import_batches` | CSV import tracking and validation |
| `rate_limits` | Per-platform daily counters (platform + date unique) |
| `oauth_states` | Short-lived OAuth tokens (CSRF, 10-min expiry) |

**Post Lifecycle:** draft → enhanced → processing → publishing → published/partial/failed

**Key Models:**

```python
class User(Base):
    id: Mapped[int]  # Telegram user ID (BigInteger)
    username: Mapped[str | None]
    first_name: Mapped[str | None]
    language_code: Mapped[str] = "en"
    is_active: Mapped[bool] = True
    created_at: Mapped[datetime]
    last_active_at: Mapped[datetime]

class UserPlatform(Base):
    id: Mapped[int]
    user_id: Mapped[int]
    platform: Mapped[PlatformType]
    account_name: Mapped[str]
    account_id: Mapped[str | None]
    encrypted_access_token: Mapped[str]
    encrypted_refresh_token: Mapped[str | None]
    token_expires_at: Mapped[datetime | None]
    is_active: Mapped[bool] = True

class Post(Base):
    id: Mapped[int]
    user_id: Mapped[int]
    original_text: Mapped[str]
    enhanced_text: Mapped[str | None]
    media_url: Mapped[str | None]
    media_type: Mapped[str | None]  # image or video
    label: Mapped[str | None]  # ContentLabel
    emotions: Mapped[str | None]  # JSON array
    target_platforms: Mapped[str | None]  # JSON array
    voice_profile_id: Mapped[int | None]
    status: Mapped[PostStatus] = PostStatus.DRAFT

class PostResult(Base):
    id: Mapped[int]
    post_id: Mapped[int]
    user_platform_id: Mapped[int]
    success: Mapped[bool | None]  # None = pending
    platform_post_id: Mapped[str | None]
    post_url: Mapped[str | None]
    retry_count: Mapped[int] = 0
    adapted_content: Mapped[str | None]
    error_message: Mapped[str | None]
```

---

### 7. Media Storage

**File:** `src/services/media_storage.py`

Cloudflare R2 (S3-compatible, zero egress cost), uses boto3 in thread executor

**URL Pattern:** `{R2_PUBLIC_URL}/media/{reference_id}/{uuid12}.{ext}`

**Limits:** 50 MB max, types: JPEG, PNG, GIF, WebP, MP4, MOV

---

### 8. MCP Server

**Directory:** `mcp_server/` (standalone, not merged into src/)

Stdio JSON-RPC server exposing 9 tools to AI agents

Calls FastAPI HTTP API for publishing; uses direct service imports for enhance/translate

Config: `.mcp.json` with `API_BASE_URL` and `POSTING_API_KEY`

---

### 9. Auth

**Files:** `src/auth/encryption.py`, `src/auth/providers/`

- **Fernet encryption** for stored tokens (symmetric, key from `ENCRYPTION_KEY` env var)
- **OAuth providers:** LinkedIn, Twitter, Meta (multi-user mode)
- **MVP mode:** Static API key + tokens from env vars (single-user)

---

## API Endpoints

### Core Posting

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/post | Single platform post |
| POST | /api/post-with-file | Post with media upload |
| POST | /api/post-languages | Multi-language account routing (EN→@camiloexperience, ES→@camilojourney) |
| POST | /api/post-story | Auto-translate story per account |
| GET | /api/jobs/{id} | Job status |
| GET | /api/accounts | List connected accounts |

### Scheduling

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/schedule | List scheduled posts |
| POST | /api/schedule | Create scheduled post |
| PUT | /api/schedule/{id} | Update scheduled post |
| DELETE | /api/schedule/{id} | Cancel scheduled post |

### CSV Import

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/import/csv | Upload CSV for validation |
| POST | /api/import/{id}/confirm | Confirm and schedule batch |
| GET | /api/import/{id}/status | Import status |

### Voice Profiles

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/voice-profile | List profiles |
| POST | /api/voice-profile | Create profile |
| PUT | /api/voice-profile/{id} | Update profile |
| DELETE | /api/voice-profile/{id} | Delete profile |

### Image Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/generate-image | Generate image from template |
| GET | /api/templates | List available templates |

---

## Configuration

**File:** `config/settings.py` — Dataclass-based config from env vars

Sub-configs: NotionConfig, AIConfig, MetaConfig, LinkedInConfig, TwitterConfig, DatabaseConfig, EncryptionConfig, R2Config, OAuthConfig

**File:** `config/constants.py` — Static values: PlatformIDs, APIEndpoints, enums

---

## Load-Bearing Walls (CRITICAL - DO NOT CHANGE WITHOUT SPEC)

1. **Account mapping** (`config/constants.py` PlatformIDs) — Wrong ID = post to wrong account
2. **Queue rate limits** (`src/core/queue_manager.py` PLATFORM_LIMITS) — Exceeding gets tokens revoked
3. **Database schema** (`src/db/models.py`) — No migration system; schema changes require plan
4. **Language account routing logic** (`src/api/routes/language_routing.py` _ACCOUNT_IDS) — Must sync with PlatformIDs (EN → @camiloexperience, ES → @camilojourney)
5. **Lifespan startup order** (`src/api/app.py` lifespan) — Dependencies; reordering causes crashes
6. **Publisher ABC contract** (`src/platforms/base.py`) — Breaking it breaks all publishers
7. **MCP tool contract** (`mcp_server/tools.py`) — AI agents depend on stable schemas
8. **Token encryption** (`src/auth/encryption.py`) — Changing invalidates all stored tokens

---

## Development Commands

```bash
# Run dev server
uvicorn src.main:app --reload --port 8000

# Run queue worker (separate process)
python -m src.core.queue_manager

# Run scheduler (separate process)
python -m src.core.scheduler

# Run tests
pytest tests/
```

---

## Integration Points

**For Holus:** This repo provides the social media posting API that Holus can call to distribute content

**Key Integration Endpoints:**
- POST `/api/post-languages` — Primary entry point for multi-language content routing (EN→@camiloexperience, ES→@camilojourney)
- POST `/api/post` — Single platform posting
- GET `/api/accounts` — Get list of configured accounts for routing decisions

**Authentication:** X-API-Key header (configured in Holus environment)

---

**Last Updated:** 2026-02-27  
**Documented By:** Fruco (Holus Repo Research Task)
