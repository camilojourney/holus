# Platform Capabilities Matrix — For Content Factory Routing

## Publishing via social-media-automatization MCP

### MCP Tools Available
1. `publish` — content, platforms[], format, media_url, media_type, first_comment
2. `get_status` — check publish job status
3. `list_platforms` — get capability matrix + health snapshot
4. `schedule` — same as publish + scheduled_at (ISO 8601)

### Platform Requirements

| Platform | Text-only? | Media Required? | Max Text | Video? | Stories? |
|----------|-----------|-----------------|----------|--------|----------|
| Instagram | NO | YES (feed) | 2,200 | Yes (Reels) | Yes |
| Facebook | Yes | No | 63,206 | Yes | Yes |
| Threads | Yes | No | 500 | Yes (5min) | No |
| LinkedIn | Yes | No | 3,000 | Yes (30min) | No |
| Twitter/X | Yes | No | 280 | Yes (140s) | No |

### Content Type → Platform Mapping

| Content Type | Best Platforms | Media Needed | Notes |
|-------------|---------------|-------------|-------|
| Carousel (PDF) | LinkedIn, Instagram | PDF/images | LinkedIn: document upload. Instagram: image carousel |
| Text post | LinkedIn, Twitter, Threads, Facebook | None | Adapt length per platform |
| Video (Reel) | Instagram, Threads, LinkedIn, Facebook | Video | Route through genpeli first |
| Diagram | LinkedIn, Twitter | Image (rendered Mermaid) | Render to PNG before posting |
| Long-form | LinkedIn | None | LinkedIn supports 3000 chars |

### Rate Limits (conservative daily)
- Instagram: 25/day
- Facebook: 25/day
- Threads: 50/day (highest)
- LinkedIn: 20/day
- Twitter/X: 17/day (Free tier)

### Validation Before Publish
- Call `POST /api/v1/publish/validate` to dry-run
- Checks: token status, rate limits, media requirements, content length
- Instagram feed without media = BLOCKED
- Text exceeding platform limit = BLOCKED

## Pilaster MCP Integration

### Key Tools for Content Factory
- `list_characters(tags, search)` — browse brand characters
- `render_character(character_id, scene_prompt, backend)` — generate images
- `get_render_status(generation_record_id)` — poll until ready
- `search_snapshots(query, outcome)` — find past successful renders

### Backends Available
- `dalle3` — fast, recognizable (1 credit)
- `comfyui` — pixel-perfect with LoRA (1 credit)
- `playwright` — CSS/HTML templates (0 credits, instant)
- `fal` — Flux/SDXL Turbo (1 credit)

## Genpeli REST API Integration

### Endpoints (NOT MCP — HTTP REST at port 8100)
- `POST /v1/process` — submit video (files[] + instruction)
- `GET /v1/jobs/{job_id}` — check status
- `GET /v1/jobs/{job_id}/preview` — download preview
- `POST /v1/jobs/{job_id}/approve` — approve for delivery
- `POST /v1/jobs/{job_id}/reject` — reject + cleanup

### Pipeline: video → transcribe → cut → merge → caption → normalize → preview → approve → deliver
### Approval gate is a HARD INVARIANT — no auto-approve bypass
### Round-trip: 2-5 min per video. Max 2 concurrent jobs.
