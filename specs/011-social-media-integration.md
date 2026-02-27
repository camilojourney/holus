# Spec 011: Social Media Integration

## Feature: Unified social media posting and analytics via Late API with MCP server interface

### Overview

Holus needs to post content to social media and read analytics back. This spec defines a two-layer approach: (1) a Python client for the Late API that handles posting to 13 platforms with one call, and (2) a local MCP server that wraps this client so the marketing agent can call it as a tool. The MCP server pattern allows the marketing agent to discover and call social media tools dynamically, following the same architecture planned for genpeli and pilaster silos. Phase 1 starts with direct Late API integration for LinkedIn + Twitter. Phase 2 adds the MCP server layer and more platforms.

### User Stories

- As the marketing agent, I want to post content to LinkedIn and Twitter so that content reaches the audience.
- As the marketing agent, I want to read analytics for published posts so that I can learn what works.
- As a founder, I want human approval before any post goes live so that nothing embarrassing is published.
- As a founder, I want to schedule posts at optimal times so that engagement is maximized.

---

### Core Specifications

**SPEC-001: Late API Client**

| Field | Value |
|-------|-------|
| Description | Python httpx client for the Late API (late.so) that handles posting, scheduling, and analytics |
| Trigger | Marketing agent act stage calls publish/analytics methods |
| Input | Content text, platform list, optional media URLs, optional schedule time |
| Output | Post IDs, publishing status per platform, analytics data |
| Validation | Text within platform limits. At least one platform specified. |
| Auth Required | `LATE_API_KEY` |

```python
# src/holus/integrations/late_api/client.py

from __future__ import annotations

import httpx
from pydantic import BaseModel


class PostRequest(BaseModel):
    text: str
    platforms: list[str]
    media_urls: list[str] = []
    schedule_time: str | None = None  # ISO 8601
    platform_overrides: dict[str, dict] = {}


class PostResult(BaseModel):
    post_id: str
    platform_results: dict[str, dict]
    scheduled: bool
    failed_platforms: list[str]
    error_details: dict[str, str]


class AnalyticsData(BaseModel):
    post_id: str
    platform: str
    impressions: int
    engagement_rate: float
    clicks: int
    shares: int
    comments: int
    follower_delta: int
    collected_at: str


PLATFORM_LIMITS = {
    "twitter": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "tiktok": 2200,
    "youtube": 5000,
    "bluesky": 300,
    "threads": 500,
    "mastodon": 500,
    "facebook": 63206,
    "pinterest": 500,
    "telegram": 4096,
    "discord": 2000,
    "reddit": 40000,
}


class LateAPIClient:
    BASE_URL = "https://api.late.so/v1"

    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def validate_content(self, text: str, platforms: list[str]) -> list[str]:
        """Check text fits platform limits. Returns list of violations."""
        violations = []
        for platform in platforms:
            limit = PLATFORM_LIMITS.get(platform)
            if limit and len(text) > limit:
                violations.append(
                    f"{platform}: {len(text)} chars exceeds {limit} limit"
                )
        return violations

    async def publish(self, request: PostRequest) -> PostResult:
        violations = self.validate_content(request.text, request.platforms)
        if violations:
            raise ValueError(f"Content too long: {violations}")

        response = await self.client.post(
            "/posts", json=request.model_dump()
        )
        response.raise_for_status()
        return PostResult.model_validate(response.json())

    async def get_analytics(
        self, post_id: str, platform: str | None = None
    ) -> list[AnalyticsData]:
        params = {}
        if platform:
            params["platform"] = platform
        response = await self.client.get(
            f"/posts/{post_id}/analytics", params=params
        )
        response.raise_for_status()
        return [AnalyticsData.model_validate(d) for d in response.json()]

    async def get_all_analytics(self, days: int = 7) -> list[AnalyticsData]:
        response = await self.client.get(
            "/analytics", params={"days": days}
        )
        response.raise_for_status()
        return [AnalyticsData.model_validate(d) for d in response.json()]

    async def get_scheduled(self) -> list[dict]:
        response = await self.client.get("/posts/scheduled")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self.client.aclose()
```

Acceptance Criteria:
- [ ] `LateAPIClient` can publish to multiple platforms in one call
- [ ] Content length validation catches violations before API call
- [ ] `platform_overrides` allows per-platform text customization
- [ ] Analytics retrieval works per post and in bulk
- [ ] Scheduled posts work with ISO 8601 timestamps
- [ ] Client handles 429 (rate limit) with retry
- [ ] Client handles 5xx with exponential backoff

---

**SPEC-002: Social Media MCP Server**

