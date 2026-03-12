# ADR-0005: Agent Self-Improvement Architecture

**Date:** 2026-03-12
**Status:** Accepted
**Deciders:** Juan (human), Opus 4.6 (AI architect)

## Context

Holus has 1,457 lines of self-improvement code (judge.py, learning_loop.py, reflexion.py, prompt_optimizer.py) that have NEVER been called in production. The evaluation pipeline, learning loop, and optimization system exist as Python code but have zero real data flowing through them.

Simultaneously, all agent prompts (TEXT_GENERATOR_PROMPT, OPUS_STRATEGY_PROMPT, SONNET_GENERATION_PROMPT) are hardcoded as Python string constants, preventing versioning, A/B testing, or automated optimization.

Three Opus experts debated the architecture in a formal deliberation:
- **Expert A (Pragmatist)**: Don't move files, just wire what exists. The interfaces are clean.
- **Expert B (Architect)**: Full restructure into specialists/evaluators/optimizers. Current separation is an architectural lie.
- **Expert C (Systems Thinker)**: Root-level agents/ prompt store with Python staying put. Intelligence lives in prompts, not code.

## Decision

**Expert C wins, with A's pragmatism.** Externalize prompts as the intelligence layer. Keep Python plumbing where it is.

### 1. Three-Layer Prompt Architecture

- **Layer 1**: `agents/` at repo root — canonical `.md` files with YAML frontmatter (human-owned, git-versioned)
- **Layer 2**: `config/prompts/{agent_id}/` — versioned variants (optimizer-owned, A/B testing)
- **Layer 3**: Hardcoded Python constants — fallback safety net during migration

Resolution order: optimizer variant → canonical .md → hardcoded fallback.

### 2. Agent File Format: Markdown + YAML Frontmatter

Based on industry research (Open Agent Format, Agent-Flavored Markdown, AGENTS.md Linux Foundation standard):
- Metadata in YAML frontmatter (id, version, category, model_tier, evaluated_by)
- Prompt body in Markdown (the actual intelligence)
- KERNEL template: Role, Scope, Steps, Negatives, Output Contract, Contrastive Examples
- 34-38% cheaper in tokens than JSON, ~10% cheaper than YAML for prompt bodies

### 3. 32-Agent System with Content-Category Specialists

- 1 manager (marketing-strategist) — the ReAct brain
- 22 specialists in 6 content categories:
  - Written Authority (5): hook-architect, storyteller, technical-translator, voice-guardian, cta-strategist
  - Visual (4): carousel-architect, data-visualizer, before-after-designer, brand-designer
  - Video (3): script-writer, brief-composer, caption-specialist
  - Growth (3): lead-magnet-designer, comment-trigger-expert, community-builder
  - Research (4): niche-researcher, seo-strategist, audience-analyst, competitive-intel
  - Repurposing (3): platform-adapter, bilingual-localizer, format-converter
- 7 domain-expert evaluators (not generic judges)
- 2 ops agents (security-sentinel, knowledge-keeper)

### 4. Expertise-Based Evaluators

Each evaluator is a domain expert with category-specific rubric dimensions:

| Evaluator | Rubric Dimensions |
|---|---|
| written-content-judge | hook_strength, narrative_arc, voice_fidelity, authority_signal, readability_score |
| visual-content-judge | visual_hierarchy, brand_alignment, info_clarity, scroll_stop_power, slide_pacing |
| video-content-judge | hook_timing, pacing_score, retention_prediction, caption_quality, cta_strength |
| engagement-judge | conversion_potential, authenticity_score, brand_safety, audience_match |
| seo-judge | keyword_relevance, search_intent_match, topical_authority, uniqueness |
| platform-fit-judge | algorithm_signal_strength, format_compliance, native_feel |
| brand-safety-judge | voice_deviation_score, anti_pattern_count, reputation_risk |

### 5. Wire the Self-Improvement Loop

- JudgeAgent.evaluate() called after every content generation (dispatcher routes by content_type)
- LearningLoop.run() weekly to extract patterns from trajectory
- PromptOptimizer.optimize() when 30+ evaluations accumulated
- Langfuse tracing wired into BaseAgent.run() for token/cost observability

## Consequences

**Positive:**
- Prompts are versionable, A/B testable, reviewable without reading Python
- Each content type gets expert evaluation with domain-specific rubrics
- Self-improvement loop finally produces real data and learns
- Agent system becomes observable via trajectory + Langfuse

**Negative:**
- 32 agents to maintain (mitigated by AGENTS.yaml registry and scaling framework)
- Prompt loading adds one file read per invocation (mitigated by caching)
- Migration period where both hardcoded and external prompts coexist

## Alternatives Considered

1. **Full file restructure** (Expert B): Move self_improvement/ into agents/. Rejected — breaks 606 tests, git blame, and imports for zero new functionality.
2. **Pure YAML agent files** (CrewAI style): Rejected — multiline prompts painful in YAML, 10% more tokens.
3. **JSON agent files**: Rejected — 34-38% more tokens, not human-friendly for long prompts.
4. **Keep hardcoded prompts**: Rejected — prevents versioning, A/B testing, and automated optimization.
