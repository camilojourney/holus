# Spec 003: Content Pipeline

> **DEPRECATED (2026-02-28):** This spec is superseded by the silo integration specs:
> - [010-marketing-agent.md](./010-marketing-agent.md) — strategy and content decisions
> - [014-genpeli-integration.md](./014-genpeli-integration.md) — video editing via MCP
> - [015-pilaster-integration.md](./015-pilaster-integration.md) — image generation via MCP
> - [016-social-media-integration-v2.md](./016-social-media-integration-v2.md) — posting + analytics via MCP
>
> This spec was written before the silo architecture was formalized. It places image
> generation, video generation, and social media distribution directly inside Holus,
> violating the MCP boundary principle. Do not implement from this spec.

## Feature: Multi-stage content generation and distribution pipeline across 13 platforms

### Overview

The content pipeline automates the full lifecycle of content creation: strategy planning (Opus), text generation (Sonnet 4.5 with prompt caching), image generation (ComfyUI locally or Replicate for production), video generation (Kling AI + Creatomate), and distribution to 13 platforms via the Late API. A performance feedback loop collects engagement metrics and feeds them back into the strategy planner for continuous improvement. See [ADR-0002](../docs/decisions/0002-claude-first-intelligence.md) for the Claude-first intelligence rationale and [HOLUS-ARCHITECTURE-DECISIONS.md](../../HOLUS-ARCHITECTURE-DECISIONS.md) Section 2B for the full content architecture.

### User Stories

- As a founder, I want the content agent to generate 30+ pieces of content per month across multiple platforms so that my audience grows without manual effort.
- As a founder, I want content strategy decisions made by Opus so that topic selection is informed by engagement data, not guesswork.
- As a founder, I want a single API call to distribute content to 13 platforms so that I do not maintain 13 separate integrations.
- As a founder, I want a feedback loop that tracks what content performs best so that the agent improves over time.

---

### Core Specifications

**SPEC-001: Text Generation**

| Field | Value |
|-------|-------|
| Description | Generates articles, social posts, email sequences, and thread content using Sonnet 4.5 with aggressive prompt caching. System prompt (persona, style guide, SEO requirements, brand voice) is cached; only the topic and brief change per piece. |
| Trigger | Content calendar schedule via n8n, or manual trigger via webhook |
| Input | `ContentBrief` with topic, target platforms, SEO keywords, content type, brand voice |
| Output | `GeneratedContent` with text, metadata, SEO score, suggested media prompts |
| Validation | Content must meet minimum word count per type. SEO score from NeuronWriter must exceed threshold. |
| Auth Required | `ANTHROPIC_API_KEY`, `NEURONWRITER_API_KEY` (optional) |

```python
# src/holus/agents/content/text_gen.py

from pydantic import BaseModel
from datetime import datetime

class ContentBrief(BaseModel):
    brief_id: str
    topic: str
    content_type: str  # "article" | "social_post" | "thread" | "email" | "video_script"
    target_platforms: list[str]  # ["twitter", "linkedin", "blog", ...]
    seo_keywords: list[str]
    brand_voice: str  # "professional" | "casual" | "technical" | "storytelling"
    target_word_count: int | None = None  # None = platform-appropriate default
    reference_urls: list[str] = []
    custom_instructions: str = ""

class GeneratedContent(BaseModel):
    content_id: str
    brief_id: str
    generated_at: datetime
    content_type: str
    text: str
    word_count: int
    platform_variants: dict[str, str]  # Platform-specific text adaptations
    seo_score: float | None  # NeuronWriter score if applicable
    suggested_image_prompts: list[str]  # For SPEC-002 visual generation
    suggested_video_hooks: list[str]   # For SPEC-003 video generation
    hashtags: dict[str, list[str]]     # Per-platform hashtag suggestions
    model_used: str  # "claude-sonnet-4-6"
    cache_hit: bool  # Whether prompt caching was used
    token_usage: dict  # {"input": N, "output": N, "cache_read": N}

# Content type defaults
CONTENT_DEFAULTS = {
    "article": {"min_words": 1200, "max_words": 2500, "model": "claude-sonnet-4-6"},
    "social_post": {"min_words": 20, "max_words": 280, "model": "claude-sonnet-4-6"},
    "thread": {"min_words": 200, "max_words": 1500, "model": "claude-sonnet-4-6"},
    "email": {"min_words": 100, "max_words": 500, "model": "claude-sonnet-4-6"},
    "video_script": {"min_words": 50, "max_words": 300, "model": "claude-sonnet-4-6"},
}
```

