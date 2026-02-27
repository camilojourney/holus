# Spec 016: Social Media Integration V2

## Feature: Enhanced multi-platform posting with bilingual routing, analytics, and intelligent scheduling

### Overview

This is the V2 enhancement of Spec 011 (Social Media Integration). It expands the integration beyond LinkedIn and Twitter to all supported platforms (Instagram, Facebook, Threads), adds bilingual EN/ES routing based on account configuration, integrates the local `social-media-automatization` service alongside Late API for platform flexibility, and provides comprehensive analytics feedback. The integration maintains the federated MCP pattern: social services run independently, and the MCP server translates marketing agent intentions into API calls.

### User Stories

- As the marketing agent, I want to post bilingual content (EN + ES) to platform-specific accounts so that both audiences are reached.
- As the marketing agent, I want to use the local social-media service for enhanced features (bilingual routing, voice profiles) and Late API as a fallback.
- As the marketing agent, I want to retrieve analytics for all platforms so that I learn what works across different audiences.
- As a founder, I want content posted at optimal times per platform so that engagement is maximized.
- As a founder, I want to approve content before it goes live on high-risk platforms (Instagram, TikTok) while auto-posting to low-risk ones (LinkedIn, Twitter).

---

### Core Specifications

**SPEC-001: Enhanced Social Media MCP Server**

| Field | Value |
|-------|-------|
| Description | Unified MCP server that routes to either the local social-media service or Late API based on feature requirements |
| Trigger | Marketing agent connects to the MCP server at startup |
| Input | Tool calls from the marketing agent (post content, get analytics, schedule, etc.) |
| Output | Tool results (post IDs, analytics data, scheduling confirmations) |
| Validation | All inputs validated before passing to backend services |
| Auth Required | `SOCIAL_MEDIA_API_KEY` (local), `LATE_API_KEY` (fallback) |

