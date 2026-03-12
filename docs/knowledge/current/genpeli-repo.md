# genpeli Repository

**Repository:** `genpeli`  
**Location:** `/Users/mini/.openclaw/workspace/github/genpeli`  
**Purpose:** Automated video processing pipeline for creating social media reels with smart cuts, word-by-word captions, audio normalization, and social delivery  
**Tech Stack:** FastAPI, PostgreSQL, Redis, arq (async queue), whisper.cpp, ffmpeg, pysubs2, fsspec, Cloudflare R2

---

## Architecture Overview

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────┐
│                    GENPELI PIPELINE                      │
├─────────────────────────────────────────────────────────┤
│  POST /v1/process (1-2 videos + instruction)            │
│         ↓                                               │
│  [arq] 1. ingest_video  — save to /tmp/genpeli/{id}/   │
│         ↓                                               │
│  [arq] 2. transcribe    — whisper.cpp :5001             │
│         ↓               → word timestamps               │
│  [arq] 3. cut_silences  — ffmpeg silencedetect -35dB   │
│         ↓               → concat manifest               │
│  [arq] 4. merge_videos  — ffmpeg concat (if 2 vids)    │
│         ↓                                               │
│  [arq] 5. burn_captions — pysubs2 → .ass → ffmpeg      │
│         ↓                                               │
│  [arq] 6. normalize     — ffmpeg loudnorm -14 LUFS      │
│         ↓                                               │
│  [arq] 7. package       — make preview available        │
│         ↓                                               │
│  GET /v1/jobs/{id}/preview  ← YOU REVIEW HERE          │
│         ↓                                               │
│  POST /v1/jobs/{id}/approve                             │
│         ↓                                               │
│  [arq] 8. deliver       — R2 upload → social push       │
└─────────────────────────────────────────────────────────┘
```

### Service Dependencies

| Service | Port | Role |
|---------|------|------|
| whisper.cpp | 5001 | Local transcription inference server |
| Redis | 6379 | arq broker and result backend |
| PostgreSQL | 5432 | Job records, segments, performance data |

---

## Directory Structure

```
genpeli/
├── backend/
│   ├── src/
│   │   └── genpeli_api/
│   │       ├── api/
│   │       │   └── v1/
│   │       │       ├── ingest.py      # POST /v1/process
│   │       │       ├── review.py      # GET /v1/jobs/{id}, preview
│   │       │       └── publish.py     # POST /v1/jobs/{id}/approve
│   │       ├── core/
│   │       │   ├── config.py          # Settings from env vars
│   │       │   ├── db/
│   │       │   │   ├── models.py      # SQLAlchemy ORM
│   │       │   │   ├── database.py    # Async engine
│   │       │   │   └── session.py     # Session factory
│   │       │   └── services/
│   │       │       ├── task_queue.py  # arq client wrapper
│   │       │       ├── asset_manager.py # File tracking
│   │       │       └── vector_store.py # Embeddings (future)
│   │       ├── pipeline/
│   │       │   ├── tasks.py           # arq task definitions
│   │       │   └── prompts.py         # AI instruction templates
│   │       ├── storage/
│   │       │   └── backend.py         # fsspec abstraction (local/R2)
│   │       ├── review/
│   │       │   ├── feedback_logger.py # Review decisions
│   │       │   └── ui_adapter.py      # Frontend data adapter
│   │       ├── schemas/
│   │       │   └── jobs.py            # Pydantic models
│   │       ├── worker.py              # arq WorkerSettings
│   │       └── main.py                # FastAPI entry point
│   ├── alembic/                       # DB migrations
│   └── tests/
├── ml/
│   ├── audio/                         # Audio analysis utilities
│   └── video/                         # Video analysis utilities
├── frontend/
│   └── src/                           # React approval UI (stub)
├── infra/
│   └── docker/                        # Service Dockerfiles
├── specs/                             # Numbered feature specs
├── docs/
│   ├── decisions/                     # ADRs
│   └── playbooks/                     # Operational guides
├── docker-compose.yml
└── justfile
```

---

## Component Details

### 1. Pipeline Tasks (arq)

**File:** `backend/src/genpeli_api/pipeline/tasks.py`

All tasks are async functions decorated with `@task` (arq). Each task:
1. Receives `job_id` + parameters
2. Updates job status in PostgreSQL
3. Performs processing (I/O, ffmpeg, whisper)
4. Creates Asset records for output files
5. Enqueues next task in the pipeline

**Task Chain:**

```python
ingest_video → transcribe → cut_silences → merge_videos → 
burn_captions → normalize → package → [MANUAL REVIEW] → deliver
```

**Key Tasks:**

- **ingest_video:** Download/copy videos to `/tmp/genpeli/{job_id}/`
- **transcribe:** Call whisper.cpp at `:5001`, get word timestamps → ScriptSegment records
- **cut_silences:** ffmpeg `silencedetect` filter (-35dB threshold) → concat manifest
- **merge_videos:** If 2 videos, ffmpeg concat demuxer
- **burn_captions:** pysubs2 generates `.ass` subtitle file → ffmpeg overlay with custom styling
- **normalize:** ffmpeg `loudnorm` filter (-14 LUFS, -1 dB peak)
- **package:** Move `video_final.mp4` to preview location
- **deliver:** Upload to R2, call social-media API, cleanup temp files

**Worker Config:**

```python
class WorkerSettings:
    functions = [ingest_video, transcribe, cut_silences, 
                 merge_videos, burn_captions, normalize, 
                 package, deliver]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    max_jobs = 2   # Prevents overloading Mac Mini
