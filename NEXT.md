# NEXT.md — Holus Task Priority Queue

Last updated: 2026-02-27

## Priority Guide
- **P0** — Blocking. Nothing else works until this is fixed.
- **P1** — Critical path. Required for agent autonomy or revenue.
- **P2** — High value. Major feature or significant improvement.
- **P3** — Medium value. Integration or enhancement.
- **P4** — Nice to have. Polish, optimization, or future prep.

---

## P3: Integration Specs (COMPLETED 2026-02-27)

- [x] Create specs/014-genpeli-integration.md
- [x] Create specs/015-pilaster-integration.md
- [x] Create specs/016-social-media-integration-v2.md
- [x] Update NEXT.md with P4 tasks from integration specs

---

## P4: Integration Implementation Tasks

### Genpeli Integration (Spec 014)

**P4-GEN-001: Implement Genpeli MCP Server**
- [ ] Create `src/holus/mcp_servers/genpeli.py`
- [ ] Implement 5 tools: process_video, check_video_status, get_video_preview, approve_video, reject_video
- [ ] Add MCP server configuration to `.claude/settings.json`
- [ ] Test tool discovery and invocation
- [ ] Document in `docs/integrations/genpeli-mcp.md`

**P4-GEN-002: Video Content Workflow in Marketing Agent**
- [ ] Create `src/holus/agents/marketing/video_workflow.py`
- [ ] Implement `create_video_content()` with Genpeli MCP calls
- [ ] Add video decision support in reason stage
- [ ] Implement polling logic for job completion (5-min timeout)
- [ ] Add error handling for Genpeli API failures

**P4-GEN-003: Video Review Queue**
- [ ] Create `src/holus/agents/marketing/video_queue.py`
- [ ] Implement enqueue_video, list_pending_videos, approve_video, reject_video
- [ ] Create `data/video-queue/` directory
- [ ] Add justfile commands: review-videos, approve-video, reject-video
- [ ] Create CLI script `src/holus/agents/marketing/review_videos.py`

**P4-GEN-004: Source Footage Management**
- [ ] Define asset library structure in `data/assets/footage/`
- [ ] Implement `get_source_footage()` helper
- [ ] Add asset metadata schema (topic tags, quality, platform)
- [ ] Create asset discovery logic for marketing agent
- [ ] Document asset workflow in `docs/guides/video-content-creation.md`

**P4-GEN-005: Genpeli Integration Tests**
- [ ] Create `tests/unit/mcp/test_genpeli.py`
- [ ] Test all 5 MCP tools with mock API responses
- [ ] Test error handling (timeout, API down, processing failed)
- [ ] Test video queue operations
- [ ] Create integration test with real Genpeli API (local)

---

### Pilaster Integration (Spec 015)

**P4-PIL-001: Implement Pilaster MCP Server**
- [ ] Create `src/holus/mcp_servers/pilaster.py`
- [ ] Implement 5 tools: query_experiments, get_successful_prompts, store_experiment, get_ai_suggestions, get_gallery_images
- [ ] Add MCP server configuration to `.claude/settings.json`
- [ ] Test tool discovery and invocation
- [ ] Document in `docs/integrations/pilaster-mcp.md`

**P4-PIL-002: Image Content Workflow in Marketing Agent**
- [ ] Create `src/holus/agents/marketing/image_workflow.py`
- [ ] Implement `create_image_content()` with Pilaster memory lookup
- [ ] Implement `build_informed_prompt()` using successful patterns
- [ ] Add image decision support in reason stage
- [ ] Add outcome storage after generation

**P4-PIL-003: Monthly Image Strategy Optimization**
- [ ] Create `src/holus/agents/marketing/image_optimization.py`
- [ ] Implement `optimize_image_strategy()` monthly analysis
- [ ] Extract success patterns from experiments
- [ ] Extract failed patterns to avoid
- [ ] Write insights to `.self-improvement/knowledge/current/image-generation.md`

**P4-PIL-004: Image Generation Best Practices Knowledge**
- [ ] Create `.self-improvement/knowledge/current/image-generation.md`
- [ ] Document prompt patterns by style (product, abstract, technical)
- [ ] Document successful parameter combinations
- [ ] Document platform-specific requirements
- [ ] Track success rate trends over time