| Field | Value |
|-------|-------|
| Description | Local MCP server that wraps the Late API client, exposing tools the marketing agent can discover and call |
| Trigger | Marketing agent connects to the MCP server at startup |
| Input | Tool calls from the marketing agent |
| Output | Tool results (analytics data, post results) |
| Validation | All inputs validated by Pydantic before passing to Late API |
| Auth Required | `LATE_API_KEY` (server-side) |

```python
# src/holus/mcp_servers/social_media.py

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("social-media")


@mcp.tool()
async def get_analytics(days: int = 7, platform: str = "all") -> str:
    """Get social media engagement analytics for recent posts.

    Args:
        days: Number of days to look back (default 7)
        platform: Filter by platform or 'all' for aggregate
    """
    client = get_late_client()
    data = await client.get_all_analytics(days=days)
    if platform != "all":
        data = [d for d in data if d.platform == platform]
    return json.dumps([d.model_dump() for d in data])


@mcp.tool()
async def get_top_posts(
    limit: int = 10, metric: str = "engagement_rate"
) -> str:
    """Get the best performing posts by a metric.

    Args:
        limit: Number of top posts to return
        metric: Rank by engagement_rate, impressions, clicks, or shares
    """
    client = get_late_client()
    data = await client.get_all_analytics(days=30)
    sorted_data = sorted(
        data, key=lambda d: getattr(d, metric, 0), reverse=True
    )
    return json.dumps([d.model_dump() for d in sorted_data[:limit]])


@mcp.tool()
async def schedule_post(
    text: str,
    platforms: str,
    media_urls: str = "",
    schedule_time: str = "",
) -> str:
    """Schedule a post for publishing on social media platforms.

    IMPORTANT: Requires human approval in Phase 1.

    Args:
        text: The post content
        platforms: Comma-separated platform list (linkedin,twitter,tiktok)
        media_urls: Comma-separated media URLs (optional)
        schedule_time: ISO 8601 datetime for scheduling (optional, empty = immediate)
    """
    client = get_late_client()
    request = PostRequest(
        text=text,
        platforms=platforms.split(","),
        media_urls=media_urls.split(",") if media_urls else [],
        schedule_time=schedule_time or None,
    )
    result = await client.publish(request)
    return result.model_dump_json()


@mcp.tool()
async def get_posting_queue() -> str:
    """Get currently scheduled posts waiting to be published."""
    client = get_late_client()
    scheduled = await client.get_scheduled()
    return json.dumps(scheduled)


if __name__ == "__main__":
    mcp.run()
```

MCP server configuration for Claude Code:

```json
{
  "mcpServers": {
    "social-media": {
      "command": "python",
      "args": ["-m", "holus.mcp_servers.social_media"],
      "cwd": "/Users/mini/.openclaw/workspace/github/holus",
      "env": {
        "LATE_API_KEY": "${LATE_API_KEY}"
      }
    }
  }
}
```

Acceptance Criteria:
- [ ] MCP server starts and responds to `tools/list`
- [ ] `get_analytics` tool returns engagement data
- [ ] `get_top_posts` tool returns ranked posts
- [ ] `schedule_post` tool publishes content
- [ ] `get_posting_queue` tool returns scheduled posts
- [ ] All tools have clear descriptions and typed arguments
- [ ] Server can be registered in `.claude/settings.json`

---

**SPEC-003: Content Queue (Human Approval Gate)**

| Field | Value |
|-------|-------|
| Description | Phase 1 content goes to a review queue before posting. Human approves via CLI or Telegram. |
| Trigger | Marketing agent generates content |
| Input | Generated content piece |
| Output | Content saved to `data/content-queue/` as YAML |
| Validation | Each piece has a unique ID and all required fields |
| Auth Required | No |

```python
# src/holus/agents/marketing/content_queue.py

from __future__ import annotations

import yaml
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel


class QueuedContent(BaseModel):
    piece_id: str
    product: str
    platform: str
    content_type: str
    topic: str
    text: str
    reasoning: str
    generated_at: datetime
    status: str = "pending_review"  # pending_review | approved | rejected | published


QUEUE_DIR = Path("data/content-queue")


def enqueue(content: QueuedContent) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    path = QUEUE_DIR / f"{content.piece_id}.yaml"
    path.write_text(yaml.dump(content.model_dump(), default_flow_style=False))
    return path


def list_pending() -> list[QueuedContent]:
    if not QUEUE_DIR.exists():
        return []
    pending = []
    for f in sorted(QUEUE_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        if data.get("status") == "pending_review":
            pending.append(QueuedContent.model_validate(data))
    return pending


def approve(piece_id: str) -> None:
    path = QUEUE_DIR / f"{piece_id}.yaml"
    data = yaml.safe_load(path.read_text())
    data["status"] = "approved"
    path.write_text(yaml.dump(data, default_flow_style=False))


def reject(piece_id: str, reason: str = "") -> None:
    path = QUEUE_DIR / f"{piece_id}.yaml"
    data = yaml.safe_load(path.read_text())
    data["status"] = "rejected"
    data["rejection_reason"] = reason
    path.write_text(yaml.dump(data, default_flow_style=False))
```

