# Spec 016: Social Media Integration V2

## Feature: Multi-platform posting with bilingual routing, analytics, and intelligent scheduling via social-media-automatization

### Overview

social-media-automatization is the publishing and analytics silo. It already has a working
FastAPI REST API (12+ endpoints) and an MCP server (9 tools) that handles posting,
scheduling, bilingual EN/ES routing, voice profiles, and text enhancement. Holus connects
to it directly — no wrapper code in Holus.

This spec defines what Holus needs from the social-media MCP, what already exists, and what
needs to be added to the social-media-automatization repo.

### User Stories

- As the marketing agent, I want to post bilingual content (EN + ES) to platform-specific accounts so that both audiences are reached.
- As the marketing agent, I want to retrieve analytics for all platforms so that I learn what works across different audiences.
- As a founder, I want content posted at optimal times per platform so that engagement is maximized.
- As a founder, I want to approve content before it goes live on high-risk platforms (Instagram, TikTok) while auto-posting to low-risk ones (LinkedIn, Twitter).

---

### Core Specifications

**SPEC-001: Social Media MCP Server**

| Field | Value |
|-------|-------|
| Description | MCP server in the social-media-automatization repo. Holus connects to it — no wrapper code in Holus. |
| Trigger | Marketing agent connects to the MCP server at startup |
| Input | Tool calls from the marketing agent (post content, get analytics, schedule, etc.) |
| Output | Tool results (post IDs, analytics data, scheduling confirmations) |
| Validation | All inputs validated by social-media MCP server |
| Auth Required | `SOCIAL_MEDIA_API_KEY` (server-side, in social-media-automatization repo) |

**NOTE:** The MCP server code lives in the **social-media-automatization repo**, not in Holus.

**Existing MCP tools (already built):**

| Tool | Description |
|------|-------------|
| `post_text` | Post text content to platforms |
| `post_with_media` | Post content with images/video |
| `schedule_post` | Schedule a post for future publishing |
| `get_job_status` | Check post job status |
| `list_scheduled` | List pending scheduled posts |
| `cancel_scheduled` | Cancel a scheduled post |
| `enhance_text` | Enhance text using voice profiles |
| `platform_health` | Check platform connection health |
| `translate` | Translate text for bilingual posting |

**MCP tools to be added in social-media-automatization repo:**

| Tool | Description |
|------|-------------|
| `get_analytics` | Get engagement analytics for recent posts (impressions, engagement rate, clicks) |
| `get_top_posts` | Get best performing posts ranked by metric |
| `post_story` | Post a story to Instagram/Facebook |
| `get_accounts` | Get list of connected social media accounts |

MCP server configuration for Holus (in `.claude/settings.json`):

```json
{
  "mcpServers": {
    "social-media": {
      "command": "python",
      "args": ["-m", "social_media_automatization.mcp_server"],
      "cwd": "/Users/mini/.openclaw/workspace/github/social-media-automatization",
      "env": {
        "SOCIAL_MEDIA_API_KEY": "${SOCIAL_MEDIA_API_KEY}"
      }
    }
  }
}
```

Acceptance Criteria:
- [ ] Social-media MCP server (in social-media-automatization repo) responds to `tools/list`
- [ ] `post_text` and `post_with_media` tools publish content to platforms
- [ ] `schedule_post` tool schedules content for future publishing
- [ ] `get_analytics` tool returns engagement data (to be added)
- [ ] `get_top_posts` tool ranks posts by specified metric (to be added)
- [ ] `post_story` tool posts stories to IG/FB (to be added)
- [ ] `get_accounts` tool returns connected account info (to be added)
- [ ] Holus can connect to social-media MCP via `.claude/settings.json` config

---

**SPEC-002: Bilingual Content Routing**

| Field | Value |
|-------|-------|
| Description | Posts bilingual content (EN + ES) to language-specific accounts automatically |
| Trigger | Marketing agent calls `post_content` with `bilingual=true` |
| Input | English content text |
| Output | English version to EN accounts, Spanish translation to ES accounts |
| Validation | Content must be in English for translation. Account language mappings must be configured. |
| Auth Required | Local service API key |

Bilingual routing configuration (lives in social-media-automatization repo, not Holus):

```yaml
# social-media-automatization config (for reference)

accounts:
  instagram:
    experience:  # English account
      account_id: "17841460112345678"
      language: "en"
      handle: "@pilot_experience"
    
    journey:  # Spanish account
      account_id: "17841460119876543"
      language: "es"
      handle: "@pilot_journey"
  
  facebook:
    experience:
      page_id: "107890123456789"
      language: "en"
      handle: "Pilot Experience"
    
    journey:
      page_id: "108901234567890"
      language: "es"
      handle: "Pilot Journey"
  
  threads:
    experience:
      account_id: "17841460112345678"  # Shares IG account ID
      language: "en"
      handle: "@pilot_experience"
    
    journey:
      account_id: "17841460119876543"
      language: "es"
      handle: "@pilot_journey"
  
  # LinkedIn and Twitter: single account, source language only
  linkedin:
    main:
      account_id: "urn:li:person:abc123"
      language: "en"
      handle: "Camilo Martinez"
  
  twitter:
    main:
      account_id: "1234567890"
      language: "en"
      handle: "@camilo_builds"
```

