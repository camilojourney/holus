# SPEC-002: Content Strategy Domain Implementation

## Overview
Implement the content strategy domain with Format Publishers, Platform Adapters, Goal/Audience Planner, and Repurposing Engine.

## Architecture
```
agents/content-strategy/
├── orchestrator/
│   ├── __init__.py
│   ├── goal_audience_planner.py    # Tags content by funnel/audience
│   └── brand_router.py             # Multi-brand dispatch
│
├── core/
│   ├── __init__.py
│   ├── idea_research_agent.py      # Ideation + trend research
│   └── repurposing_engine.py       # 1→N content transformation
│
├── publishers/
│   ├── __init__.py
│   ├── video_publisher.py          # YouTube, TikTok, Reels, Shorts
│   ├── text_publisher.py           # X, LinkedIn, Threads, Newsletter
│   ├── audio_publisher.py          # Podcasts, Spotify
│   └── community_publisher.py      # Discord, Reddit, Forums
│
├── adapters/
│   ├── __init__.py
│   ├── base_adapter.py             # Adapter interface
│   ├── youtube_adapter.py
│   ├── tiktok_adapter.py
│   ├── twitter_adapter.py
│   ├── linkedin_adapter.py
│   ├── discord_adapter.py
│   └── newsletter_adapter.py
│
├── analytics_loop.py               # Feedback to optimize
├── config.yaml                     # Domain configuration
├── content_orchestrator.py         # Domain entry point
└── tests/
    ├── test_publishers.py
    ├── test_adapters.py
    └── test_repurposing.py
```

## Component Specifications

### 1. Goal & Audience Planner
**Purpose:** Tag content with funnel stage and audience segment before creation.

**Inputs:**
- Raw content idea
- Historical performance data
- Brand guidelines

**Outputs:**
- Funnel stage: `awareness | consideration | conversion`
- Audience segment: `professionals | consumers | developers | ...`
- Recommended formats: `[video, thread, newsletter]`
- Priority score: `1-10`

**Implementation:**
```python
class GoalAudiencePlanner(BaseAgent):
    name = "goal_audience_planner"
    
    def get_tools(self):
        @tool
        def tag_content(idea: str, brand: str = "default") -> dict:
            """Analyze idea and return funnel/audience tags."""
            ...
        
        @tool
        def get_audience_insights(segment: str) -> str:
            """Get insights about an audience segment."""
            ...
```

### 2. Repurposing Engine
**Purpose:** Transform one piece of content into multiple platform-optimized versions.

**Capabilities:**
- Video clipping (FFmpeg)
- Transcript extraction (Whisper)
- Hook generation (LLM)
- Format adaptation (aspect ratio, duration)
- Hashtag/caption optimization per platform

**Implementation:**
```python
class RepurposingEngine(BaseAgent):
    name = "repurposing_engine"
    
    def get_tools(self):
        @tool
        def extract_clips(video_path: str, count: int = 5) -> list[str]:
            """Extract viral-worthy clips from long-form video."""
            # Uses FFmpeg + scene detection
            ...
        
        @tool
        def transcribe(media_path: str) -> str:
            """Transcribe audio/video to text."""
            # Uses Whisper
            ...
        
        @tool
        def generate_hooks(content: str, platform: str) -> list[str]:
            """Generate attention-grabbing hooks for platform."""
            ...
        
        @tool
        def adapt_format(content_path: str, target_platform: str) -> str:
            """Adapt content to platform specs (aspect ratio, duration)."""
            ...
```

### 3. Format Publishers
**Purpose:** Execute content publishing to specific format categories.

**Video Publisher:**
- Manages: YouTube (long), TikTok, Reels, Shorts
- Uses adapters for platform-specific logic
- Handles thumbnails, titles, descriptions, tags

**Text Publisher:**
- Manages: X/Twitter, LinkedIn, Threads, Newsletters
- Thread creation, carousel generation
- Platform tone adaptation

**Audio Publisher:**
- Manages: Podcasts, Spotify
- RSS feed management
- Show notes generation

**Community Publisher:**
- Manages: Discord, Reddit, Forums
- Community-appropriate formatting
- Engagement tracking

### 4. Platform Adapters
**Purpose:** Encapsulate platform-specific API logic.

