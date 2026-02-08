# Content Data Warehouse Schema

**Status:** PENDING APPROVAL  
**Date:** 2026-02-08  
**Host:** Supabase (Postgres + pgvector)

---

## Overview

Unified schema to replace your 3 Notion databases:
- **Thought Content DB** → `posts` (type='thought')
- **Content DB** → `posts` (type='content')
- **Short DB** → `posts` (type='short')

**Result of 4-cycle expert debate:**
- 🏞️ Data Lake Expert: DuckDB
- 🏛️ Data Warehouse Expert: Postgres ✅
- 🤖 AI Engineer: Postgres ✅

**Winner: Postgres + pgvector (2-1 vote)**

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Thought Content │     │   Content DB    │     │    Short DB     │
│   (Notion)      │     │   (Notion)      │     │   (Notion)      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Supabase (Postgres)  │
                    │      + pgvector        │
                    └────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
              ┌──────────┐             ┌──────────────┐
              │  HOLUS   │             │ BI Dashboard │
              │ (Agents) │             │  (Metabase)  │
              └──────────┘             └──────────────┘
```

---

## Tables (5 + 1 Materialized View)

### 1. `dim_accounts` — Platforms & Languages

Your social media accounts (4 platforms × 2 languages = ~8 rows).

| Column | Type | Description |
|--------|------|-------------|
| `account_id` | SERIAL | Primary key |
| `platform` | VARCHAR(20) | 'twitter', 'instagram', 'youtube', 'tiktok' |
| `language` | VARCHAR(10) | 'en', 'es' |
| `handle` | TEXT | @username |
| `profile_url` | TEXT | Link to profile |
| `followers` | BIGINT | Current follower count |
| `created_at` | TIMESTAMPTZ | Record created |
| `updated_at` | TIMESTAMPTZ | Last updated |

**Indexes:**
- Unique: `(platform, language)`
- Fuzzy search: `handle` (trigram)

---

### 2. `dim_tags` — Content Tags

Normalized tags for filtering and BI slicing.

| Column | Type | Description |
|--------|------|-------------|
| `tag_id` | SERIAL | Primary key |
| `name` | TEXT | Tag name (unique) |
| `category` | VARCHAR(50) | 'topic', 'mood', 'series', etc. |
| `created_at` | TIMESTAMPTZ | Record created |

**Indexes:**
- Unique: `name`
- Fuzzy search: `name` (trigram)

---

### 3. `post_tags` — Junction Table (Many-to-Many)

Links posts to tags.

| Column | Type | Description |
|--------|------|-------------|
| `post_id` | INTEGER | FK → posts.post_id |
| `tag_id` | INTEGER | FK → dim_tags.tag_id |

**Primary Key:** `(post_id, tag_id)`

---

### 4. `posts` — Unified Content (⭐ Main Table)

All your content in one place. Replaces 3 Notion DBs.

| Column | Type | Description |
|--------|------|-------------|
| `post_id` | SERIAL | Primary key |
| `account_id` | INTEGER | FK → dim_accounts.account_id |
| `type` | VARCHAR(20) | **'thought'**, **'content'**, or **'short'** |
| `title` | TEXT | Post title |
| `url` | TEXT | Unique URL (Notion page or published link) |
| `thumbnail_url` | TEXT | Thumbnail image |
| `raw_data` | JSONB | **Full Notion payload** (schema flexibility) |
| `embedding` | VECTOR(1536) | OpenAI embedding for similarity search |
| `text_content` | TEXT | Auto-generated from raw_data (for search) |
| `created_at` | TIMESTAMPTZ | When content was created |
| `published_at` | TIMESTAMPTZ | When published (null if draft) |
| `status` | VARCHAR(20) | 'draft', 'published', 'archived' |

**Indexes:**
- `(account_id, type)` — filter by platform + content type
- `title` (trigram) — fuzzy text search
- `embedding` (HNSW) — vector similarity <50ms
- `embedding` (IVFFlat) — fallback vector index

**Key Feature:** `raw_data` JSONB preserves ALL Notion fields. If Notion schema changes, no migration needed.

---

### 5. `post_metrics` — Daily Performance (Partitioned)

Daily snapshots of engagement metrics. Partitioned by date for scale.

| Column | Type | Description |
|--------|------|-------------|
| `metric_id` | BIGSERIAL | Auto-increment |
| `post_id` | INTEGER | FK → posts.post_id |
| `snapshot_date` | DATE | **Partition key** |
| `views` | BIGINT | View count |
| `likes` | BIGINT | Like count |
| `comments` | BIGINT | Comment count |
| `shares` | BIGINT | Share/retweet count |
| `engagement_rate` | FLOAT | Auto-calculated: (likes+comments+0.5*shares)/views |
| `raw_metrics` | JSONB | Platform-specific metrics (flexibility) |

**Primary Key:** `(post_id, snapshot_date)`

**Partitioning:** Monthly partitions auto-created. Handles 1B+ rows.

---

### 6. `mv_monthly_performance` — BI Summary (Materialized View)

Pre-aggregated monthly stats. Refreshed daily by cron.

| Column | Type | Description |
|--------|------|-------------|
| `account_id` | INTEGER | Account reference |
| `type` | VARCHAR | Content type |
| `month` | DATE | Truncated to month |
| `post_count` | INTEGER | Posts that month |
| `avg_engagement` | FLOAT | Average engagement rate |
| `total_views` | BIGINT | Sum of views |

---

## Example Queries

### HOLUS Agent: Find Similar Content
```sql
SELECT post_id, title, url, 
       1 - (embedding <=> '[0.1, -0.2, ...]'::vector) AS similarity
