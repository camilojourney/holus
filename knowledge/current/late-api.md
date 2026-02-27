# Late API Research (2026-02-27)

## Overview

Late.so (https://getlate.dev) is a unified social media API that allows posting to 13+ platforms with a single API call.

**Supported Platforms:**
- Twitter/X
- Instagram
- Facebook
- LinkedIn
- TikTok
- YouTube
- Pinterest
- Reddit
- Bluesky
- Threads
- Google Business Profile
- Telegram
- Snapchat

## Authentication

- **Method:** Bearer token authentication
- **Header:** `Authorization: Bearer YOUR_API_KEY`
- **Base URL:** `https://getlate.dev/api/v1`

## Key Endpoints

### Accounts
```bash
GET /api/v1/accounts
# Returns list of connected social media accounts with their _id values
```

### Posts

#### Create Post
```bash
POST /api/v1/posts
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "content": "Post text content",
  "accountIds": ["account_id_1", "account_id_2"],
  "scheduledFor": "2024-11-01T10:00:00Z",  // Optional, ISO 8601
  "media": ["https://example.com/image.jpg"],  // Optional
  "platformOverrides": {  // Optional
    "twitter": { "content": "Shorter version for Twitter" }
  }
}
```

#### Update Post
```bash
PUT /api/v1/posts/{postId}
Content-Type: application/json

{
  "content": "Updated content",
  "scheduledFor": "2024-11-02T14:00:00Z"
}
```

#### List Posts
```bash
GET /api/v1/posts?status=scheduled&limit=50
```

#### Get Post Details
```bash
GET /api/v1/posts/{postId}
```

#### Delete Post
```bash
DELETE /api/v1/posts/{postId}
```

### Analytics

Based on research, Late API likely provides:
- Post performance metrics (impressions, engagement, clicks)
- Per-platform breakdown
- Time-series data for tracking trends

**Probable endpoint:**
```bash
GET /api/v1/posts/{postId}/analytics
GET /api/v1/analytics?days=7&platform=linkedin
```

**Expected metrics:**
- `impressions`: Total views
- `engagement_rate`: (likes + comments + shares) / impressions
- `clicks`: Link clicks
- `shares`: Reshares/retweets
- `comments`: Comment count
- `follower_delta`: New followers attributed to post

## Character Limits (as documented in spec)

| Platform | Limit |
|----------|-------|
| Twitter/X | 280 |
| LinkedIn | 3000 |
| Instagram | 2200 |
| TikTok | 2200 |
| YouTube | 5000 |
| Bluesky | 300 |
| Threads | 500 |
| Mastodon | 500 |
| Facebook | 63206 |
| Pinterest | 500 |
| Telegram | 4096 |
| Discord | 2000 |
| Reddit | 40000 |

## Error Handling

- **401:** Invalid or expired API key
- **429:** Rate limit exceeded (implement retry with exponential backoff)
- **5xx:** Server errors (implement retry logic)
- **Partial failures:** Some platforms succeed, others fail (Late returns per-platform status)

## Best Practices

1. **Validate content length** before API call to avoid platform-specific failures
2. **Use `platformOverrides`** to customize content per platform (e.g., shorter for Twitter)
3. **Schedule strategically** using ISO 8601 timestamps
4. **Handle partial failures** gracefully (log successful platforms, retry failed ones)
5. **Respect rate limits** with exponential backoff
6. **Store `accountIds`** after initial account list fetch (they're stable)

## Alternative: Buffer API

If Late.so doesn't meet needs, Buffer (buffer.com) is the industry-standard alternative:
- Similar multi-platform posting
- More mature analytics
- Higher pricing tier required for API access
- Better documentation and SDKs

**Decision:** Starting with Late.so per spec. Will evaluate Buffer if Late has limitations.

## MCP Server Integration

Late.so provides a Social Media MCP server (mentioned in their docs at /resources/mcp). This could be used instead of building our own, but we're building a custom one per spec to:
1. Match Holus architecture (local MCP servers for each silo)
2. Add human approval workflow
3. Customize for marketing agent needs

## Implementation Notes

- Using `httpx.AsyncClient` for async/await support
- Pydantic models for request/response validation
- Retry logic with `tenacity` library for 429/5xx errors
- Content queue in `data/content-queue/` for human approval gate (Phase 1)

---

**Last researched:** 2026-02-27 03:20 AM EST
**Spec reference:** specs/011-social-media-integration.md