**P4-PIL-005: Pilaster Integration Tests**
- [ ] Create `tests/unit/mcp/test_pilaster.py`
- [ ] Test all 5 MCP tools with mock API responses
- [ ] Test memory-driven prompt building
- [ ] Test monthly optimization logic
- [ ] Create integration test with real Pilaster API (local)

---

### Social Media Integration V2 (Spec 016)

**P4-SOC-001: Enhanced Social Media MCP Server**
- [ ] Update `src/holus/mcp_servers/social_media.py` with dual backend support
- [ ] Implement backend routing logic (local vs Late API)
- [ ] Add all 9 tools: post_content, post_story, get_analytics, get_top_posts, schedule_post, get_scheduled_posts, get_accounts
- [ ] Test fallback behavior when one backend unavailable
- [ ] Document in `docs/integrations/social-media-mcp-v2.md`

**P4-SOC-002: Bilingual Content Routing**
- [ ] Create `config/social_accounts.yaml` with account mappings
- [ ] Implement bilingual routing in local service integration
- [ ] Test EN → "experience" accounts, ES → "journey" accounts
- [ ] Verify LinkedIn/Twitter receive source language only
- [ ] Add validation for account configuration

**P4-SOC-003: Analytics Integration in Marketing Agent**
- [ ] Update observe stage to call `get_analytics` MCP tool
- [ ] Parse analytics data into MarketingState
- [ ] Extract top-performing content types
- [ ] Extract per-platform engagement trends
- [ ] Feed analytics into Opus reasoning prompt

**P4-SOC-004: Social Content Workflow**
- [ ] Create `src/holus/agents/marketing/social_workflow.py`
- [ ] Implement platform-specific content adaptation
- [ ] Implement scheduling logic (optimal times per platform)
- [ ] Add approval queue for high-risk platforms (IG, TikTok)
- [ ] Add auto-post for low-risk platforms (LinkedIn, Twitter)

**P4-SOC-005: Social Media Integration Tests**
- [ ] Create `tests/unit/mcp/test_social_media_v2.py`
- [ ] Test all 9 MCP tools
- [ ] Test bilingual routing logic
- [ ] Test backend fallback behavior
- [ ] Test analytics aggregation
- [ ] Create integration test with mock social API responses

---

### Cross-Integration Tasks

**P4-INT-001: MCP Server Discovery and Registration**
- [ ] Update `.claude/settings.json` with all 3 MCP servers
- [ ] Verify marketing agent can discover all tools
- [ ] Test tool invocation across all servers
- [ ] Add error handling for MCP connection failures
- [ ] Document MCP server management in `docs/architecture/mcp-servers.md`

**P4-INT-002: Marketing Agent Act Stage Enhancement**
- [ ] Update act stage to use MCP tools for content creation
- [ ] Implement content type routing (text → social, image → pilaster, video → genpeli)
- [ ] Add parallel content generation for efficiency
- [ ] Implement approval queue for all content types
- [ ] Add comprehensive error handling and retry logic

**P4-INT-003: Content Queue Management CLI**
- [ ] Create unified CLI for all content queues (text, image, video)
- [ ] Implement `just review-content-all` to show all pending items
- [ ] Implement `just approve-all` to batch-approve low-risk content
- [ ] Add filtering by product, platform, content type
- [ ] Create web UI preview for content queue (optional, nice-to-have)

**P4-INT-004: Analytics Dashboard**
- [ ] Aggregate analytics from all platforms
- [ ] Create visual dashboard (simple HTML + Chart.js)
- [ ] Show engagement trends over time
- [ ] Show per-product performance comparison
- [ ] Show content type effectiveness
- [ ] Export analytics to CSV for external analysis

**P4-INT-005: Integration Monitoring and Health Checks**
- [ ] Create health check endpoint for each integration
- [ ] Implement status dashboard showing service availability
- [ ] Add alerting for integration failures
- [ ] Create recovery playbooks for common failures
- [ ] Document in `docs/operations/integration-health.md`

---

### Knowledge and Memory Enhancements

**P4-KNW-001: Image Generation Knowledge Base**
- [ ] Create `.self-improvement/knowledge/current/image-generation.md`
- [ ] Document successful prompt patterns by style
- [ ] Document parameter combinations that work
- [ ] Track quality score trends
- [ ] Update monthly based on Pilaster optimization

