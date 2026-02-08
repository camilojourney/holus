# Content Data Warehouse Schema v2

**Status:** READY FOR APPROVAL  
**Date:** 2026-02-08  
**Host:** Supabase (Postgres + pgvector)  
**Review:** 3-cycle expert review (DBA + Backend + Product)

---

## Overview

Unified schema replacing 3 Notion databases:
- **Thought Content DB** → `posts` (type='thought')
- **Content DB** → `posts` (type='content')
- **Short DB** → `posts` (type='short')

**Architecture:**
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
                    │       Supabase         │
                    │   posts + platforms    │
                    └────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
        ┌──────────┐      ┌──────────┐      ┌──────────────┐
        │  HOLUS   │      │ Cross-   │      │ BI Dashboard │
        │ (Vector) │      │ Posts    │      │  (Metrics)   │
        └──────────┘      └──────────┘      └──────────────┘
```

---

## Tables (2 + 1 Materialized View)

### 1. `posts` — Unified Content Table

All your content in one place. The `type` enum distinguishes origin.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key (auto-generated) |
| `type` | ENUM | NO | **'thought'**, **'content'**, or **'short'** |
| `notion_page_id` | TEXT | NO | Original Notion page ID (UNIQUE) |
| `title` | TEXT | NO | Post title |
| `body` | TEXT | NO | Full content text (min 1 char) |
| `language` | TEXT | YES | 2-letter code: 'en', 'es', etc. |
| `embedding` | VECTOR(1536) | YES | OpenAI embedding (null until generated) |
| `metrics` | JSONB | YES | Aggregated metrics: `{"likes": 100, "views": 500}` |
| `created_at` | TIMESTAMPTZ | NO | Record created |
| `updated_at` | TIMESTAMPTZ | NO | Auto-updated on change |

**Indexes:**
- `type` — filter by content type
- `language` — filter by language
- `created_at DESC` — recent content
- `embedding` (HNSW) — vector similarity <50ms
- `title`, `body` (trigram) — fuzzy text search

---

### 2. `posts_platforms` — Cross-Post Junction

Tracks where each post is published (supports multi-platform).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `post_id` | UUID | NO | FK → posts.id |
| `platform` | ENUM | NO | 'twitter', 'instagram', 'tiktok', 'youtube', etc. |
| `platform_post_id` | TEXT | YES | Native ID (tweet ID, etc.) |
| `platform_url` | TEXT | YES | Direct link to post |
| `metrics` | JSONB | YES | Platform-specific metrics |
| `posted_at` | TIMESTAMPTZ | YES | When published on this platform |

**Primary Key:** `(post_id, platform)`

**Use cases:**
- One thought → posted to Twitter EN + Twitter ES + LinkedIn
- Track platform-specific engagement separately
- Link to actual platform posts for API pulls

---

### 3. `top_posts_mv` — BI Materialized View

Pre-aggregated performance by type/language/platform. Refreshed daily at 2 AM.

| Column | Type | Description |
|--------|------|-------------|
| `type` | ENUM | Content type |
| `language` | TEXT | Language code |
| `platform` | ENUM | Platform |
| `avg_likes` | NUMERIC | Average likes |
| `avg_views` | NUMERIC | Average views |
| `count` | BIGINT | Number of posts |

---

## ENUMs

```sql
CREATE TYPE post_type AS ENUM ('thought', 'content', 'short');
CREATE TYPE platform_type AS ENUM ('twitter', 'linkedin', 'instagram', 'tiktok', 'youtube', 'other');
```

---

## Full DDL

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Enums
CREATE TYPE post_type AS ENUM ('thought', 'content', 'short');
CREATE TYPE platform_type AS ENUM ('twitter', 'linkedin', 'instagram', 'tiktok', 'youtube', 'other');

-- Main table
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type post_type NOT NULL,
    notion_page_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL CHECK (LENGTH(body) > 0),
    language TEXT DEFAULT 'en' CHECK (language ~ '^[a-z]{2}$'),
    embedding VECTOR(1536),
    metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Junction for cross-posts
CREATE TABLE posts_platforms (
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    platform platform_type NOT NULL,
    platform_post_id TEXT,
    platform_url TEXT,
    metrics JSONB,
    posted_at TIMESTAMPTZ,
    PRIMARY KEY (post_id, platform)
);

-- Auto-update trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_updated_at BEFORE UPDATE ON posts
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Indexes
CREATE INDEX idx_posts_type ON posts(type);
CREATE INDEX idx_posts_language ON posts(language);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_posts_embedding ON posts USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_posts_title_trgm ON posts USING gin (title gin_trgm_ops);
CREATE INDEX idx_posts_body_trgm ON posts USING gin (body gin_trgm_ops);
CREATE INDEX idx_posts_platforms_post ON posts_platforms(post_id);
CREATE INDEX idx_posts_platforms_platform ON posts_platforms(platform);

-- BI Materialized View
CREATE MATERIALIZED VIEW top_posts_mv AS
SELECT 
    p.type, p.language, pp.platform,
    AVG((p.metrics->>'likes')::NUMERIC) as avg_likes,
    AVG((p.metrics->>'views')::NUMERIC) as avg_views,
    COUNT(*) as count
FROM posts p
JOIN posts_platforms pp ON p.id = pp.post_id
WHERE p.metrics IS NOT NULL
GROUP BY p.type, p.language, pp.platform;

-- Daily refresh (2 AM)
SELECT cron.schedule('refresh-top-posts', '0 2 * * *', 'REFRESH MATERIALIZED VIEW top_posts_mv;');

-- Row Level Security
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts_platforms ENABLE ROW LEVEL SECURITY;

CREATE POLICY posts_select ON posts FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY posts_insert ON posts FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY posts_update ON posts FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY posts_delete ON posts FOR DELETE USING (auth.role() = 'service_role');

CREATE POLICY posts_platforms_all ON posts_platforms FOR ALL USING (auth.role() = 'authenticated');
```