```

Run: `python -m arq genpeli_api.worker.WorkerSettings`

---

### 2. Database Schema

**Engine:** PostgreSQL via SQLAlchemy async

**Tables (3):**

| Table | Purpose |
|-------|---------|
| `assets_dim` | Tracks each file artifact in the pipeline |
| `content_performance_fact` | Job records and social post outcomes |
| `script_segments_dim` | Word-level transcript data from whisper |

**ORM Models:**

```python
class AssetType(str, enum.Enum):
    video = "video"
    image = "image"
    audio = "audio"
    voiceover = "voiceover"
    text = "text"
    multi = "multi"

class PublishStatus(str, enum.Enum):
    draft = "draft"
    generating = "generating"
    ready_for_review = "ready_for_review"
    rejected = "rejected"
    approved = "approved"
    scheduled = "scheduled"
    published = "published"
    error = "error"
    archived = "archived"

class Asset(Base):
    __tablename__ = "assets_dim"
    asset_sk = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String, unique=True, nullable=False, index=True)
    asset_url = Column(String, nullable=False)
    asset_type = Column(SQLAlchemyEnum(AssetType), nullable=False)
    creation_ts_utc = Column(DateTime(timezone=True), server_default=func.now())
    updated_ts_utc = Column(DateTime(timezone=True), onupdate=func.now())
    
    content = relationship("ContentPerformance", back_populates="final_asset")

class ContentPerformance(Base):
    __tablename__ = "content_performance_fact"
    content_sk = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(String, unique=True, nullable=False, index=True)
    final_asset_sk = Column(Integer, ForeignKey("assets_dim.asset_sk"))
    publish_status = Column(SQLAlchemyEnum(PublishStatus), 
                           default=PublishStatus.draft)
    
    final_asset = relationship("Asset", back_populates="content")
    script_segments = relationship("ScriptSegment", back_populates="content")

class ScriptSegment(Base):
    __tablename__ = "script_segments_dim"
    segment_sk = Column(Integer, primary_key=True, autoincrement=True)
    content_sk = Column(Integer, ForeignKey("content_performance_fact.content_sk"))
    segment_order = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    start_time_ms = Column(Integer)
    end_time_ms = Column(Integer)
    
    content = relationship("ContentPerformance", back_populates="script_segments")
```

---

### 3. Storage Backend

**File:** `backend/src/genpeli_api/storage/backend.py`

Uses `fsspec` for abstraction — single API for local and R2 storage

**Modes:**
- `STORAGE_BACKEND=local` — All files on disk at `/Users/mini/genpeli-assets/`
- `STORAGE_BACKEND=r2` — Cloudflare R2 bucket (boto3 S3-compatible)

**Strategy:**
- All processing happens locally in `/tmp/genpeli/{job_id}/`
- Only final approved reel (`video_final.mp4`) is uploaded to R2
- Rejected jobs: all tmp files deleted immediately

**fsspec Usage:**

```python
from fsspec import open as fsopen

# Works for both local and R2
with fsopen(path, "wb") as f:
    f.write(video_data)
```

---

### 4. ML Modules

**Directory:** `ml/`

These are utility libraries, not standalone services. Pipeline tasks import them directly:

```python
from ml.audio.silence import detect_silences
from ml.video.analysis import extract_keyframes
```

No separate process or port required.

**Key Modules:**
- `ml/audio/` — Silence detection, audio analysis
- `ml/video/` — Keyframe extraction, shot detection

---

### 5. API Surface

**Base URL:** `http://localhost:8100` (default)

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/process | Submit 1-2 videos + instruction |
| GET | /v1/jobs/{id} | Job status + progress percentage |
| GET | /v1/jobs/{id}/preview | Stream preview video (range requests) |
| POST | /v1/jobs/{id}/approve | Approve → queue deliver task |
| POST | /v1/jobs/{id}/reject | Reject → delete all tmp files |

