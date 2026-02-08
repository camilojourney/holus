# SPEC-000: HOLUS Architecture Overview

> This document MUST be read before any other spec. It provides the big picture.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            main.py (Supervisor)                          │
│                                                                          │
│  Responsibilities:                                                       │
│  • Spawn domain orchestrators as subprocesses                           │
│  • Monitor health via heartbeats                                         │
│  • Auto-restart crashed domains                                          │
│  • Graceful shutdown handling                                            │
└─────────────────────────────────────────────────────────────────────────┘
                    │                    │                    │
                    ▼                    ▼                    ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  content-strategy/   │  │    job-tracker/      │  │      trading/        │
│    orchestrator      │  │     orchestrator     │  │     orchestrator     │
│                      │  │                      │  │                      │
│  ┌────────────────┐  │  │  ┌────────────────┐  │  │  ┌────────────────┐  │
│  │ Video Publisher│  │  │  │  Job Hunter    │  │  │  │ Market Monitor │  │
│  │  └─ YouTube    │  │  │  │                │  │  │  │                │  │
│  │  └─ TikTok     │  │  │  └────────────────┘  │  │  └────────────────┘  │
│  │  └─ Shorts     │  │  │                      │  │                      │
│  └────────────────┘  │  │  ┌────────────────┐  │  │  ┌────────────────┐  │
│  ┌────────────────┐  │  │  │ Resume Tailor  │  │  │  │ Alert Manager  │  │
│  │ Text Publisher │  │  │  │                │  │  │  │                │  │
│  │  └─ Twitter    │  │  │  └────────────────┘  │  │  └────────────────┘  │
│  │  └─ LinkedIn   │  │  │                      │  │                      │
│  └────────────────┘  │  └──────────────────────┘  └──────────────────────┘
│  ┌────────────────┐  │
│  │Repurpose Engine│  │
│  └────────────────┘  │
└──────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              shared/                                     │
│                                                                          │
│  base_agent.py    │  memory.py    │  llm.py    │  notifier.py           │
│  orchestrator.py  │  utils.py     │  types.py  │  config.py             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Language | Python 3.11+ | LangChain ecosystem |
| Agent Framework | LangChain | Mature, well-documented |
| LLM Providers | OpenAI, Anthropic, Ollama | Flexibility |
| Vector Memory | ChromaDB | Local-first, simple |
| Scheduling | APScheduler | Built into orchestrators |
| Process Management | subprocess + multiprocessing | No K8s needed |
| IPC | multiprocessing.Queue | Simple, no external deps |
| Config | YAML | Human readable |
| Logging | Loguru | Better than stdlib |
| Testing | Pytest | Standard |

## Shared Data Models

```python
# shared/types.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime

class ContentType(Enum):
    VIDEO = "video"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"

class FunnelStage(Enum):
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    CONVERSION = "conversion"

class Platform(Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    # Add more as needed

@dataclass
class ContentItem:
    """Universal content representation."""
    id: str
    type: ContentType
    title: str
    body: str
    media_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    tags: list[str] = None
    funnel_stage: FunnelStage = FunnelStage.AWARENESS
    target_platforms: list[Platform] = None
    metadata: dict = None
    created_at: datetime = None

@dataclass
class PublishResult:
    """Result of publishing to a platform."""
    success: bool
    platform: Platform
    content_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    published_at: datetime = None

@dataclass
class AgentMessage:
    """Message for inter-agent communication."""
    from_agent: str
    to_agent: str
    action: str
    payload: dict
    timestamp: datetime = None
```

## Directory Structure (Target State)

```
holus/
├── main.py                     # Supervisor: spawns orchestrators
├── requirements.txt
├── pyproject.toml
├── docker-compose.yml          # Optional
├── README.md
│
├── shared/                     # Framework code
│   ├── __init__.py
│   ├── base_agent.py           # BaseAgent class
│   ├── orchestrator.py         # DomainOrchestrator base
│   ├── memory.py               # ChromaDB wrapper
│   ├── llm.py                  # LLM provider abstraction
│   ├── notifier.py             # Telegram notifications
│   ├── types.py                # Shared data models
│   ├── config.py               # Config loader
│   └── utils.py                # Helpers
│
├── agents/
│   ├── content-strategy/       # Domain 1
│   │   ├── __init__.py
│   │   ├── config.yaml
│   │   ├── orchestrator.py     # ContentOrchestrator
│   │   ├── publishers/
│   │   │   ├── video_publisher.py
│   │   │   └── text_publisher.py
│   │   ├── adapters/
│   │   │   ├── base_adapter.py
│   │   │   ├── youtube_adapter.py
│   │   │   └── twitter_adapter.py
│   │   ├── repurposing_engine.py
│   │   └── tests/
│   │
│   ├── job-tracker/            # Domain 2
│   │   ├── __init__.py
│   │   ├── config.yaml
│   │   ├── orchestrator.py
│   │   ├── job_hunter.py
│   │   └── tests/
│   │
│   └── trading/                # Domain 3 (future)
│       └── ...
│
├── scripts/
│   ├── migrate.py              # Migration helper
│   └── test_all.py
│
└── logs/                       # Runtime logs
```

## Implementation Order

```
Week 1: Foundation
├── Day 1-2: SPEC-001 (Restructure)
│   └── Migration script, shared/ setup, domain stubs
├── Day 3-4: SPEC-004 (Subprocess Isolation)
│   └── Supervisor, heartbeats, auto-restart
└── Day 5: Integration testing

Week 2: Content Pipeline (SPEC-002 + SPEC-003 merged)
├── Day 1-2: YouTube adapter (auth, publish, analytics)
├── Day 3: Video publisher (uses adapter)
├── Day 4: Twitter adapter + Text publisher
└── Day 5: Repurposing engine (basic clip extraction)

Week 3: Polish
├── Testing, docs, bug fixes
└── First real content published
```

## Scope for MVP (Minimum Viable Product)

**IN SCOPE:**
- Repository restructure with domain grouping
- Subprocess isolation with auto-restart
- YouTube adapter (publish + analytics)
- Twitter adapter (publish threads)
- Video publisher
- Text publisher
- Basic repurposing (transcript → thread)

**OUT OF SCOPE (Phase 2):**
- TikTok, LinkedIn, Discord adapters
- Audio publisher
- Community publisher
- Goal/Audience planner (use manual tagging)
- Advanced repurposing (video clipping)
- Multi-brand support

## Success Criteria

1. **Restructure works**: All imports resolve, tests pass
2. **Isolation works**: Kill one domain, others continue
3. **YouTube publishes**: Upload a video via adapter
4. **Twitter publishes**: Post a thread via adapter
5. **End-to-end**: YouTube video → extracted transcript → Twitter thread

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| YouTube API complexity | Use google-api-python-client, follow quickstart |
| Twitter API changes | Use tweepy, have fallback to browser automation |
| Subprocess zombies | Proper signal handling, process groups |
| Import cycles after restructure | Careful module design, test immediately |
| Scope creep | Stick to MVP, defer everything else |