FROM posts 
WHERE status = 'published'
ORDER BY embedding <=> '[0.1, -0.2, ...]'::vector 
LIMIT 10;
```
**Performance:** <50ms on 100K rows

### BI: Top Platforms (Last 90 Days)
```sql
SELECT a.platform, a.language, 
       AVG(m.engagement_rate) as avg_engagement,
       SUM(m.views) as total_views
FROM post_metrics m 
JOIN posts p ON m.post_id = p.post_id
JOIN dim_accounts a ON p.account_id = a.account_id
WHERE m.snapshot_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY a.platform, a.language 
ORDER BY total_views DESC;
```

### Get All Shorts for Twitter (Spanish)
```sql
SELECT p.* 
FROM posts p
JOIN dim_accounts a ON p.account_id = a.account_id
WHERE p.type = 'short' 
  AND a.platform = 'twitter' 
  AND a.language = 'es';
```

---

## Migration Plan

### Step 1: Create Supabase Project
- Go to supabase.com → New Project
- Enable pgvector extension

### Step 2: Run DDL
- Execute table creation SQL (I'll provide full script)

### Step 3: Migrate Notion Data
- Python script queries 3 Notion DBs
- Embeds content via OpenAI
- Upserts to Supabase

### Step 4: Set Up Sync
- Daily cron: Pull new/updated Notion pages
- Daily cron: Fetch metrics from platform APIs

**Estimated time:** ~1 hour

---

## Cost

| Component | Cost |
|-----------|------|
| Supabase (free tier) | $0/mo (500MB, 2 projects) |
| OpenAI embeddings | ~$0.10 per 1000 posts |
| Total | **< $1/mo** for your scale |

---

## Approval Checklist

- [ ] Table structure looks correct
- [ ] Fields cover all my Notion data
- [ ] JSONB flexibility for future changes
- [ ] Vector search for HOLUS agents
- [ ] BI-ready for dashboards
- [ ] Hosting on Supabase approved

---

**Ready to implement?** Reply with approval and I'll:
1. Create Supabase project
2. Deploy schema
3. Write migration script
4. Set up sync cron

🦞