Routing logic (handled by social-media-automatization internally):

```python
# Bilingual platforms: IG, FB, Threads → EN + ES versions
# Single-language platforms: LinkedIn, Twitter → source language only

bilingual_platforms = {"instagram", "facebook", "threads"}

if bilingual:
    # Translate EN → ES
    spanish_text = translate(text, "en", "es")
    
    # Post to EN accounts
    post_to_accounts(text, "experience" accounts, platforms & bilingual_platforms)
    
    # Post to ES accounts
    post_to_accounts(spanish_text, "journey" accounts, platforms & bilingual_platforms)
    
    # Post source language to single-language platforms
    post_to_accounts(text, "main" accounts, platforms - bilingual_platforms)
```

Acceptance Criteria:
- [ ] Bilingual posts create 2 versions: EN and ES
- [ ] EN version goes to "experience" accounts on IG, FB, Threads
- [ ] ES version goes to "journey" accounts on IG, FB, Threads
- [ ] LinkedIn and Twitter receive source language only
- [ ] Translation uses Google Translate (no API key needed)
- [ ] Both versions tracked separately in analytics

---

**SPEC-003: Content Types Supported**

| Content Type | Available Now | Needs Tooling |
|--------------|---------------|---------------|
| **Text posts** (all platforms) | ✅ YES | None |
| **Image posts** (single image) | ✅ YES | None |
| **Video posts** (reels, native video) | ✅ YES | None |
| **Stories** (IG, FB with auto-translation) | ✅ YES | None |
| **Carousels** (multi-image swipe) | ❌ NO | Carousel assembly API |
| **Threads** (Twitter/Threads multi-post) | ⚠️ PARTIAL | Thread splitting logic (local service) |
| **Polls** (Twitter, IG stories) | ❌ NO | Poll creation API |
| **Live videos** | ❌ NO | Out of scope |
| **Link previews** (rich cards) | ✅ YES | Platform auto-generates |

---

**SPEC-004: Analytics and Feedback**

| Field | Value |
|-------|-------|
| Description | Comprehensive analytics retrieval with per-platform and per-product breakdowns |
| Trigger | Marketing agent observe stage or manual analytics request |
| Input | Time period, platform filter, product filter (optional) |
| Output | Analytics summary with engagement metrics and top performers |
| Validation | Minimum 1 post required for analytics |
| Auth Required | Service API keys |

Analytics data structure:

```json
{
  "period_days": 7,
  "total_posts": 12,
  "total_impressions": 45320,
  "total_engagement": 2145,
  "avg_engagement_rate": 0.0473,
  
  "platform_breakdown": {
    "linkedin": {
      "posts": 4,
      "impressions": 18200,
      "engagement_rate": 0.067,
      "top_post": {
        "post_id": "urn:li:share:7234567890",
        "topic": "ComfyUI workflow management",
        "engagement_rate": 0.089
      }
    },
    "twitter": {
      "posts": 4,
      "impressions": 12100,
      "engagement_rate": 0.041,
      "top_post": {
        "post_id": "1765432109876543210",
        "topic": "AI agent architecture",
        "engagement_rate": 0.056
      }
    },
    "instagram": {
      "posts": 4,
      "impressions": 15020,
      "engagement_rate": 0.038,
      "top_post": {
        "post_id": "18234567890123456",
        "topic": "Product demo reel",
        "engagement_rate": 0.052
      }
    }
  },
  
  "product_breakdown": {
    "pilaster": {
      "posts": 5,
      "avg_engagement_rate": 0.058,
      "best_platform": "linkedin"
    },
    "genpeli": {
      "posts": 4,
      "avg_engagement_rate": 0.042,
      "best_platform": "instagram"
    },
    "holus": {
      "posts": 3,
      "avg_engagement_rate": 0.035,
      "best_platform": "twitter"
    }
  },
  
  "content_type_performance": {
    "tutorial": {"posts": 4, "avg_engagement": 0.061},
    "demo": {"posts": 3, "avg_engagement": 0.048},
    "thread": {"posts": 3, "avg_engagement": 0.038},
    "tips": {"posts": 2, "avg_engagement": 0.032}
  },
  
  "top_posts": [
    {
      "post_id": "urn:li:share:7234567890",
      "platform": "linkedin",
      "product": "pilaster",
      "content_type": "tutorial",
      "topic": "ComfyUI workflow management",
      "published_at": "2026-02-25T14:00:00Z",
      "impressions": 5200,
      "engagement_rate": 0.089,
      "clicks": 312,
      "shares": 18,
      "comments": 12
    }
    // ... more top posts
  ]
}
```

