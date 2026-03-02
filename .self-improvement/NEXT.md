# NEXT.md — Holus Task Priority Queue

Last updated: 2026-03-01

## Priority Guide
- **P0** — Blocking. Nothing else works until this is fixed.
- **P1** — Critical path. Required for first authority-building content cycle.
- **P2** — High value. Enables automated research and content repurposing.
- **P3** — Medium value. Agent code updates for the new strategy.
- **P4** — Nice to have. Polish or future prep.

---

## Spec Status (as of 2026-03-01)

| Spec | Name | Status |
|------|------|--------|
| 001 | Core Infrastructure | Partial (config, kill switch, events, health: done; docker compose, event bus integration: not tested) |
| 009 | Autonomous Build System | Partial (builder agent, run lock, trajectory logging: done; launchd scheduler: not tested) |
| 010 | Marketing Agent | Implemented (ReAct loop, content queue, review CLI, 247 tests) — NEEDS UPDATE for authority engine |
| 012 | Knowledge & Learning | Implemented (knowledge base, trajectory, learning loop, knowledge gaps, archive rotation, README index: all done) |
| 013 | Scheduling & Runtime | Partial (launchd plists exist; not tested/activated) |
| 014 | Genpeli Integration | Partial (video_workflow.py + video_queue.py built; genpeli MCP server: not built) |
| 015 | Pilaster Integration | Partial (pilaster MCP connected + image_workflow.py built; end-to-end not tested) |
| 016 | Social Media Integration V2 | Partial (MCP connected + get_analytics/get_top_posts tools added; end-to-end not tested) |

---

## Sprint 1 Complete (2026-03-01)

All 18 tasks from the infrastructure sprint are done:
- Core infrastructure, marketing agent, knowledge learning: IMPLEMENTED
- Silo integrations (video/image workflows, MCP configs): BUILT
- Knowledge base (voice profile, content frameworks, 9 files): SEEDED
- 247 tests passing, health checks working, launchd plists validated
- See `.self-improvement/reports/builder/` for cycle details

---

## Sprint 2: Authority Engine Build

Strategic shift: from "promote products" to "build authority for AI consulting pipeline."
Source document: `tasks/next.md`

### P0 — Identity Foundation

- [x] [BUILD] Draft `config/brand.yaml` scaffold — Create the file structure with all required sections (story, positioning, offer, target client, products-as-proof, voice, anti-patterns, competitor accounts). Fill in what's known from tasks/next.md. Mark sections needing Camilo's input with `# TODO: Camilo input needed`. This unblocks downstream tasks.
- [x] [BUILD] Reframe `config/products.yaml` — Shift product descriptions from "features to promote" to "proof points for consulting authority." Each product becomes evidence of builder expertise, not the primary pitch.

### P1 — Strategy Knowledge Rewrite

- [x] [BUILD] Rewrite `content-marketing-strategy.md` — Replace generic research questions with authority-building strategy: LinkedIn-primary, 5 content pillars (builder stories, AI implementation frameworks, industry analysis, results/proof, contrarian takes), 5x/week LinkedIn cadence, consulting lead generation focus.
- [x] [BUILD] Rewrite `audience-profiles.md` — Add primary audience: consulting prospects (CTOs, VPs Eng, founders at 50-500 employee companies considering AI transformation, NYC market). Keep product audiences as secondary (brand builders, not pipeline).
- [ ] [BUILD] Rewrite `platforms.md` — LinkedIn-first playbook: hook patterns, post formats (text/carousel/document/video), engagement tactics (comments, DMs, community), algorithm signals (dwell time, comments > likes, shares = gold). Other platforms = repurpose, don't create separate.
- [ ] [BUILD] Update `growth-engine-vision.md` — Align with consulting goal: authority-building engine, not product promotion engine. Update target results to consulting metrics (inbound DMs, discovery calls, not just views).

### P2 — Niche Research Capability

- [ ] [BUILD] Seed `viral-frameworks.md` — New knowledge file. Research LinkedIn AI consulting/builder space. Document 10+ examples of viral posts: hook, structure, proof element, CTA, why it worked. Machine-readable format like content-frameworks.md.
- [ ] [BUILD] Design niche research step — Write spec addendum for Spec 010: new observe sub-step that uses web search to find trending AI consulting content on LinkedIn. Define search queries, extraction patterns, output format. Write to `specs/010-marketing-agent.md` as SPEC-005.
- [ ] [BUILD] Define search queries for niche research — Create `.self-improvement/knowledge/current/niche-research-queries.md` with curated search queries for monitoring the AI consulting/builder niche. Categories: competitor posts, trending topics, viral patterns, industry news.

### P3 — Agent Code Updates (Spec 010 v2)

- [ ] [BUILD] Write spec 017 — Authority Engine Agent Update. Covers: brand.yaml loading in observe, niche research step, authority framing in reason, content repurposing in act (LinkedIn → Twitter → Instagram → Threads → Facebook). This is the agent code spec for Sprint 2.
- [ ] [BUILD] Implement brand.yaml config loader — Add `config/brand.yaml` reading to `src/holus/core/config.py`. Pydantic model for brand identity. Loaded into every marketing agent cycle.
- [ ] [BUILD] Update marketing agent prompts — Replace product-promotion framing with authority-building framing in `src/holus/agents/marketing/prompts.py`. Reference brand.yaml, use consulting language, builder mindset.
- [ ] [BUILD] Implement content repurposing logic — New module `src/holus/agents/marketing/repurpose.py`. Takes LinkedIn post → adapts for Twitter (condensed), Instagram (visual), Threads (conversational), Facebook (bilingual ES if applicable). Platform-specific formatting.
- [ ] [BUILD] Implement niche research step in observe stage — Add web search capability to marketing agent's observe phase. Agent searches for trending content, extracts patterns, stores in knowledge base. Uses Claude tool_use with web_search.

### P4 — Polish & Infrastructure

- [ ] [BUILD] Fix `just check` PATH issue — ruff needs `uv run` prefix in justfile. Minor but annoying.
- [ ] [REVIEW] End-to-end authority engine test — Run full marketing agent cycle with brand.yaml → research → reason → create content → review queue. Verify content sounds like Camilo, uses authority framing, targets consulting prospects.
- [ ] [BUILD] Update `.self-improvement/MEMORY.md` — Refresh system memory with Sprint 2 learnings: what changed strategically, new file locations, updated agent behavior.
