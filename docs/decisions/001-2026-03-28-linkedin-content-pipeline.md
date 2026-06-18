# Pipeline: Holus LinkedIn Content Pipeline

**Date:** 2026-03-28 | **Team:** Allocator | **CID:** ALLOCATOR-20260328-e26b8625
**Vote:** Unanimous 3-0 (Round 2 skipped)

## Question
Design the full pipeline for LinkedIn content posting — from research to publish. Include humanization, compliance check, brand voice, engagement prediction.

## Overview
- **Total phases:** 7 (Phase 0: Trigger + Phases 1-6)
- **Total agents:** 9 LLM + 2 deterministic
- **Total gates:** 6 quality gates
- **Patterns:** Chaining (primary) + Parallelization (Phase 1) + Evaluator-Optimizer (Phase 4)
- **Progressive thresholds:** 60 → 60 → 70 → 75 → 80 → 75 (composite)
- **Estimated latency:** 90-120s end-to-end
- **Estimated cost:** ~$0.50-1.20 per post
- **Autonomous rate:** ~57% (43% routed to human at various gates)
- **Bad content escape rate:** <2%

## Pipeline Diagram

```
[TRIGGER deterministic]
    │
    ▼
[RESEARCH: 3 Sonnet gatherers ║ parallel → Haiku aggregator]
    │ Gate 1: soft 60, D1≥50
    ▼
[DRAFT: Opus creator + brand voice]
    │ Gate 2: progressive 60→68→75, D1≥55
    ▼
[REVIEW: Gemini critic → PoLL consensus]
    │ Gate 3: PoLL consensus 70, D1≥65
    │         ↺ loop to DRAFT (max 2)
    ▼
[HUMANIZE: Opus humanizer ↔ Gemini AI-detection critic]
    │ Gate 4: soft 75, D4≥70 (3 retries)
    ▼
[COMPLIANCE: Gemini auditor + deterministic regex]
    │ Gate 5: hard + soft 80, D7≥80 (BLOCKING)
    ▼
[ENGAGEMENT PREDICTION: Sonnet predictor]
    │ Gate 6: progressive + human (conditional)
    ▼
[PUBLISH: deterministic + human gate]
```

## Phase 0: Trigger (Deterministic)
- **Agents:** None (pure deterministic)
- **Action:** Check content calendar, API key health, posting cooldown (18h), circuit breaker status
- **Output:** `trigger_payload.json` {content_type, target_audience, timing_slot}
- **Gate:** Hard — abort if API keys expired or cooldown active

## Phase 1: Research (Parallelization — 3+1 agents)

| Agent | Archetype | Model | Input | Output |
|-------|-----------|-------|-------|--------|
| Topic Gatherer | Gatherer | Sonnet | Repo state (Pilaster, genpeli, invoz) | Recent features, wins, updates |
| Audience Analyst | Analyst | Sonnet | social-media MCP analytics | Top topics, engagement patterns, sentiment |
| Trend Scanner | Gatherer | Sonnet | LinkedIn trending, competitor posts | Trending topics, industry signals |
| Research Aggregator | Synthesizer | Haiku | 3 gatherer outputs | `research_brief.json` |

### Gate 1: Research → Draft
- **Type:** Soft Gate + Retry
- **Threshold:** 60
- **Dimensions:** D1 Accuracy (w=0.6), D2 Completeness (w=0.4)
- **Mandatory floor:** D1 ≥ 50
- **Retry:** max 2, re-run weakest gatherer
- **Fallback:** Proceed with `research_confidence: LOW` flag

## Phase 2: Draft (Single agent)

| Agent | Archetype | Model | Input | Output |
|-------|-----------|-------|-------|--------|
| Content Creator | Creator | Opus | research_brief + brand_voice_spec | draft_post.md + meta.json |

**Brand voice spec:** Direct assertions, first-person experience, technical depth + accessible framing, contrarian angles preferred. Anti-patterns: "I think", "It's worth noting", corporate speak, humble brag.

**Sandwich:** Validate research_brief → Opus drafts → Check word count (100-300), CTA presence, no external links in first line.

### Gate 2: Draft → Review
- **Type:** Progressive Gate
- **Threshold:** 60 → 68 → 75 (across retries)
- **Dimensions:** D3 Clarity (w=0.3), D5 Hook Quality (w=0.3), D2 Completeness (w=0.2), D1 Accuracy (w=0.2)
- **Retry:** max 2 with targeted feedback
- **Fallback:** Pass to Review with `draft_quality: BELOW_THRESHOLD` flag