**P4-KNW-002: Video Content Knowledge Base**
- [ ] Create `.self-improvement/knowledge/current/video-content.md`
- [ ] Document video topics that perform well
- [ ] Document optimal video lengths per platform
- [ ] Track caption styles that resonate
- [ ] Document source footage categorization

**P4-KNW-003: Platform-Specific Best Practices**
- [ ] Create `.self-improvement/knowledge/current/platforms/linkedin.md`
- [ ] Create `.self-improvement/knowledge/current/platforms/twitter.md`
- [ ] Create `.self-improvement/knowledge/current/platforms/instagram.md`
- [ ] Document optimal posting times per platform
- [ ] Document content format preferences per platform

**P4-KNW-004: Content Performance Memory**
- [ ] Enhance `.self-improvement/MEMORY.md` with content insights
- [ ] Track which topics resonate most
- [ ] Track which products get most engagement
- [ ] Track seasonal trends (if data available)
- [ ] Document learnings in weekly memory updates

---

### Testing and Quality

**P4-TST-001: Integration Test Suite**
- [ ] Create `tests/integration/test_content_pipeline_full.py`
- [ ] Test end-to-end: decision → image gen → video gen → social post
- [ ] Test error recovery across all integrations
- [ ] Test MCP server failures and fallbacks
- [ ] Measure end-to-end latency (target: < 10 min for full pipeline)

**P4-TST-002: Load Testing**
- [ ] Test concurrent content generation (3+ pieces in parallel)
- [ ] Test queue depth limits (100+ items)
- [ ] Test MCP server stability under load
- [ ] Identify performance bottlenecks
- [ ] Document scaling limits in `docs/performance/load-testing.md`

**P4-TST-003: Cost Monitoring**
- [ ] Track API costs per integration (Anthropic, Replicate, etc.)
- [ ] Set up cost alerts (> $10/day threshold)
- [ ] Analyze cost per content piece
- [ ] Optimize expensive operations
- [ ] Document in `docs/operations/cost-management.md`

---

### Documentation

**P4-DOC-001: Integration Architecture Documentation**
- [ ] Create `docs/architecture/integrations-overview.md`
- [ ] Document federated MCP pattern
- [ ] Explain backend routing decisions
- [ ] Create architecture diagrams (mermaid)
- [ ] Document data flows

**P4-DOC-002: MCP Server Developer Guide**
- [ ] Create `docs/guides/creating-mcp-servers.md`
- [ ] Document MCP tool interface design
- [ ] Provide examples from existing servers
- [ ] Document testing strategies
- [ ] Document deployment and registration

**P4-DOC-003: Content Creation Workflow Guide**
- [ ] Create `docs/guides/content-workflows.md`
- [ ] Document text content creation workflow
- [ ] Document image content creation workflow
- [ ] Document video content creation workflow
- [ ] Include approval process and queue management

**P4-DOC-004: Troubleshooting Guide**
- [ ] Create `docs/troubleshooting/integrations.md`
- [ ] Document common failure modes
- [ ] Provide diagnostic commands
- [ ] Include recovery procedures
- [ ] Link to relevant health check tools

---

## Notes

- **Genpeli tasks depend on**: Genpeli API running locally (port 8100)
- **Pilaster tasks depend on**: Pilaster Next.js app running locally (port 3000)
- **Social Media tasks depend on**: social-media-automatization API running (port 8000) OR Late API key configured
- **All tasks depend on**: Marketing agent baseline from Spec 010 (observe-reason-act-evaluate loop)

## Next Actions (Human)

1. **Prioritize P4 tasks**: Which integration should be implemented first? (Suggestion: Social Media V2 → Pilaster → Genpeli)
2. **Assign owners**: Who implements each integration? (Single developer, pair, or autonomous builder?)
3. **Set milestones**: When should each integration be complete?
4. **Configure services**: Ensure all backend services are running and accessible
5. **Review and merge**: Review this NEXT.md and merge to main branch

---

**Generated by:** Fruco (Holus Spec Writer)  
**Date:** 2026-02-27  
**Context:** P3 Integration Specs cron task
