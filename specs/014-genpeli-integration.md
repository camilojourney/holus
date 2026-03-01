# Spec 014: Genpeli Integration

**Status:** partial
**Phase:** Phase 1
**Author:** Camilo Martinez
**Created:** 2026-02-27
**Updated:** 2026-02-27

## Problem

The marketing agent can create text and image content, but has no way to produce video content -- the highest-engagement format on social platforms. Raw footage exists (screen recordings, talking head clips, B-roll) but requires manual editing: cutting silences, adding captions, normalizing audio. Without Genpeli integration, every video requires the founder to manually process it, making autonomous video content production impossible.

## Goals

- Marketing agent submits raw footage and receives polished, social-ready reels without manual editing
- Video processing is accessible via MCP tools following the federated silo pattern (no wrapper code in Holus)
- Generated reels are previewed before publishing so quality is verified
- Human approval gate ensures brand quality in Phase 1
- Video performance data feeds back into strategy so future video decisions improve

## Non-Goals

- AI-generated video from text (Kling AI) -- requires separate integration, future spec
- Template-based video assembly (Creatomate) -- different pipeline, future spec
- Custom caption styling -- basic styling only in Phase 1, Genpeli config extension needed
- Background music mixing -- Phase 2+, requires audio mixing in Genpeli
- Multi-video advanced editing -- only 2-video concat supported by Genpeli currently

## Solution

Genpeli runs as an independent silo with its own REST API (5 endpoints at `http://localhost:8100`) and its own MCP server (built in the genpeli repo). Holus connects to it via MCP configuration -- no wrapper code lives in Holus.

The integration follows this workflow:
1. Marketing agent decides to create video content during its reason stage
2. Agent calls `process_video` MCP tool with source footage URLs and processing instructions
3. Agent polls `check_video_status` until the job reaches `ready_for_review`
4. Agent retrieves a preview URL via `get_video_preview`
5. Video is queued for human review (Phase 1) or auto-approved (Phase 2+)
6. On approval, `approve_video` triggers Genpeli's delivery pipeline (R2 upload, social distribution)
7. On rejection, `reject_video` cleans up temp files and logs the reason for future learning

Security: `GENPELI_API_KEY` is stored in `.env` only, never in code. Preview URLs are temporary (expire after 24 hours). Final videos are stored in R2 with access control.

## Implementation Notes

### SPEC-001: Genpeli MCP Server

| Field | Value |
|-------|-------|
| Description | MCP server in the genpeli repo that exposes the video processing pipeline as tools. Holus connects to it -- no wrapper code in Holus. |
| Trigger | Marketing agent connects to the MCP server at startup |
| Input | Tool calls from the marketing agent (submit video, check status, approve/reject) |
| Output | Tool results (job IDs, status updates, preview URLs, final video URLs) |
| Validation | All inputs validated by the MCP server before passing to Genpeli pipeline |
| Auth Required | `GENPELI_API_KEY` (server-side, in genpeli repo) |

**NOTE:** The MCP server code lives in the **genpeli repo**, not in Holus.
Genpeli already has a REST API (5 endpoints at `http://localhost:8100`).
The MCP server wraps these endpoints as tools. This is work for the genpeli repo.

Expected MCP tools (to be built in genpeli repo):

| Tool | Description |
|------|-------------|
| `process_video` | Submit video(s) for processing (cut silences, add captions) |
| `check_video_status` | Check job status and progress percentage |
| `get_video_preview` | Get preview URL for completed job |
| `approve_video` | Approve for delivery (upload to R2, push to social media) |
| `reject_video` | Reject and cleanup temp files |

MCP server configuration for Holus (in `.claude/settings.json`):

```json
{
  "mcpServers": {
    "genpeli": {
      "command": "python",
      "args": ["-m", "genpeli.mcp_server"],
      "cwd": "/Users/mini/.openclaw/workspace/github/genpeli",
      "env": {
        "GENPELI_API_KEY": "${GENPELI_API_KEY}"
      }
    }
  }
}
```

### SPEC-002: Marketing Agent Integration

| Field | Value |
|-------|-------|
| Description | Marketing agent discovers and uses Genpeli tools through the MCP server for video content production |
| Trigger | Marketing agent reason stage decides to create video content |
| Input | Content decision with `content_type: "video"` |
| Output | Processed video ready for social media distribution |
| Validation | Video decisions must include visual prompts or source footage reference |
| Auth Required | MCP server handles auth |

Video content workflow in marketing agent:

```python
# src/holus/agents/marketing/video_workflow.py

async def create_video_content(self, decision: ContentDecision) -> dict:
    """Create video content using Genpeli MCP server."""

    # Step 1: Get source footage (from assets or record new)
    source_videos = await self.get_source_footage(decision)

    # Step 2: Submit to Genpeli via MCP
    job_id = await self.call_mcp(
        "genpeli",
        "process_video",
        video_urls=",".join(source_videos),
        instruction=decision.get("video_instruction", "Cut silences, add animated captions"),
    )

    # Step 3: Poll for completion
    max_wait = 300  # 5 minutes
    start_time = time.time()
    while time.time() - start_time < max_wait:
        status = await self.call_mcp("genpeli", "check_video_status", job_id=job_id)
        status_data = json.loads(status)

        if status_data["status"] == "ready_for_review":
            break
        elif status_data["status"] == "error":
            raise ValueError(f"Genpeli processing failed: {status_data.get('error')}")

        await asyncio.sleep(10)

    # Step 4: Get preview URL
    preview_url = await self.call_mcp("genpeli", "get_video_preview", job_id=job_id)

    # Step 5: Human review (Phase 1) or auto-approve (Phase 2+)
    await self.queue_for_review({
        "piece_id": f"video-{job_id}",
        "job_id": job_id,
        "preview_url": preview_url,
        "decision": decision,
    })

    return {
        "job_id": job_id,
        "preview_url": preview_url,
        "status": "pending_review",
    }
```

### SPEC-003: Content Types Supported

| Content Type | Available Now | Needs Tooling |
|--------------|---------------|---------------|
| **Screen recordings** (product demos) | YES | None (capture on Mac Mini) |
| **Talking head footage** (founder explaining features) | YES | None (record on iPhone/Mac) |
| **B-roll clips** (UI interactions, workflows) | YES | None (capture from products) |
| **AI-generated clips** (synthetic scenes) | NO | Kling AI integration (future) |
| **Template-based assembly** (slides + voiceover) | NO | Creatomate integration (future) |
| **Multi-video merges** (intro + demo + CTA) | YES | Genpeli supports 2-video concat |
| **Custom caption styles** | NO | Genpeli config extension needed |
| **Background music** | NO | Audio mixing in Genpeli |

### SPEC-004: Video Content Queue

| Field | Value |
|-------|-------|
| Description | Videos require human review before approval, similar to text content queue |
| Trigger | Video processing completes (status: ready_for_review) |
| Input | Processed video with preview URL |
| Output | Video saved to review queue with approval/rejection interface |
| Validation | Each video has job_id, preview_url, and decision context |
| Auth Required | No (local file operations) |

```python
# src/holus/agents/marketing/video_queue.py

from __future__ import annotations

import yaml
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel


class QueuedVideo(BaseModel):
    piece_id: str
    job_id: str
    preview_url: str
    product: str
    topic: str
    reasoning: str
    generated_at: datetime
    status: str = "pending_review"  # pending_review | approved | rejected


VIDEO_QUEUE_DIR = Path("data/video-queue")


def enqueue_video(video: QueuedVideo) -> Path:
    VIDEO_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    path = VIDEO_QUEUE_DIR / f"{video.piece_id}.yaml"
    path.write_text(yaml.dump(video.model_dump(), default_flow_style=False))
    return path


def list_pending_videos() -> list[QueuedVideo]:
    if not VIDEO_QUEUE_DIR.exists():
        return []
    pending = []
    for f in sorted(VIDEO_QUEUE_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        if data.get("status") == "pending_review":
            pending.append(QueuedVideo.model_validate(data))
    return pending


async def approve_video(piece_id: str) -> str:
    """Approve video and trigger Genpeli delivery."""
    path = VIDEO_QUEUE_DIR / f"{piece_id}.yaml"
    data = yaml.safe_load(path.read_text())

    # Call Genpeli via MCP to approve
    result = await call_mcp("genpeli", "approve_video", job_id=data["job_id"])

    # Update queue status
    data["status"] = "approved"
    path.write_text(yaml.dump(data, default_flow_style=False))

    return result


async def reject_video(piece_id: str, reason: str = "") -> str:
    """Reject video and cleanup Genpeli temp files."""
    path = VIDEO_QUEUE_DIR / f"{piece_id}.yaml"
    data = yaml.safe_load(path.read_text())

    # Call Genpeli via MCP to reject
    result = await call_mcp("genpeli", "reject_video", job_id=data["job_id"], reason=reason)

    # Update queue status
    data["status"] = "rejected"
    data["rejection_reason"] = reason
    path.write_text(yaml.dump(data, default_flow_style=False))

    return result
```