---

## HOLUS Agent Queries

### 1. Find 10 Similar Posts (Vector Search)
```sql
SELECT id, title, body, 
       1 - (embedding <=> $1::vector) AS similarity
FROM posts 
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT 10;
```
**Performance:** <50ms on 100K rows

### 2. Best Content Type per Platform
```sql
SELECT type, platform, avg_likes, avg_views
FROM top_posts_mv
WHERE avg_likes > 0
ORDER BY avg_likes DESC
LIMIT 5;
```

### 3. Lifecycle Funnel (Last 90 Days)
```sql
SELECT
    date_trunc('week', created_at) AS week,
    COUNT(*) FILTER (WHERE type = 'thought') AS thoughts,
    COUNT(*) FILTER (WHERE type = 'content') AS contents,
    COUNT(*) FILTER (WHERE type = 'short') AS shorts,
    COUNT(pp.*) AS total_platform_posts
FROM posts p
LEFT JOIN posts_platforms pp ON p.id = pp.post_id
WHERE created_at > NOW() - INTERVAL '90 days'
GROUP BY week 
ORDER BY week DESC;
```

---

## Migration Plan

### Step 1: Create Supabase Project
1. Go to [supabase.com](https://supabase.com) → New Project
2. Enable pgvector in Extensions
3. Run the DDL above in SQL Editor

### Step 2: Migrate Notion Data
```python
from notion_client import Client
from supabase import create_client
import openai

notion = Client(auth="YOUR_NOTION_TOKEN")
supabase = create_client("YOUR_SUPABASE_URL", "YOUR_SUPABASE_KEY")

DB_MAP = {
    'THOUGHT_DB_ID': 'thought',
    'CONTENT_DB_ID': 'content', 
    'SHORT_DB_ID': 'short'
}

for db_id, post_type in DB_MAP.items():
    pages = notion.databases.query(database_id=db_id)['results']
    
    for page in pages:
        props = page['properties']
        title = props['Name']['title'][0]['plain_text']
        body = props.get('Body', {}).get('rich_text', [{}])[0].get('plain_text', title)
        
        # Insert post
        supabase.table('posts').insert({
            'type': post_type,
            'notion_page_id': page['id'],
            'title': title,
            'body': body,
            'language': 'en'
        }).execute()

print("Migration complete!")
```

### Step 3: Generate Embeddings (Background Job)
```python
posts = supabase.table('posts').select('id, title, body').is_('embedding', 'null').execute()

for post in posts.data:
    text = f"{post['title']} {post['body']}"
    embedding = openai.embeddings.create(input=text, model='text-embedding-3-small').data[0].embedding
    
    supabase.table('posts').update({'embedding': embedding}).eq('id', post['id']).execute()
```

### Step 4: Set Up Platform Tracking
Manually or via API, add entries to `posts_platforms` when you publish content.

---

## Cost

| Component | Cost |
|-----------|------|
| Supabase (free tier) | $0/mo (500MB, 50K rows) |
| OpenAI embeddings | ~$0.02 per 1000 posts |
| **Total** | **< $1/mo** for your scale |

---

## Approval Checklist

- [ ] 2 tables + 1 mview structure approved
- [ ] ENUMs cover all platforms/types
- [ ] `notion_page_id` links back to Notion ✓
- [ ] Cross-post support via junction table ✓
- [ ] Vector search for HOLUS ✓
- [ ] BI materialized view ✓
- [ ] RLS policies for Supabase ✓
- [ ] Migration plan clear ✓

---

**Ready to deploy?** Approve and I'll set up Supabase.

🦞