## Phase 3: Review (PoLL Consensus)

| Agent | Archetype | Model | Input | Output |
|-------|-----------|-------|-------|--------|
| Editor Critic | Critic | Gemini | draft + topic headline/angle only | Scores + revision instructions (max 3) |

**Context scoping:** Reviewer does NOT see voice spec — judges output, not intent. Prevents confirmation bias.

### Gate 3: Review → Humanize
- **Type:** Consensus Gate (PoLL — 3 model families)
- **Threshold:** Unanimous pass on composite ≥ 70
- **Dimensions:** D1 Accuracy (w=0.25), D3 Clarity (w=0.25), D5 Hook Quality (w=0.25), D6 Brand Voice (w=0.25)
- **PoLL:** Gemini scores D1+D3, Opus scores D5+D6, Codex scores D1+D3
- **Split handling:** ANY split → human review queue
- **Loop:** If REVISE, draft + revision_instructions back to Drafter (max 2 loops, then force-pass)

## Phase 4: Humanize (Evaluator-Optimizer — 2 agents)

| Agent | Archetype | Model | Input | Output |
|-------|-----------|-------|-------|--------|
| Humanizer | Humanizer | Opus | reviewed draft + detector patterns | humanized_post.md + changes_made[] |
| AI-Detection Critic | Critic | Gemini | humanized post | AI-detection score (0-100) |

**Loop:** If AI-detection score > 30 → return to Humanizer with specific flags. Max 3 iterations, take best scoring version.

**AI tells to remove:** Uniform sentence length, "delve", "landscape", "leverage", list-heavy structure, perfect grammar. Add: dash usage, parentheticals, sentence fragments.

### Gate 4: Humanize → Compliance
- **Type:** Soft Gate + Retry
- **Threshold:** 75
- **Dimensions:** D4 Authenticity (w=0.50), D6 Brand Voice (w=0.30), D3 Clarity (w=0.20)
- **Mandatory floor:** D4 ≥ 70 (non-negotiable)
- **Retry:** max 3 (extra retries — humanization is iterative)
- **Fallback:** Escalate to human with side-by-side (original vs best humanization)

## Phase 5: Compliance (Hard + Soft Gate)

| Agent | Archetype | Model | Input | Output |
|-------|-----------|-------|-------|--------|
| Compliance Auditor | Compliance-Checker | Gemini | humanized draft + policy rules only | compliance_report.json |

**Context scoping:** Compliance checker is INTENTIONALLY context-blind to topic/analytics. Audits text only, preventing bias.

**Deterministic pre-scan:** Regex for competitor names, dollar amounts, percentages, superlatives, engagement bait phrases.

### Gate 5: Compliance → Predict
- **Type:** Hard Gate (deterministic) + Soft Gate (LLM for gray areas)
- **Threshold:** Hard must pass. Soft ≥ 80 on D7
- **Mandatory floor:** D7 ≥ 80
- **Retry:** max 1 with specific rewrite suggestion
- **Fallback:** **BLOCK.** Route to human. This gate does NOT degrade gracefully.

## Phase 6: Engagement Prediction + Publish

| Agent | Archetype | Model | Input | Output |
|-------|-----------|-------|-------|--------|
| Engagement Predictor | Analyst | Sonnet | final draft + historical performance | prediction.json |
| Publisher | (deterministic) | N/A | final draft + prediction + compliance verdict | Published post URL |

### Gate 6: Predict → Publish
- **Type:** Progressive + Human (conditional)
- **Threshold:** Based on percentile vs last 10 posts:
  - ≥ median → auto-eligible
  - 25th-50th percentile → publish with `low_confidence` tag
  - < 25th percentile → Human Gate activates
- **Final composite:** 75 across all 7 dimensions (D1-D7)
- **Mandatory floors:** D1≥65, D4≥70, D7≥80

**Human gate:** Present final content, engagement prediction, composite score, comparison to recent posts. Juan decides: publish / edit / kill. Auto-publish after 15-min window (configurable).

**Post-publish:** Log to trajectory store, schedule engagement checks at +2h, +24h, +7d.

## Custom Quality Dimensions (7)