Acceptance Criteria:
- [ ] Analytics aggregated across all connected platforms
- [ ] Per-platform breakdown shows engagement trends
- [ ] Per-product breakdown identifies which products resonate
- [ ] Content type performance guides future strategy
- [ ] Top posts ranked by engagement_rate, impressions, or clicks
- [ ] Analytics updated daily (collected via cron)

---

### Data Structures

Post result (what the MCP server returns):

```json
{
  "job_id": "post-20260227-001",
  "bilingual": true,
  "versions": {
    "en": {
      "text": "Learn how to manage ComfyUI workflows with Pilaster...",
      "platforms": {
        "linkedin": {
          "status": "published",
          "post_id": "urn:li:share:7234567890",
          "url": "https://linkedin.com/feed/update/..."
        },
        "twitter": {
          "status": "published",
          "post_id": "1765432109876543210",
          "url": "https://twitter.com/camilo_builds/status/..."
        },
        "instagram": {
          "status": "published",
          "post_id": "18234567890123456",
          "url": "https://instagram.com/p/..."
        }
      }
    },
    "es": {
      "text": "Aprende a gestionar flujos de trabajo de ComfyUI con Pilaster...",
      "platforms": {
        "instagram": {
          "status": "published",
          "post_id": "18345678901234567",
          "url": "https://instagram.com/p/..."
        },
        "facebook": {
          "status": "published",
          "post_id": "108901234567890_234567890123456",
          "url": "https://facebook.com/..."
        }
      }
    }
  },
  "published_at": "2026-02-27T10:00:00Z",
  "total_posts": 5
}
```

---

### File Locations

**In Holus repo:**

| File | Change Type | Description |
|------|-------------|-------------|
| `.claude/settings.json` | Modified | Add social-media MCP server config |
| `src/holus/agents/marketing/social_workflow.py` | New | Social media posting workflow |

**In social-media-automatization repo (to be added to existing MCP server):**

| Tool | Description |
|------|-------------|
| `get_analytics` | Get engagement analytics for recent posts |
| `get_top_posts` | Get best performing posts ranked by metric |
| `post_story` | Post stories to Instagram/Facebook |
| `get_accounts` | Get connected account information |

---

### Edge Cases & Error Handling

**EDGE-001: Social-media service unavailable**
- Scenario: social-media-automatization service is down
- Expected behavior: Content saved to local queue. Agent logs error and continues with other tasks.
- Recovery: Retry queue checked every 15 minutes via launchd.

**EDGE-002: MCP connection lost mid-operation**
- Scenario: MCP connection drops during posting
- Expected behavior: Agent retries MCP connection. If persistent, logs error and moves on.
- Recovery: Next cycle retries the content.

**EDGE-003: Bilingual post requested but no account mapping configured**
- Scenario: Agent requests bilingual post for a platform without ES account
- Expected behavior: Post to EN account only. Warning logged.
- Recovery: Manual — configure ES account or disable bilingual for that platform.

**EDGE-004: Platform-specific failure (partial success)**
- Scenario: LinkedIn succeeds but Instagram fails (e.g., media format issue)
- Expected behavior: Successful platforms recorded. Failed platform queued for retry.
- Recovery: Automatic retry for failed platform only.

**EDGE-005: Translation fails**
- Scenario: Google Translate API unreachable
- Expected behavior: Post EN version only. Log translation failure.
- Recovery: Retry translation on next post.

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Post to single platform | < 5s | MCP call latency |
| Post bilingual (5 platforms) | < 30s | End-to-end including translation |
| Analytics fetch (7 days) | < 10s | MCP call latency |
| Top posts ranking | < 5s | In-memory sorting |
| Schedule post | < 3s | Database write |
| Get scheduled posts | < 2s | Database query |

---

### Security Considerations

- `SOCIAL_MEDIA_API_KEY` stored in `.env` only
- API key provides publish access to all platforms — protect it
- Account configuration lives in social-media-automatization, not in Holus
- Analytics data may contain follower demographics — privacy compliant aggregation only

---

### Out of Scope

- Direct platform OAuth (handled by service setup)
- Comment/reply management (analytics only for now)
- Paid promotion / ads (organic content only)
- Influencer outreach
- User-generated content moderation

---

### Related Specs

- [010-marketing-agent.md](./010-marketing-agent.md) — the agent that calls social media tools
- [011-social-media-integration.md](./011-social-media-integration.md) — V1 spec (deprecated, superseded by this spec)
- [014-genpeli-integration.md](./014-genpeli-integration.md) — video content for social media
- [015-pilaster-integration.md](./015-pilaster-integration.md) — image content for social media
- [012-knowledge-learning.md](./012-knowledge-learning.md) — learning loop consumes analytics from this MCP

---

**Last Updated:** 2026-02-27  
**Status:** Not Started
**Owner:** Camilo Martinez