**Base Adapter Interface:**
```python
class BaseAdapter(ABC):
    platform: str
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with platform API."""
        ...
    
    @abstractmethod
    def publish(self, content: Content) -> PublishResult:
        """Publish content to platform."""
        ...
    
    @abstractmethod
    def get_analytics(self, content_id: str) -> Analytics:
        """Fetch performance metrics."""
        ...
    
    @abstractmethod
    def adapt_content(self, content: Content) -> Content:
        """Adapt content to platform requirements."""
        ...
```

**Platform-Specific Adaptations:**
| Platform | Aspect Ratio | Max Duration | Hashtags | Special |
|----------|--------------|--------------|----------|---------|
| YouTube | 16:9 | Unlimited | Tags | Chapters, Cards |
| TikTok | 9:16 | 10 min | 3-5 trending | Sounds, Effects |
| Reels | 9:16 | 90 sec | 3-5 | Music, Collab |
| Shorts | 9:16 | 60 sec | Tags | End screen |
| Twitter | Any | 2:20 | 1-2 | Threads, Polls |
| LinkedIn | 1:1 or 16:9 | 10 min | 3-5 | Documents |

### 5. Analytics Loop
**Purpose:** Collect performance data and feed back to improve future content.

**Metrics Collected:**
- Views, impressions, reach
- Engagement (likes, comments, shares)
- Watch time, retention curves
- Click-through rates
- Conversion events

**Feedback Actions:**
- Update audience segment preferences
- Adjust hook effectiveness scores
- Recommend content types
- Identify best posting times

## Configuration Schema
```yaml
# agents/content-strategy/config.yaml
domain: content-strategy
enabled: true

brands:
  default:
    name: "Juan's Personal Brand"
    voice: "casual, technical, helpful"
    audiences: [developers, tech-curious]
    
platforms:
  youtube:
    enabled: true
    channel_id: "..."
    default_tags: [AI, tech, tutorials]
  tiktok:
    enabled: true
    # ...
    
repurposing:
  auto_clip: true
  min_clip_duration: 15
  max_clips_per_video: 5
  
analytics:
  poll_interval_hours: 6
  retention_days: 90
```

## Workflow Example
```
1. Idea Input: "How AI agents work in 2026"
   │
   ▼
2. Goal/Audience Planner:
   - Funnel: awareness
   - Audience: developers, tech-curious
   - Formats: [youtube_long, tiktok_clips, twitter_thread]
   │
   ▼
3. Idea Research Agent:
   - Trends: "AI agents", "LangChain", "autonomous AI"
   - Competitors: 5 similar videos analyzed
   - Unique angle: "Personal workforce on Mac Mini"
   │
   ▼
4. Content Creation (manual or assisted):
   - 10-minute YouTube script
   - Thumbnail concept
   │
   ▼
5. Video Publisher → YouTube Adapter:
   - Upload video
   - Set metadata, chapters, end screen
   │
   ▼
6. Repurposing Engine:
   - Extract 5 clips (15-60 sec each)
   - Generate hooks for each
   - Transcribe for threads
   │
   ▼
7. Video Publisher → TikTok/Reels/Shorts Adapters:
   - Adapt aspect ratio (9:16)
   - Add trending sounds/hashtags
   - Schedule posts
   │
   ▼
8. Text Publisher → Twitter Adapter:
   - Create thread from transcript
   - Add key insights as tweets
   │
   ▼
9. Analytics Loop (ongoing):
   - Track performance
   - Feed back to Planner
```

## Acceptance Criteria
- [ ] All publishers can post to their platforms
- [ ] Adapters handle platform-specific formatting
- [ ] Repurposing engine extracts clips from video
- [ ] Goal planner tags content correctly
- [ ] Analytics loop collects metrics
- [ ] Config-driven platform enable/disable
- [ ] Tests cover critical paths

## Dependencies
- FFmpeg (video processing)
- Whisper (transcription)
- Platform APIs (YouTube, TikTok, Twitter, etc.)
- LangChain (agent framework)
- ChromaDB (analytics storage)

## Timeline
- Orchestrator + Config: 2 hours
- Publishers (stubs): 4 hours
- Adapters (YouTube, Twitter first): 6 hours
- Repurposing Engine: 4 hours
- Analytics Loop: 2 hours
- **Total: 18 hours (3-4 days)**