```python
# src/holus/mcp_servers/social_media.py

from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("social-media")

LOCAL_API = "http://localhost:8000"
LOCAL_API_KEY = os.environ.get("SOCIAL_MEDIA_API_KEY", "")
LATE_API = "https://api.late.so/v1"
LATE_API_KEY = os.environ.get("LATE_API_KEY", "")


def get_backend_for_request(request_features: set[str]) -> str:
    """Route to local or Late API based on feature requirements."""
    # Features only available on local service
    local_only_features = {"bilingual", "voice_profile", "story", "bilingual_routing"}
    
    if request_features & local_only_features:
        return "local"
    
    # Default to Late API for broader platform support
    return "late" if LATE_API_KEY else "local"


@mcp.tool()
async def post_content(
    text: str,
    platforms: str,
    media_urls: str = "",
    bilingual: bool = False,
    voice_profile_id: str = "",
    schedule_time: str = "",
) -> str:
    """Post content to social media platforms.

    Args:
        text: Content text
        platforms: Comma-separated platforms (linkedin,twitter,instagram,facebook,threads)
        media_urls: Comma-separated media URLs (optional)
        bilingual: Enable EN/ES bilingual routing (local service only)
        voice_profile_id: Voice profile for text enhancement (local service only)
        schedule_time: ISO 8601 datetime for scheduling (optional, empty = immediate)

    Returns:
        JSON with post IDs and status per platform
    """
    request_features = set()
    if bilingual:
        request_features.add("bilingual")
    if voice_profile_id:
        request_features.add("voice_profile")
    
    backend = get_backend_for_request(request_features)
    
    if backend == "local":
        return await _post_via_local(
            text=text,
            platforms=platforms.split(","),
            media_urls=media_urls.split(",") if media_urls else [],
            bilingual=bilingual,
            voice_profile_id=voice_profile_id,
            schedule_time=schedule_time,
        )
    else:
        return await _post_via_late(
            text=text,
            platforms=platforms.split(","),
            media_urls=media_urls.split(",") if media_urls else [],
            schedule_time=schedule_time,
        )


async def _post_via_local(
    text: str,
    platforms: list[str],
    media_urls: list[str],
    bilingual: bool,
    voice_profile_id: str,
    schedule_time: str,
) -> str:
    """Post via local social-media-automatization service."""
    async with httpx.AsyncClient() as client:
        endpoint = "/api/post-bilingual" if bilingual else "/api/post"
        
        payload = {
            "text": text,
            "platforms": platforms,
            "media_urls": media_urls,
        }
        
        if voice_profile_id:
            payload["voice_profile_id"] = int(voice_profile_id)
        
        if schedule_time:
            payload["schedule_time"] = schedule_time
        
        response = await client.post(
            f"{LOCAL_API}{endpoint}",
            json=payload,
            headers={"X-API-Key": LOCAL_API_KEY},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.text


async def _post_via_late(
    text: str,
    platforms: list[str],
    media_urls: list[str],
    schedule_time: str,
) -> str:
    """Post via Late API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LATE_API}/posts",
            json={
                "text": text,
                "platforms": platforms,
                "media_urls": media_urls,
                "schedule_time": schedule_time or None,
            },
            headers={"Authorization": f"Bearer {LATE_API_KEY}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.text


@mcp.tool()
async def post_story(
    caption: str,
    media_url: str,
    platforms: str = "instagram,facebook",
) -> str:
    """Post a story with auto-translation per account language.

    Args:
        caption: Story caption text
        media_url: Image or video URL
        platforms: Comma-separated platforms (instagram, facebook supported)

    Returns:
        JSON with story IDs per platform
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LOCAL_API}/api/post-story",
            json={
                "caption": caption,
                "media_url": media_url,
                "platforms": platforms.split(","),
            },
            headers={"X-API-Key": LOCAL_API_KEY},
        )
        response.raise_for_status()
        return response.text


@mcp.tool()
async def get_analytics(
    days: int = 7,
    platform: str = "all",
    product: str = "",
) -> str:
    """Get social media engagement analytics for recent posts.

    Args:
        days: Number of days to look back (default 7)
        platform: Filter by platform or 'all' for aggregate
        product: Filter by product mentioned in posts (optional)

    Returns:
        JSON with analytics summary and per-post breakdown
    """
    # Try local service first (has product tagging)
    if LOCAL_API_KEY:
        try:
            return await _get_analytics_local(days, platform, product)
        except Exception:
            pass  # Fall back to Late API
    
    # Fall back to Late API
    return await _get_analytics_late(days, platform)


async def _get_analytics_local(days: int, platform: str, product: str) -> str:
    """Get analytics from local service."""
    async with httpx.AsyncClient() as client:
        params = {"days": days}
        if platform != "all":
            params["platform"] = platform
        if product:
            params["product"] = product
        
        response = await client.get(
            f"{LOCAL_API}/api/analytics",
            params=params,
            headers={"X-API-Key": LOCAL_API_KEY},
        )
        response.raise_for_status()
        return response.text


async def _get_analytics_late(days: int, platform: str) -> str:
    """Get analytics from Late API."""
    async with httpx.AsyncClient() as client:
        params = {"days": days}
        if platform != "all":
            params["platform"] = platform
        
        response = await client.get(
            f"{LATE_API}/analytics",
            params=params,
            headers={"Authorization": f"Bearer {LATE_API_KEY}"},
        )
        response.raise_for_status()
        return response.text


@mcp.tool()
async def get_top_posts(
    limit: int = 10,
    metric: str = "engagement_rate",
    days: int = 30,
) -> str:
    """Get the best performing posts by a metric.

    Args:
        limit: Number of top posts to return (default 10)
        metric: Rank by engagement_rate, impressions, clicks, or shares
        days: Look back period in days (default 30)

    Returns:
        JSON array of top posts with metrics
    """
    analytics = await get_analytics(days=days)
    import json
    data = json.loads(analytics)
    
    # Sort by metric
    posts = data.get("posts", [])
    sorted_posts = sorted(
        posts,
        key=lambda p: p.get(metric, 0),
        reverse=True,
    )
    
    return json.dumps(sorted_posts[:limit])


@mcp.tool()
async def schedule_post(
    text: str,
    platforms: str,
    media_urls: str = "",
    schedule_time: str = "",
    bilingual: bool = False,
) -> str:
    """Schedule a post for future publishing.

    Args:
        text: Content text
        platforms: Comma-separated platforms
        media_urls: Comma-separated media URLs (optional)
        schedule_time: ISO 8601 datetime (required for scheduling)
        bilingual: Enable bilingual routing (local service only)

    Returns:
        Scheduled post ID and confirmation
    """
    if not schedule_time:
        raise ValueError("schedule_time required for scheduling")
    
    return await post_content(
        text=text,
        platforms=platforms,
        media_urls=media_urls,
        bilingual=bilingual,
        schedule_time=schedule_time,
    )


@mcp.tool()
async def get_scheduled_posts() -> str:
    """Get currently scheduled posts waiting to be published.

    Returns:
        JSON array of scheduled posts
    """
    # Try local service first
    if LOCAL_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{LOCAL_API}/api/schedule",
                    headers={"X-API-Key": LOCAL_API_KEY},
                )
                response.raise_for_status()
                return response.text
        except Exception:
            pass
    
    # Fall back to Late API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{LATE_API}/posts/scheduled",
            headers={"Authorization": f"Bearer {LATE_API_KEY}"},
        )
        response.raise_for_status()
        return response.text


@mcp.tool()
async def get_accounts() -> str:
    """Get list of connected social media accounts with platform info.

    Returns:
        JSON array of accounts with platform, handle, and status
    """
    # Local service has account management
    if LOCAL_API_KEY:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LOCAL_API}/api/accounts",
                headers={"X-API-Key": LOCAL_API_KEY},
            )
            response.raise_for_status()
            return response.text
    
    # Late API doesn't expose account list - return config-based info
    return json.dumps([
        {"platform": "linkedin", "status": "connected"},
        {"platform": "twitter", "status": "connected"},
        # Add others as configured
    ])


if __name__ == "__main__":
    mcp.run()
```

