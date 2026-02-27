# Knowledge: Social Media Platforms

**Last updated:** 2026-02-26
**Updated by:** human + research agent
**Confidence:** high (based on 2025-2026 platform data)
**Affects:** marketing agent posting decisions, content formatting, scheduling
**Research cadence:** monthly

---

## Platform Profiles

### LinkedIn

| Field | Value |
|-------|-------|
| API | Share API v2, OAuth 2.0 |
| Best for | Pilaster (B2B), genpeli (professional creators), invoz (developers) |
| Audience | Professionals, developers, decision-makers |
| Character limit | 3,000 |
| Best content | Document carousels (PDF slides), native video <3min, long-form text with line breaks, polls |
| Posting frequency | 3-5x/week |
| Best times (EST) | Tue-Thu 8-10am, Wed 12pm |
| Rate limits | 100 posts/day (member), 150 (page) |
| Analytics API | Yes — impressions, clicks, engagement, follower demographics |
| Key metric | Engagement rate (likes + comments + shares / impressions) |
| Algorithm notes | Favors native content over links. Dwell time matters. First-hour engagement critical. |

### Twitter / X

| Field | Value |
|-------|-------|
| API | v2 API |
| Best for | invoz (developer community), Pilaster (AI/ML community) |
| Audience | Developers, tech enthusiasts, AI community |
| Character limit | 280/tweet, threads unlimited |
| Best content | Threads (6-12 tweets), single tweet + image, quote tweets, polls |
| Posting frequency | 3-5x/day (with threads) |
| Best times (EST) | 8-10am, 12-1pm, 5-6pm |
| Rate limits | Free: 17 tweets/12hrs. Basic ($100/mo): 100/24hrs |
| Analytics API | Limited on free/basic. Pro ($5000/mo) for full analytics |
| Key metric | Impressions, retweets, bookmark rate |
| Algorithm notes | Engagement in first 30 min determines reach. Threads get algorithmic boost. |

### TikTok

| Field | Value |
|-------|-------|
| API | Content Posting API (requires developer approval) |
| Best for | Pilaster (tutorial demos), genpeli (video showcases) |
| Audience | Creators, visual learners, younger tech audience |
| Character limit | 2,200 caption |
| Best content | Vertical video 15-60s, tutorials with on-screen text, before/after, hooks in first 3s |
| Posting frequency | 1-3x/day |
| Best times (EST) | 7-9pm weekdays, 11am-3pm weekends |
| Rate limits | 20 videos/day, 2 min between posts |
| Analytics API | Research API (approved partners). Limited public analytics. |
| Key metric | Watch time, completion rate, shares |
| Algorithm notes | First 3 seconds decide everything. Loopable content gets pushed. Niche > broad. |

### Instagram

| Field | Value |
|-------|-------|
| API | Graph API via Meta (business/creator accounts only) |
| Best for | genpeli (before/after demos), Pilaster (visual art) |
| Audience | Creative professionals, visual content consumers |
| Character limit | 2,200 caption |
| Best content | Reels (15-90s), carousels (10 slides), single image + long caption |
| Posting frequency | 3-5x/week feed, daily stories |
| Best times (EST) | 11am-1pm, 7-9pm |
| Rate limits | 25 API calls/user/hour publishing, max 50 posts/day |
| Analytics API | Yes — impressions, reach, engagement, audience demographics |
| Key metric | Saves, shares, reach |
| Algorithm notes | Reels get 3-5x reach vs feed posts. Saves signal high value content. |

### YouTube Shorts

| Field | Value |
|-------|-------|
| API | Data API v3 |
| Best for | Pilaster (workflow demos), genpeli (AI video demos) |
| Audience | Learners, tutorial seekers |
| Character limit | 5,000 description |
| Best content | Vertical video <60s, hooks in first 3s, educational content |
| Posting frequency | 3-5x/week |
| Best times (EST) | 12-3pm Fri-Sat, 5-6pm weekdays |
| Rate limits | 10,000 units/day (video upload = 1600 units) |
| Analytics API | Full via YouTube Analytics API |
| Key metric | Watch time, subscriber conversion |
| Algorithm notes | YouTube promotes Shorts to non-subscribers. Good for discovery. |

### Bluesky

| Field | Value |
|-------|-------|
| API | AT Protocol (open, no API keys needed — handle/password auth) |
| Best for | invoz (developer community), tech audience |
| Audience | Tech-forward, decentralization enthusiasts |
| Character limit | 300 |
| Best content | Short text posts, images, links |
| Posting frequency | 3-5x/day |
| Rate limits | ~1,666 actions/5min, 35K/day (generous) |
| Analytics API | No built-in (use firehose for tracking) |
| Key metric | Reposts, likes |
| Algorithm notes | Chronological + custom feeds. Growing developer community. |

### Threads

| Field | Value |
|-------|-------|
| API | Meta API (launched mid-2024) |
| Best for | Cross-posting from Instagram content |
| Audience | Instagram spillover audience |
| Character limit | 500 |
| Best content | Text-based posts, images |
| Posting frequency | 3-5x/week |
| Rate limits | 250 posts/24hrs, 50 replies/24hrs |
| Analytics API | Limited |

---

## Platform Priority for Holus Products

### Phase 1 (Immediate — highest ROI)

| Priority | Platform | Products | Why |
|----------|----------|----------|-----|
| 1 | LinkedIn | All 3 | B2B audience matches all products. Best analytics. Professional credibility. |
| 2 | Twitter/X | invoz, Pilaster | Developer community. Thread format for tutorials. |
| 3 | TikTok | Pilaster, genpeli | Visual demos. Massive discovery potential. |

### Phase 2 (After first 4 weeks of data)

| Priority | Platform | Products | Why |
|----------|----------|----------|-----|
| 4 | YouTube Shorts | Pilaster, genpeli | Tutorial discovery. Long-tail SEO value. |
| 5 | Instagram | genpeli | Visual portfolio. Before/after demos. |
| 6 | Bluesky | invoz | Growing dev community. Easy API. |

### Phase 3 (After 8 weeks)

Expand to remaining platforms based on data.

---

## Unified Distribution Strategy

Use Late API (`late.so`) as the primary distribution layer.
It handles 13 platforms with one API call.

**Fallback plan** (if Late API has issues):
1. Direct LinkedIn API (highest priority)
2. Direct Twitter/X API
3. TikTok Content Posting API
4. Meta Graph API (Instagram + Threads)

---

## Posting Schedule Template

| Day | LinkedIn | Twitter/X | TikTok |
|-----|---------|-----------|--------|
| Mon | Product tip | Thread: tutorial | Tutorial video |
| Tue | Case study | Engagement post | Behind-the-scenes |
| Wed | — | Quote + insight | — |
| Thu | Technical deep-dive | Thread: tips | Demo video |
| Fri | Week recap / learnings | Engagement post | Fun/creative |
| Sat | — | — | Tutorial video |
| Sun | Strategy planning (internal) | — | — |

---

## What Changed vs Last Version

Initial comprehensive seed based on 2025-2026 platform data and API documentation.