**Request Example:**

```bash
POST /v1/process
Content-Type: multipart/form-data

{
  "video_files": [<file1>, <file2>],
  "instruction": "Cut silences, add animated captions"
}
```

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Job queued successfully"
}
```

---

### 6. Review Workflow

**Human-in-the-Loop:**

1. Submit job via POST `/v1/process`
2. Poll GET `/v1/jobs/{id}` until status = `ready_for_review`
3. Stream preview via GET `/v1/jobs/{id}/preview`
4. Decision:
   - **Approve:** POST `/v1/jobs/{id}/approve` → triggers `deliver` task
   - **Reject:** POST `/v1/jobs/{id}/reject` → deletes all files, marks archived

**Status Flow:**

```
draft → generating → ready_for_review → 
  [approved → published] OR [rejected → archived]
```

---

### 7. Configuration

**File:** `backend/src/genpeli_api/core/config.py`

Loads from environment variables:

```python
REDIS_URL = "redis://localhost:6379"
POSTGRES_URL = "postgresql+asyncpg://..."
WHISPER_ENDPOINT = "http://localhost:5001/inference"
STORAGE_BACKEND = "local"  # or "r2"
R2_BUCKET = "genpeli-assets"
R2_ENDPOINT = "https://..."
SOCIAL_MEDIA_API_URL = "http://localhost:8000"
```

---

### 8. arq Queue

**Why arq over Celery?** See `docs/decisions/0001-arq-over-celery.md`

Key reasons:
- Asyncio-native (no Celery's thread/greenlet overhead)
- Uses same Redis instance (no separate broker)
- Simpler configuration
- Better for I/O-bound tasks (video processing)

**Worker Management:**

```bash
# Start worker
python -m arq genpeli_api.worker.WorkerSettings

# Monitor queue
redis-cli LLEN arq:queue:genpeli

# Check running jobs
redis-cli KEYS arq:job:*
```

---

## Development Commands

```bash
# Start all services (Docker Compose)
docker-compose up -d

# Start FastAPI dev server
cd backend
uvicorn genpeli_api.main:app --reload --port 8100

# Start arq worker
cd backend
python -m arq genpeli_api.worker.WorkerSettings

# Run migrations
cd backend
alembic upgrade head

# Run tests
cd backend
pytest tests/
```

---

## Integration Points

**For Holus:** Genpeli is the video processing pipeline. Holus can:
1. Submit videos via POST `/v1/process`
2. Monitor job status via GET `/v1/jobs/{id}`
3. Present preview to user for review
4. Trigger approval/rejection based on user input

**Key Integration Endpoints:**
- POST `/v1/process` — Submit videos for processing
- GET `/v1/jobs/{id}` — Poll for status (includes progress %)
- GET `/v1/jobs/{id}/preview` — Stream preview video
- POST `/v1/jobs/{id}/approve` — Approve and trigger social push
- POST `/v1/jobs/{id}/reject` — Reject and cleanup

**Authentication:** API key header (configured in Holus environment)

**Asset Location:** `/Users/mini/genpeli-assets/jobs/{job_id}/`

---

## File Naming Convention

```
/tmp/genpeli/{job_id}/
├── video_raw_1.mp4           # Original video 1
├── video_raw_2.mp4           # Original video 2 (if exists)
├── audio_extracted.wav       # Audio extracted for transcription
├── transcript.json           # whisper.cpp output
├── silence_manifest.txt      # ffmpeg concat file
├── video_cut.mp4             # After silence removal
├── video_merged.mp4          # After merging (if 2 videos)
├── captions.ass              # ASS subtitle file
├── video_captioned.mp4       # After caption burn
└── video_final.mp4           # After normalization (FINAL)
```

---

## Caption Styling

**File:** Generated via pysubs2

**Style:**
- Font: Arial Bold
- Size: 52px (responsive to video height)
- Position: Bottom center
- Background: Semi-transparent black box
- Color: White with yellow highlight on current word
- Animation: Word-by-word reveal based on whisper timestamps

---

## Performance Considerations

**Processing Time:**
- 1-minute video: ~2-3 minutes total processing
- Bottlenecks:
  1. Transcription (whisper.cpp): ~30s per minute of speech
  2. Caption burn (ffmpeg): ~45s per minute of video
  3. Normalization (loudnorm): ~30s per minute of video

**Optimizations:**
- `max_jobs = 2` in worker (prevents overload)
- Local processing, R2 only for finals
- Temp files cleaned up immediately on rejection

---

**Last Updated:** 2026-02-27  
**Documented By:** Fruco (Holus Repo Research Task)
