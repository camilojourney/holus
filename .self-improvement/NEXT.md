# NEXT.md — Holus Task Priority Queue

Last updated: 2026-03-01

## Priority Guide
- **P0** — Blocking. Nothing else works until this is fixed.
- **P1** — Critical path. Required for first end-to-end marketing cycle.
- **P2** — High value. Major feature or integration.
- **P3** — Medium value. Enhancement or optimization.
- **P4** — Nice to have. Polish or future prep.

---

## Spec Status (as of 2026-03-01)

| Spec | Name | Status |
|------|------|--------|
| 001 | Core Infrastructure | Partial (config, kill switch, events, health: done; docker compose, event bus integration: not tested) |
| 010 | Marketing Agent | Implemented (ReAct loop, content queue, review CLI, 97 tests) |
| 012 | Knowledge & Learning | Partial (trajectory logger: done; knowledge files: done; knowledge_gaps.py: not built; weekly learning loop: not built) |
| 013 | Scheduling & Runtime | Partial (launchd plists exist; not tested/activated) |
| 014 | Genpeli Integration | Not Started (genpeli has no MCP server) |
| 015 | Pilaster Integration | Not Started (pilaster MCP exists in sibling repo; not connected) |
| 016 | Social Media Integration V2 | Not Started (social-media MCP exists in sibling repo with 9 tools; not connected; missing get_analytics + get_top_posts tools) |

---

## Queue

### P1 — First End-to-End Marketing Cycle

- [x] [BUILD] Implement `knowledge_gaps.py` — Spec 012 SPEC-004. Agent needs to flag missing info. Create `src/holus/memory/knowledge_gaps.py` with `file_knowledge_gap()` and `list_open_gaps()`. Add tests.
- [x] [BUILD] Add metadata headers to all knowledge files — Spec 012 requires each file in `.self-improvement/knowledge/current/` to have `Last updated`, `Updated by`, `Confidence`, `Affects`, `Research cadence` headers. Audit all 6 files.
- [x] [INTEGRATE] Add social-media MCP config — Add social-media MCP server entry to Holus MCP config so the marketing agent can call `post_text`, `schedule_post`, etc. Config points to `/Users/mini/.openclaw/workspace/github/social-media-automatization`.
- [x] [INTEGRATE] Add pilaster MCP config — Add pilaster MCP server entry to Holus MCP config. Config points to `/Users/mini/.openclaw/workspace/github/pilaster`.
- [x] [REVIEW] Verify marketing agent runs end-to-end in fallback mode — Run `uv run python -m holus run marketing --once` without API keys. Agent should use fallback decisions and template content. Fix any runtime errors.

### P2 — Silo Integration (Close the Loop)

- [x] [INTEGRATE] Add `get_analytics` tool to social-media MCP — Spec 016 SPEC-004. The social-media-automatization repo needs this tool added to its MCP server so the marketing agent's observe stage can read real analytics.
- [x] [INTEGRATE] Add `get_top_posts` tool to social-media MCP — Same as above. Needed for the learning loop to know what content performs best.
- [x] [BUILD] Implement video workflow (`video_workflow.py`) — Spec 014 SPEC-002. Marketing agent integration for Genpeli video processing. Create `src/holus/agents/marketing/video_workflow.py`.
- [x] [BUILD] Implement image workflow (`image_workflow.py`) — Spec 015 SPEC-002. Marketing agent integration for Pilaster image generation. Create `src/holus/agents/marketing/image_workflow.py`.
- [x] [BUILD] Implement video queue (`video_queue.py`) — Spec 014 SPEC-004. Review queue for videos, similar to content queue. Create `src/holus/agents/marketing/video_queue.py` and `review_videos.py`.

### P3 — Growth Engine (Strategy Quality)

- [x] [BUILD] Voice profile capture — Growth engine vision requires content that sounds like Camilo. Analyze existing LinkedIn/Twitter posts to extract voice characteristics. Write results to `.self-improvement/knowledge/current/voice-profile.md`.
- [x] [BUILD] Structured content framework library — Growth engine vision defines 7 frameworks (Breakdown, Contrarian, Before/After, Thread, BTS, Engagement Bait, Data Drop) + hook templates. Structure these into a machine-readable format in `.self-improvement/knowledge/current/content-frameworks.md`.
- [ ] [BUILD] Weekly learning loop — Spec 012 SPEC-003. Manager agent reads trajectory + analytics weekly, uses Opus to extract patterns, updates MEMORY.md. Wire up `just improve` to run this.
- [ ] [BUILD] Performance patterns knowledge file — Auto-generated from analytics data. Create `.self-improvement/knowledge/current/performance-patterns.md` seeded with the correct metadata header. Updated by the weekly learning loop.

### P4 — Polish

- [ ] [BUILD] Knowledge archive rotation — Spec 012 requires old knowledge versions to be moved to `archive/` when updated. Add utility function.
- [ ] [BUILD] Knowledge README.md index — Create `.self-improvement/knowledge/README.md` indexing all current knowledge files, their topics, and confidence levels.
- [ ] [REVIEW] Update specs/README.md status — Spec 010 is listed as "Not Started" but is Implemented. Spec 012 status should be "Partial". Sync all spec statuses.
- [ ] [REVIEW] Verify launchd scheduling works — Spec 013. Test `just schedule` and `just schedule-status`. Verify marketing agent cron runs every 30 min.