Prompt caching architecture for text generation:

```python
# Stable prefix (cached -- ~3,000 tokens, changes monthly at most):
#   - Brand voice and persona definition
#   - Writing style guide (sentence structure, vocabulary level, tone)
#   - SEO requirements template
#   - Platform formatting rules (Twitter character limits, LinkedIn formatting, etc.)
#   - Example outputs per content type

# Dynamic suffix (not cached -- changes per content piece):
#   - Topic and brief
#   - SEO keywords for this piece
#   - Reference URLs / research context
#   - Custom instructions

# Cost estimate at scale:
# 50 articles/month * ~5K tokens each = ~250K output tokens
# With Sonnet 4.5 + caching: ~$15-25/month for text generation
```

Acceptance Criteria:
- [ ] Text generation uses Sonnet 4.5 with prompt caching for all content types
- [ ] System prompt prefix is cached (verify `cache_read_input_tokens > 0` in Langfuse traces)
- [ ] Generated content meets `min_words` threshold for each content type
- [ ] `platform_variants` contains platform-adapted text (e.g., Twitter-length for Twitter, full article for blog)
- [ ] `suggested_image_prompts` contains at least 1 prompt for visual content types
- [ ] Token usage is tracked per generation and logged to Langfuse
- [ ] NeuronWriter SEO scoring is optional (graceful degradation if API unavailable)

---

**SPEC-002: Image Generation**

| Field | Value |
|-------|-------|
| Description | Routes image generation between ComfyUI (local, for prototyping and custom workflows) and Replicate (Flux Schnell at $0.003/image, for production batches). The routing decision is made by the agent based on quality requirements and volume. |
| Trigger | Text generation produces `suggested_image_prompts`, or manual request via webhook |
| Input | Image prompt, quality requirements, batch size, target dimensions |
| Output | Generated image(s) with quality assessment scores |
| Validation | Quality assessment via Claude Vision must score >= 7/10 overall |
| Auth Required | `REPLICATE_API_TOKEN` (for Replicate), none for local ComfyUI |

```python
# src/holus/agents/content/visual_gen.py

from pydantic import BaseModel
from enum import Enum

class ImageProvider(str, Enum):
    COMFYUI = "comfyui"       # Local, free, custom workflows
    REPLICATE = "replicate"    # Cloud, $0.003/image, Flux Schnell

class ImageRequest(BaseModel):
    request_id: str
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    provider: ImageProvider | None = None  # None = auto-route
    batch_size: int = 1
    quality_threshold: float = 7.0  # Minimum quality score (1-10)
    style: str = "default"    # Workflow variant for ComfyUI

class ImageResult(BaseModel):
    request_id: str
    provider: ImageProvider
    image_urls: list[str]    # Local paths or remote URLs
    quality_scores: list[dict]  # Per-image quality assessment
    generation_time_seconds: float
    cost_usd: float          # $0 for ComfyUI, $0.003 * batch for Replicate

# Routing logic
class ImageRouter:
    """
    Route to ComfyUI for:
    - Single images needing custom style (specific ComfyUI workflow)
    - Prototyping / iteration on prompt
    - When Mac Mini GPU is available

    Route to Replicate for:
    - Batch generation (5+ images)
    - Standard Flux Schnell quality is sufficient
    - ComfyUI is busy or unavailable
    """
    def route(self, request: ImageRequest) -> ImageProvider:
        if request.provider:
            return request.provider
        if request.batch_size >= 5:
            return ImageProvider.REPLICATE
        if request.style != "default":
            return ImageProvider.COMFYUI
        return ImageProvider.REPLICATE  # Default to cloud
```

