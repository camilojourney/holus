# Domain — Holus

Non-obvious knowledge for agents working in this codebase.

## Non-Obvious Constraints

- Holus is the BRAIN (strategy, decisions, learning). Silos (genpeli, pilaster, social-media-automatization) are the HANDS (execution). Never blur this boundary.
- Data never flows back into Holus permanently — it reads silo data via MCP, processes it for decisions, but the source of truth stays in the silo.
- `config/guardrails.yaml` is SAFETY-CRITICAL — never modify without explicit human approval. Contains kill switch, spending limits, and content restrictions.
- Agents communicate with silos exclusively via MCP (Model Context Protocol). No direct database access, no SSH, no importing silo Python packages.
- The self-improvement system (judge.py, learning_loop.py, reflexion.py, prompt_optimizer.py) is 1,457 lines of code that has NEVER been called in production. Wiring it is the current priority.
- Prompts are the product, code is the plumbing. When improving agent intelligence, edit prompt .md files in `agents/`, not Python code.
- LinkedIn is the primary platform (5x/week). All other platforms (Twitter, Instagram, Threads, Facebook) receive repurposed content adapted to their native voice.
- Content quality gates enforce minimum thresholds before publishing. Three tiers: hard-block (< 40), soft-block (40-60, needs review), warn (60-70).
- The kill switch can halt all agent operations instantly. Always respect it.
- Brand voice is "builder-philosopher" — first person, technical depth without jargon, never corporate speak. See `config/brand.yaml`.
- 9 content types (TUTORIAL, DEMO, TIPS, THREAD, CASE_STUDY, CAROUSEL, VIDEO_REEL, ANNOUNCEMENT, EDUCATIONAL), 5 content pillars, 19 frameworks.
- Trading systems (pythia, milo-to-the-moon) are completely isolated. Holus NEVER references, calls, or monitors them.

## Production Environment

- **Runtime**: Python 3.12 / uv / LangGraph + Claude API (Anthropic)
- **Execution model**: Episodic agent — triggered weekly by cron or manually via Telegram
- **Scheduling**: launchd on macOS (not systemd)
- **Silo MCP servers**: genpeli-mcp (video editing), social-media-mcp (posting + analytics), pilaster-mcp (image generation)
- **Tracing**: Langfuse (configured, being wired into BaseAgent)
- **State storage**: File-based — trajectory.jsonl, lessons.json, eval_history.jsonl, knowledge/*.md
- **No database**: All Holus state lives in files (JSONL, YAML, Markdown). Silos have their own databases.
- **Cost tracking**: Per-agent API costs tracked in trajectory entries (input_tokens, output_tokens, cost_usd)

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Do This Instead |
|---|---|---|
| Generic evaluation rubrics | Different content types need different quality criteria | Use domain-expert evaluators with category-specific rubrics |
| Storing silo data in Holus | Violates the brain/hands boundary, creates stale duplicates | Read via MCP, decide, forget |
| Hardcoding prompts in Python | Can't version, A/B test, or optimize independently | Externalize to .md files in agents/ |
| Running optimization without data | Prompt optimizer needs 30+ trajectory entries | Seed the loop, accumulate data first |
| Copy-paste repurposing | Each platform has different algorithms and voice norms | Use platform-adapter specialist for native adaptation |
| Engagement farming | Destroys credibility, violates brand voice | Frequency-cap growth content (max 1x/2wk per platform) |
| Testing self-improvement with mocks | The whole point is real LLM evaluation | Use real API calls, just limit batch size |

## Glossary

| Term | Definition |
|---|---|
| **ReAct Loop** | Observe → Reason → Act → Evaluate cycle that drives the marketing agent |
| **Silo** | Independent repo with its own data and execution (genpeli, pilaster, social-media-automatization) |
| **MCP** | Model Context Protocol — standardized tool calling interface between Holus and silos |
| **Trajectory** | Append-only JSONL log of every agent decision and outcome (.self-improvement/memory/trajectory.jsonl) |
| **KERNEL Template** | 6-section agent prompt structure: Role, Scope, Steps, Negatives, Output Contract, Contrastive Examples |
| **Content Pillar** | Thematic category: builder_stories, ai_frameworks, industry_analysis, results_proof, contrarian_takes |
| **Kill Switch** | Emergency halt in config/guardrails.yaml — stops all agent operations |
| **Specialist** | Domain-specific agent for one content production sub-skill (e.g., hook-architect, carousel-architect) |
| **Evaluator** | Domain-expert judge with category-specific rubric (e.g., written-content-judge, visual-content-judge) |
| **Quality Gate** | 3-tier enforcement (hard-block, soft-block, warn) based on quality scores |
| **Hook** | First 2 lines of a social media post — determines 80% of engagement |
| **Content Factory** | The specialist pipeline: strategist decides → specialists create → evaluators score → repurposers adapt |