| ID | Dimension | Weight | Mandatory | Used At |
|----|-----------|--------|-----------|---------|
| D1 | Accuracy | 0.20 | YES | Gates 1-3, 6 |
| D2 | Completeness | 0.15 | NO | Gates 1-2 |
| D3 | Clarity | 0.15 | NO | Gates 2-4 |
| D4 | Authenticity | 0.15 | YES | Gates 4, 6 |
| D5 | Hook Quality | 0.10 | NO | Gates 2-3 |
| D6 | Brand Voice | 0.10 | NO | Gates 3-4 |
| D7 | Compliance | 0.15 | YES | Gates 5-6 |

## Handoff Context Flow

| From → To | What Flows | What's Scoped Out | Narrative Cast |
|-----------|-----------|-------------------|----------------|
| Research → Draft | selected_topic + recent_performance | Raw analytics, rejected topics | "Here's the strongest topic. Make it sound like Juan." |
| Draft → Review | draft + headline/angle only | Evidence, voice spec, analytics | "Score this. You don't know the voice spec." |
| Review → Draft (loop) | draft + 3 revision instructions | Scores, rationale | "Fix these 3 things. Nothing else." |
| Review → Humanize | reviewed draft only | Topic, scores, revision history | "Make this read human. No topic context." |
| Humanize → Compliance | humanized draft only | Changes, patterns, everything upstream | "Audit against policy. Zero context about intent." |
| Compliance → Predict | draft (if CLEAR) + recent_performance | Violations, policy rules | "Forecast performance given baselines." |
| Predict → Publish | final draft + verdict + prediction | Everything else | "Ship it." |

## Observability

### Telemetry per step
```python
telemetry("start", pipeline_id=CID, agent="{name}", phase="{phase}")
telemetry("complete", pipeline_id=CID, agent="{name}", tokens=N, duration_ms=T, verdict="PASS|FAIL")
telemetry("handoff", pipeline_id=CID, from="{agent}", to="{agent}", context_bytes=N)
```

### Alert thresholds
| Metric | Threshold | Action |
|--------|-----------|--------|
| Any agent > 60s | WARN | Log |
| Any agent > 120s | ALERT | Timeout + retry |
| Review loop > 2 | FORCE_PASS | Flag + continue |
| Pipeline total > 5 min | ALERT | Investigate |
| Token budget > 50k | WARN | Check context leaks |

### Circuit breaker integration
- Research: 3 consecutive gate failures → trip → human research queue
- Humanize: 3 consecutive authenticity fails → trip → pause for prompt recalibration
- Compliance: 3 consecutive same-rule hits → trip → strategy review

## Token Budget Estimate
| Phase | Tokens | Cost |
|-------|--------|------|
| Research (3 agents + aggregator) | ~12k | $0.05 |
| Draft | ~8k | $0.15 |
| Review | ~4k | $0.10 |
| Humanize (with loop) | ~8k | $0.20 |
| Compliance | ~3k | $0.08 |
| Prediction | ~4k | $0.05 |
| PoLL (Gate 3) | ~6k | $0.30 |
| **Total** | **~45k** | **$0.50-1.20** |

## Reliability
- **P(good content publishes autonomously):** ~57%
- **P(bad content escapes all gates):** <2%
- **Autonomous improves over time:** as voice model improves, engagement predictions calibrate, PoLL consensus rate increases

## Action Items
- [ ] Build trigger phase (cron + API health check + cooldown)
- [ ] Implement research aggregator (Haiku-based merge)
- [ ] Create brand_voice_spec.md from Juan's actual LinkedIn posts
- [ ] Build compliance_rules.json (deterministic regex + LLM rubric)
- [ ] Wire PoLL at Gate 3 (reuse eval_gate.py infrastructure)
- [ ] Train engagement predictor on historical post data (need 50+ posts)
- [ ] Build AI-detection critic prompt (calibrate against Juan's real posts)
- [ ] Wire telemetry hooks per step
- [ ] Configure circuit breakers for 3 failure points
- [ ] Create `.pipeline-state/` schema for this pipeline

## Key Risks
1. **Humanization loop convergence** — if critic and humanizer disagree on "human-sounding", loop burns 3 iterations with mediocre output. Mitigate: seed with 5-10 Juan posts as few-shot, calibrate threshold.
2. **Authenticity gate threshold** — may be miscalibrated. Mitigate: run 50 posts through Gate 4, compute judge-human Spearman, recalibrate if ρ < 0.6.
3. **Review loop thrashing** — vague revision instructions cause drafter to thrash. Mitigate: constrain to max 3 specific instructions with location references.