Quality assessment via Claude Vision:

```python
# Quality check runs on every generated image
# Uses Sonnet 4.5 (sufficient for vision assessment)
# Scores: technical_quality, prompt_adherence, aesthetic_quality, commercial_viability
# Pass threshold: overall >= 7
# Failed images are regenerated once with modified prompt; if still failing, flagged for human review
```

Acceptance Criteria:
- [ ] Auto-routing sends batches of 5+ to Replicate and custom-style requests to ComfyUI
- [ ] Replicate integration generates images via Flux Schnell at $0.003/image
- [ ] ComfyUI integration submits workflow JSON and retrieves generated images
- [ ] Every image is scored by Claude Vision quality assessment
- [ ] Images scoring below `quality_threshold` are regenerated once with modified prompt
- [ ] Images that fail twice are flagged for human review (not silently discarded)
- [ ] Cost tracking: every image generation is logged with provider and cost

---

**SPEC-003: Video Generation**

| Field | Value |
|-------|-------|
| Description | Generates short-form video content using Kling AI for AI-generated clips (5-20 seconds) and Creatomate for template-based assembly with ElevenLabs voiceover. Not full AI video -- practical production uses AI-generated B-roll with synthesized narration. |
| Trigger | Content brief specifies `content_type: "video"`, or text generation produces `suggested_video_hooks` |
| Input | Video brief (script, visual prompts, music/mood), duration target, platform aspect ratios |
| Output | Rendered video files per target platform (9:16 for TikTok/Reels, 16:9 for YouTube, 1:1 for feed) |
| Validation | Video must render without errors. Audio sync must be within 100ms. |
| Auth Required | `KLING_API_KEY`, `CREATOMATE_API_KEY`, `ELEVENLABS_API_KEY` |

```python
# src/holus/agents/content/video_gen.py

from pydantic import BaseModel
from enum import Enum

class VideoType(str, Enum):
    AI_CLIP = "ai_clip"           # Kling AI short-form (5-20s)
    TEMPLATE_VIDEO = "template"    # Creatomate template assembly
    VOICEOVER_SLIDES = "voiceover" # ElevenLabs narration + images

class VideoRequest(BaseModel):
    request_id: str
    video_type: VideoType
    script: str              # Narration text (for voiceover) or visual description
    visual_prompts: list[str]  # Scene descriptions for AI generation
    duration_seconds: int    # Target duration (5-60)
    aspect_ratios: list[str]  # ["9:16", "16:9", "1:1"]
    music_mood: str = "none"  # "upbeat" | "calm" | "dramatic" | "none"
    voice_id: str | None = None  # ElevenLabs voice ID

class VideoResult(BaseModel):
    request_id: str
    video_type: VideoType
    output_files: dict[str, str]  # {"9:16": "/path/to/vertical.mp4", "16:9": "/path/..."}
    duration_seconds: float
    generation_time_seconds: float
    cost_usd: float
    audio_sync_offset_ms: float  # Should be < 100ms

# Pipeline stages:
# 1. Script -> ElevenLabs TTS -> narration audio
# 2. Visual prompts -> Kling AI -> B-roll clips (5-20s each)
# 3. Images from SPEC-002 -> slide deck with transitions
# 4. Assembly: Creatomate combines narration + visuals + music + text overlays
# 5. Export per aspect ratio
```

Acceptance Criteria:
- [ ] AI clip generation via Kling AI produces 5-20 second clips from text prompts
- [ ] ElevenLabs TTS generates narration audio from script text
- [ ] Creatomate assembles video from components (narration + visuals + music + overlays)
- [ ] Output files are generated for each requested aspect ratio
- [ ] Audio-video sync offset is < 100ms
- [ ] Cost is tracked per video: Kling AI + ElevenLabs + Creatomate itemized
- [ ] Failed video renders are retried once. Second failure alerts human.