CLI commands:

```just
# Review pending videos
review-videos:
    python -m holus.agents.marketing.review_videos

# Approve a video
approve-video piece_id:
    python -m holus.agents.marketing.review_videos --approve {{piece_id}}

# Reject a video
reject-video piece_id reason="":
    python -m holus.agents.marketing.review_videos --reject {{piece_id}} --reason "{{reason}}"
```

### Data Structures

Genpeli job status (what the MCP server returns):

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready_for_review",
  "progress_percent": 100,
  "created_at": "2026-02-27T10:00:00Z",
  "preview_url": "http://localhost:8100/v1/jobs/550e8400.../preview",
  "pipeline_stages": {
    "ingest": "completed",
    "transcribe": "completed",
    "cut_silences": "completed",
    "burn_captions": "completed",
    "normalize": "completed",
    "package": "completed"
  }
}
```

### File Locations

**In Holus repo:**

| File | Change Type | Description |
|------|-------------|-------------|
| `.claude/settings.json` | Modified | Add genpeli MCP server config |
| `src/holus/agents/marketing/video_workflow.py` | New | Video creation workflow |
| `src/holus/agents/marketing/video_queue.py` | New | Video review queue |
| `src/holus/agents/marketing/review_videos.py` | New | CLI for reviewing videos |
| `data/video-queue/` | New (gitignored) | Video queue directory |

**In genpeli repo (to be built):**

| File | Change Type | Description |
|------|-------------|-------------|
| `genpeli/mcp_server.py` | New | MCP server wrapping the existing REST API |
| `tests/test_mcp_server.py` | New | MCP server tests |

### Dependencies

- Depends on: [Spec 010](./010-marketing-agent.md) — the marketing agent that calls Genpeli tools
- Depended on by: [Spec 016](./016-social-media-integration-v2.md) — social media distribution of videos
- Related: [Spec 015](./015-pilaster-integration.md) — image generation silo, parallel pattern

## Edge Cases & Failure Modes

**EDGE-001: Genpeli API unavailable**
- Scenario: Genpeli service is down or unreachable
- Expected behavior: Video creation skipped for this cycle. Text/image content still created. Retry queued for next cycle.
- Recovery: Automatic retry when service returns.

**EDGE-002: Video processing timeout**
- Scenario: Video processing takes longer than 5 minutes
- Expected behavior: Agent logs timeout and moves on. Video can be checked manually via `just check-genpeli-jobs`.
- Recovery: Manual review of stuck jobs.

**EDGE-003: Video quality poor (after review)**
- Scenario: Human rejects video due to quality issues
- Expected behavior: Rejection logged with reason. Agent learns to avoid similar source footage.
- Recovery: Human provides feedback for future video selection.

**EDGE-004: No source footage available for topic**
- Scenario: Agent decides to create video but has no relevant footage
- Expected behavior: Video creation skipped. Agent logs "no footage available for {topic}". Text content created instead.
- Recovery: Human records footage and places in asset library.

## Observability

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Video submission | < 10s | MCP call latency |
| Status check | < 2s | MCP call latency |
| Genpeli processing (1-min video) | < 3 min | Genpeli internal timing |
| Preview retrieval | < 5s | HTTP GET latency |
| Approval/rejection | < 5s | Genpeli API call |

## Acceptance Criteria

- [ ] Genpeli MCP server (in genpeli repo) starts and responds to `tools/list`
- [ ] `process_video` tool submits videos to Genpeli pipeline
- [ ] `check_video_status` tool returns job status with progress percentage
- [ ] `get_video_preview` tool returns preview URL when ready
- [ ] `approve_video` tool triggers delivery pipeline
- [ ] `reject_video` tool cleans up temp files
- [ ] Holus can connect to genpeli MCP via `.claude/settings.json` config
- [ ] All tools have clear descriptions and typed arguments
- [ ] Marketing agent discovers Genpeli tools via MCP
- [ ] Agent can submit video processing jobs
- [ ] Agent polls job status until ready_for_review
- [ ] Agent retrieves preview URL for review
- [ ] Agent queues video for human approval in Phase 1
- [ ] Failed processing logged with error details
- [ ] Processing timeouts handled gracefully
- [ ] Videos saved to `data/video-queue/` as YAML files
- [ ] `just review-videos` lists pending videos with preview URLs
- [ ] `just approve-video <id>` approves and triggers Genpeli delivery
- [ ] `just reject-video <id>` rejects and cleans up temp files
- [ ] Approved videos are delivered to R2 and social platforms