CLI commands:

```just
# Review pending content
review-content:
    python -m holus.agents.marketing.review

# Approve a content piece
approve-content piece_id:
    python -m holus.agents.marketing.review --approve {{piece_id}}

# Reject a content piece
reject-content piece_id reason="":
    python -m holus.agents.marketing.review --reject {{piece_id}} --reason "{{reason}}"

# Publish all approved content
publish-approved:
    python -m holus.agents.marketing.publish_approved
```

Acceptance Criteria:
- [ ] Content saved to `data/content-queue/` as YAML files
- [ ] `just review-content` lists all pending content
- [ ] `just approve-content <id>` marks content as approved
- [ ] `just reject-content <id>` marks content as rejected
- [ ] `just publish-approved` publishes all approved content via Late API
- [ ] Approved content is published and status updated to "published"

---

### Data Structures

Analytics summary (what the agent reads during observe):

```json
{
  "period_days": 7,
  "total_impressions": 15420,
  "avg_engagement_rate": 0.045,
  "top_performing": {
    "content_type": "tutorial",
    "platform": "linkedin",
    "topic": "ComfyUI workflow management"
  },
  "platform_breakdown": {
    "linkedin": {"impressions": 8200, "engagement_rate": 0.067},
    "twitter": {"impressions": 5100, "engagement_rate": 0.032},
    "tiktok": {"impressions": 2120, "engagement_rate": 0.051}
  },
  "product_breakdown": {
    "pilaster": {"posts": 5, "avg_engagement": 0.058},
    "genpeli": {"posts": 3, "avg_engagement": 0.041},
    "invoz": {"posts": 2, "avg_engagement": 0.035}
  }
}
```

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/integrations/late_api/__init__.py` | Modified | Export LateAPIClient |
| `src/holus/integrations/late_api/client.py` | New | Late API client |
| `src/holus/mcp_servers/__init__.py` | New | MCP servers module |
| `src/holus/mcp_servers/social_media.py` | New | Social media MCP server |
| `src/holus/agents/marketing/content_queue.py` | New | Content review queue |
| `src/holus/agents/marketing/review.py` | New | CLI for reviewing content |
| `src/holus/agents/marketing/publish_approved.py` | New | Publish approved content |
| `data/content-queue/` | New (gitignored) | Content queue directory |
| `tests/unit/integrations/test_late_api.py` | New | Late API client tests |
| `tests/unit/mcp/test_social_media.py` | New | MCP server tests |

---

### Edge Cases & Error Handling

**EDGE-001: Late API unavailable**
- Scenario: Late API returns 5xx or times out
- Expected behavior: Content saved to queue with status "retry_pending". n8n retry workflow checks every 15 min.
- Recovery: Automatic retry when API returns.

**EDGE-002: Late API key invalid or expired**
- Scenario: 401 response from Late API
- Expected behavior: Kill switch activated for content publishing. Error logged. Human notified.
- Recovery: Human updates LATE_API_KEY in .env.

**EDGE-003: Platform-specific failure (partial success)**
- Scenario: LinkedIn succeeds but Twitter fails
- Expected behavior: Successful platforms recorded. Failed platform queued for retry.
- Recovery: Automatic retry for failed platform only.

**EDGE-004: No Late API key configured (fresh install)**
- Scenario: LATE_API_KEY not set in .env
- Expected behavior: Agent runs observe and reason stages normally. Act stage saves content to queue with status "no_api_key". Human can review content and manually post.
- Recovery: Human adds LATE_API_KEY and runs `just publish-approved`.

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Publish to all platforms | < 30s | Late API round-trip |
| Analytics fetch (7 days) | < 10s | Late API analytics call |
| Content queue save | < 100ms | Local file write |
| MCP server startup | < 2s | Time to first tool response |

---

### Security Considerations

- `LATE_API_KEY` stored in `.env` only, never in code
- Late API key provides publish access to all connected platforms — protect it
- Content queue files may contain post text but no secrets
- MCP server runs locally only (not exposed to network)

---

### Out of Scope

- Direct platform API integrations (use Late API as unified layer)
- Social media account setup/OAuth (done in Late.so dashboard)
- Comment/reply management (read-only analytics for now)
- Paid promotion / ads management

---

### Related Specs

- [010-marketing-agent.md](./010-marketing-agent.md) — the agent that calls these tools
- [003-content-pipeline.md](./003-content-pipeline.md) — full content pipeline including images and video

---

**Last Updated:** 2026-02-26
**Status:** Not Started
**Owner:** Camilo Martinez