---

**SPEC-004: Distribution via Late API**

| Field | Value |
|-------|-------|
| Description | Single API endpoint for publishing content to 13 platforms simultaneously. Replaces 13 separate platform integrations. Handles scheduling, thread formatting, and platform-specific adaptations. |
| Trigger | Content generation complete and approved (automatic for low-risk, human review for brand-sensitive) |
| Input | `ContentPost` with text, media URLs, target platforms, optional schedule time |
| Output | Post IDs per platform, publishing status, analytics tracking IDs |
| Validation | Text must be within platform character limits. Media must be in supported formats. At least one platform must be specified. |
| Auth Required | `LATE_API_KEY` |

```python
# src/holus/integrations/late_api/client.py

from pydantic import BaseModel
import httpx

class ContentPost(BaseModel):
    text: str
    media_urls: list[str] = []
    platforms: list[str]
    # Supported: twitter, linkedin, instagram, facebook, tiktok, youtube,
    #            pinterest, threads, bluesky, mastodon, telegram, discord, reddit
    schedule_time: str | None = None  # ISO 8601, None = publish immediately
    thread: bool = False  # Twitter/Threads thread mode
    platform_overrides: dict[str, dict] = {}
    # e.g. {"twitter": {"text": "shorter version"}, "linkedin": {"text": "longer version"}}

class PublishResult(BaseModel):
    post_id: str  # Late API internal ID
    platform_results: dict[str, dict]
    # Per-platform: {"status": "published", "platform_post_id": "...", "url": "..."}
    scheduled: bool
    published_at: str | None
    failed_platforms: list[str]
    error_details: dict[str, str]  # Platform -> error message for failures

class LateAPIClient:
    BASE_URL = "https://api.late.so/v1"

    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def publish(self, post: ContentPost) -> PublishResult:
        response = await self.client.post("/posts", json=post.model_dump())
        response.raise_for_status()
        return PublishResult.model_validate(response.json())

    async def get_analytics(self, post_id: str) -> dict:
        response = await self.client.get(f"/posts/{post_id}/analytics")
        response.raise_for_status()
        return response.json()

    async def get_scheduled(self) -> list[dict]:
        response = await self.client.get("/posts/scheduled")
        response.raise_for_status()
        return response.json()
```

Platform character limits enforced before publishing:

```python
PLATFORM_LIMITS = {
    "twitter": {"text": 280, "thread_segment": 280},
    "linkedin": {"text": 3000},
    "instagram": {"text": 2200},
    "facebook": {"text": 63206},
    "tiktok": {"text": 2200},
    "youtube": {"description": 5000, "title": 100},
    "pinterest": {"text": 500},
    "threads": {"text": 500},
    "bluesky": {"text": 300},
    "mastodon": {"text": 500},
    "telegram": {"text": 4096},
    "discord": {"text": 2000},
    "reddit": {"title": 300, "text": 40000},
}
```

Acceptance Criteria:
- [ ] Single `publish()` call sends content to all specified platforms
- [ ] Platform character limits are enforced before API call (not relying on Late API to reject)
- [ ] `platform_overrides` allows per-platform text customization
- [ ] Failed platforms are reported in `failed_platforms` with error details; successful platforms are unaffected
- [ ] Scheduled posts work with ISO 8601 timestamps
- [ ] Thread mode splits long content into thread segments for Twitter/Threads
- [ ] Analytics retrieval works for published posts

---

**SPEC-005: Performance Feedback Loop**