MCP server configuration for marketing agent:

```json
{
  "mcpServers": {
    "social-media": {
      "command": "python",
      "args": ["-m", "holus.mcp_servers.social_media"],
      "cwd": "/Users/mini/.openclaw/workspace/github/holus",
      "env": {
        "SOCIAL_MEDIA_API_KEY": "${SOCIAL_MEDIA_API_KEY}",
        "LATE_API_KEY": "${LATE_API_KEY}"
      }
    }
  }
}
```

Acceptance Criteria:
- [ ] MCP server starts and responds to `tools/list`
- [ ] `post_content` tool routes to local service for bilingual posts
- [ ] `post_content` tool routes to Late API for standard posts
- [ ] `post_story` tool uses local service for story posting
- [ ] `get_analytics` tool aggregates data from available backend
- [ ] `get_top_posts` tool ranks posts by specified metric
- [ ] `schedule_post` tool schedules content for future publishing
- [ ] `get_scheduled_posts` tool lists pending scheduled posts
- [ ] `get_accounts` tool returns connected account information
- [ ] Graceful fallback when one backend is unavailable

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

Bilingual routing configuration:

```yaml
# config/social_accounts.yaml

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

Routing logic:

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

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/mcp_servers/social_media.py` | Modified | Enhanced MCP server with dual backend support |
| `config/social_accounts.yaml` | New | Social media account configuration |
| `src/holus/agents/marketing/social_workflow.py` | New | Social media posting workflow |
| `tests/unit/mcp/test_social_media_v2.py` | New | V2 MCP server tests |

---

### Edge Cases & Error Handling

**EDGE-001: Local service unavailable, Late API available**
- Scenario: Local social-media service is down
- Expected behavior: MCP server routes to Late API. Bilingual features unavailable. Warning logged.
- Recovery: Automatic fallback. Retry local service on next post.

**EDGE-002: Both services unavailable**
- Scenario: Local service and Late API both down
- Expected behavior: Content saved to queue. Agent logs error and continues with other tasks.
- Recovery: Retry queue checked every 15 minutes via cron.

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

- `SOCIAL_MEDIA_API_KEY` and `LATE_API_KEY` stored in `.env` only
- API keys provide publish access to all platforms — protect them
- Account configuration in `config/social_accounts.yaml` is version controlled but sensitive
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
- [011-social-media-integration.md](./011-social-media-integration.md) — V1 spec (LinkedIn + Twitter only)
- [014-genpeli-integration.md](./014-genpeli-integration.md) — video content for social media
- [015-pilaster-integration.md](./015-pilaster-integration.md) — image content for social media

---

**Last Updated:** 2026-02-27  
**Status:** Draft  
**Owner:** Camilo Martinez