| Field | Value |
|-------|-------|
| Description | Collects engagement metrics from all platforms, analyzes trends weekly (Opus), and feeds insights back into content strategy and generation prompts. Monthly DSPy optimization on content generation prompts. |
| Trigger | Daily: pull analytics. Weekly: Opus trend analysis. Monthly: DSPy optimization. |
| Input | Per-post analytics (impressions, engagement rate, clicks, follower changes), posting metadata (topic, platform, time, format) |
| Output | Updated Mem0 memories (what topics/platforms/formats work), monthly optimized prompts |
| Validation | Analytics data must have valid post IDs. Trends require minimum 10 data points. |
| Auth Required | `LATE_API_KEY` (analytics), Mem0 access |

```python
# src/holus/agents/content/feedback.py

from pydantic import BaseModel
from datetime import datetime

class ContentMetrics(BaseModel):
    post_id: str
    content_id: str
    platform: str
    published_at: datetime
    topic: str
    content_type: str
    metrics: dict
    # Standard metrics per platform:
    # impressions: int
    # engagement_rate: float  (likes + comments + shares) / impressions
    # clicks: int
    # click_through_rate: float
    # time_on_page: float (for articles)
    # follower_delta: int (followers gained/lost from this post)
    # shares: int
    # saves: int (Instagram/Pinterest)

class PerformanceInsight(BaseModel):
    insight_id: str
    generated_at: datetime
    insight_type: str
    # Types: "topic_performance", "platform_preference", "timing_pattern",
    #        "format_effectiveness", "engagement_trend"
    description: str
    # e.g. "Posts about AI trading published on Tuesday mornings get 2.3x engagement on LinkedIn"
    confidence: float
    sample_size: int
    recommendation: str
    # e.g. "Increase AI trading content on LinkedIn. Schedule for Tuesday 8-9 AM EST."
```

```yaml
# config/content_agent.yaml -- feedback section
feedback_loop:
  collection_schedule: "daily"    # Pull analytics daily via n8n
  analysis_schedule: "weekly"     # Opus analyzes trends every Sunday
  optimization_schedule: "monthly" # DSPy optimizes content prompts monthly

  metrics_tracked:
    - engagement_rate
    - click_through_rate
    - time_on_page
    - follower_growth
    - seo_ranking_position
    - shares
    - saves

  memory_storage:
    agent_id: "content-agent"
    memory_types:
      - topic_performance      # Which topics resonate
      - platform_preferences   # What works on each platform
      - timing_patterns        # Best posting times
      - format_effectiveness   # Article vs thread vs carousel
      - audience_insights      # What the audience responds to

  dspy_optimization:
    min_labeled_examples: 30   # Minimum before running DSPy
    budget_per_run_usd: 5.0    # ~$2-5 per DSPy MIPROv2 run
    target_metric: "engagement_rate"
```

Acceptance Criteria:
- [ ] Daily analytics collection pulls metrics for all published content from Late API
- [ ] Weekly Opus analysis produces `PerformanceInsight` objects stored in Mem0
- [ ] Insights include `sample_size` (minimum 10) and `confidence` scores
- [ ] Insights are fed back into text generation as context (included in the dynamic prompt suffix)
- [ ] Monthly DSPy optimization runs when 30+ labeled examples exist
- [ ] DSPy optimization targets `engagement_rate` as the primary metric
- [ ] Before/after engagement rates are logged for each optimization cycle
- [ ] Content strategy planner (Opus, monthly) reads all insights to set the content calendar

---

### Data Structures

Content lifecycle event (published to `holus.content.performance`):

```json
{
  "source_agent": "content-agent",
  "event_type": "content_published",
  "timestamp": "2026-03-15T10:00:00Z",
  "payload": {
    "content_id": "C-20260315-001",
    "content_type": "article",
    "topic": "How AI Agents Are Changing Solo Founder Productivity",
    "platforms": ["linkedin", "twitter", "blog"],
    "word_count": 1850,
    "seo_score": 82,
    "seo_keywords": ["AI agents", "solo founder", "productivity"],
    "media_attached": true,
    "image_provider": "replicate",
    "scheduled": false
  },
  "correlation_id": "brief-20260314-005"
}
```

Engagement update event:

```json
{
  "source_agent": "content-agent",
  "event_type": "engagement_update",
  "timestamp": "2026-03-16T21:00:00Z",
  "payload": {
    "content_id": "C-20260315-001",
    "platform": "linkedin",
    "metrics": {
      "impressions": 4520,
      "engagement_rate": 0.067,
      "clicks": 189,
      "shares": 34,
      "comments": 12,
      "follower_delta": 8
    },
    "hours_since_publish": 35
  }
}
```

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/agents/content/__init__.py` | New | Content agent module init |
| `src/holus/agents/content/agent.py` | New | ContentAgent(BaseAgent) with LangGraph state machine |
| `src/holus/agents/content/strategy.py` | New | Content strategy planner (Opus, monthly) |
| `src/holus/agents/content/text_gen.py` | New | Text generation with prompt caching |
| `src/holus/agents/content/visual_gen.py` | New | Image generation routing (ComfyUI / Replicate) |
| `src/holus/agents/content/video_gen.py` | New | Video generation pipeline |
| `src/holus/agents/content/distribution.py` | New | Late API publishing orchestration |
| `src/holus/agents/content/feedback.py` | New | Performance feedback loop |
| `src/holus/integrations/late_api/__init__.py` | New | Late API module init |
| `src/holus/integrations/late_api/client.py` | New | Late API client for publishing and analytics |
| `src/holus/integrations/comfyui/__init__.py` | New | ComfyUI module init |
| `src/holus/integrations/comfyui/client.py` | New | ComfyUI REST + WebSocket client |
| `src/holus/integrations/comfyui/models.py` | New | Workflow JSON schemas |
| `src/holus/integrations/replicate/__init__.py` | New | Replicate module init |
| `src/holus/integrations/replicate/client.py` | New | Replicate API client (Flux Schnell) |
| `src/holus/integrations/elevenlabs/__init__.py` | New | ElevenLabs module init |
| `src/holus/integrations/elevenlabs/client.py` | New | ElevenLabs TTS client |
| `src/holus/integrations/kling/__init__.py` | New | Kling AI module init |
| `src/holus/integrations/kling/client.py` | New | Kling AI video generation client |
| `src/holus/integrations/creatomate/__init__.py` | New | Creatomate module init |
| `src/holus/integrations/creatomate/client.py` | New | Creatomate video assembly client |
| `config/content_agent.yaml` | New | Content agent configuration (strategy, feedback, thresholds) |
| `tests/unit/agents/test_content.py` | New | Text generation, routing, feedback tests |
| `tests/unit/integrations/test_late_api.py` | New | Late API client tests |
| `tests/integration/test_content_pipeline.py` | New | End-to-end content generation + distribution |

---

### Edge Cases & Error Handling

**EDGE-001: Late API rate limit or outage**
- Scenario: Late API returns 429 (rate limit) or 5xx (outage) during batch publishing
- Expected behavior: Retry with exponential backoff (3 attempts, 10s/30s/60s). If all retries fail, save content to a local queue (`data/distribution_queue/`) for retry via n8n schedule.
- Error message: `WARN: Late API unavailable for platforms {platforms}. Content queued for retry. Queue depth: {N}`
- Recovery: n8n retry workflow checks queue every 15 minutes and re-attempts publishing

**EDGE-002: Generated content fails SEO scoring threshold**
- Scenario: NeuronWriter returns SEO score below 60 for an article
- Expected behavior: Regenerate with additional SEO context injected into the prompt. If second attempt also fails, publish without SEO optimization and flag for human review.
- Error message: `WARN: Content {content_id} SEO score {score} below threshold (60). Regenerating with SEO focus.`
- Recovery: Automatic regeneration. If still failing, human reviews and adjusts SEO keywords.

**EDGE-003: Image quality assessment fails twice**
- Scenario: Claude Vision scores generated image below 7/10, regeneration also fails
- Expected behavior: Flag for human review. Publish text content without image rather than delay.
- Error message: `WARN: Image for {content_id} failed quality check twice (scores: {s1}, {s2}). Publishing text-only. Image flagged for human review.`
- Recovery: Human selects or creates a replacement image. Content is updated on platforms that support edits.

**EDGE-004: ComfyUI unavailable when image generation is routed locally**
- Scenario: ComfyUI process crashed or Mac Mini GPU is occupied
- Expected behavior: Automatic fallback to Replicate. Log the routing change.
- Error message: `INFO: ComfyUI unavailable. Falling back to Replicate for image generation.`
- Recovery: Automatic. ComfyUI availability is checked at the start of each generation request.

**EDGE-005: Platform-specific publish failure (partial success)**
- Scenario: Content publishes to LinkedIn and Twitter but fails on Instagram (media format issue)
- Expected behavior: Successful platforms are unaffected. Failed platform is logged with error detail. Retry is attempted for the failed platform only.
- Error message: `WARN: Publish partial failure. Success: [linkedin, twitter]. Failed: [instagram: "Image aspect ratio not supported"]. Retrying failed platforms.`
- Recovery: Content agent attempts to reformat media for the failed platform. If still failing, alerts human.

**EDGE-006: ElevenLabs or Kling AI API unavailable during video generation**
- Scenario: Third-party video/audio API is down
- Expected behavior: Video generation is skipped for this content piece. Text and image content is still published. Video is queued for retry.
- Error message: `WARN: {service} unavailable. Skipping video generation for {content_id}. Text/image content published.`
- Recovery: n8n retry workflow attempts video generation when service returns.

**EDGE-007: DSPy optimization degrades content quality**
- Scenario: Monthly DSPy optimization produces prompts that generate lower-quality content
- Expected behavior: A/B test: run 5 pieces with new prompts, 5 with old prompts. If new prompts underperform, roll back automatically.
- Error message: `INFO: DSPy optimization A/B test: new prompts scored {new_avg} vs old {old_avg}. Rolling back.`
- Recovery: Automatic rollback to previous prompts. Failed optimization is logged for analysis.

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Article generation (1500 words) | < 45s | Langfuse trace: Claude API call + post-processing |
| Social post generation | < 10s | Langfuse trace |
| Image generation (Replicate) | < 30s | Replicate API round-trip |
| Image generation (ComfyUI) | < 60s | ComfyUI queue + render time |
| Image quality assessment | < 15s | Claude Vision API call |
| Video generation (full pipeline) | < 5 min | End-to-end: TTS + clips + assembly |
| Distribution to 13 platforms | < 30s | Late API round-trip |
| Daily analytics collection | < 2 min | Late API analytics calls for all posts |
| Content generation cost | < $25/month | Langfuse cost dashboard (50 articles/month) |
| Image generation cost | < $15/month | Replicate billing (5,000 images at $0.003) |

---

### Security Considerations

- Content never contains financial advice (hard rule in system prompt). Content about markets is educational/informational only.
- Brand voice and persona are defined in the cached system prompt, not user-modifiable per request.
- Late API key provides publish access to all 13 platforms. If compromised, revoke immediately.
- ElevenLabs voice cloning is used only with licensed voices. No unauthorized voice synthesis.
- All generated content is logged in Langfuse for audit trail (what was generated, when, for which platform).
- Content mentioning specific people or companies requires human approval (defined in `config/guardrails.yaml`).

---

### Out of Scope

- Podcast production (audio-only long-form content)
- Live streaming or real-time content
- User-generated content moderation
- Content calendar UI (content strategy lives in Mem0, triggered by n8n)
- Influencer outreach or paid promotion
- A/B testing of headlines at scale (manual A/B via DSPy is in scope)
- Full-length video production (>60 seconds AI-generated)

---

### Related Specs

- [001-core-infrastructure.md](./001-core-infrastructure.md) -- provides Redis (event bus), Claude client (text generation), Langfuse (cost tracking)

---

**Last Updated:** 2026-02-24
**Status:** Not Started
**Owner:** Camilo Martinez
