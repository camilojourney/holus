# Consultation 007: Visual Variety Routing + Pipeline Architecture Split

**Date:** 2026-03-20 | **Team:** Engineering | **CID:** CONSULT-ENG-20260320-91f73457

## Question

Two decision points:
1. How to route visual type selection with variety (not always data_viz) while maintaining quality
2. Whether to split the 810-line idea_runner.py monolith into separate modules + agent .md files

## Recommendation

### Visual Variety Routing
**Chosen:** Config-driven weighted sampling with recency penalty — zero LLM cost
**Vote:** systems-architect: scoring matrix via prompt context | ml-engineer: scoring matrix in Python | developer-experience: config YAML + recency penalty
**Result:** Unanimous (3-0)

**Rationale:** The variety deficit is caused by a prompt instruction (`DECISION PRIORITY: flowchart > architecture > ...`), not a model limitation. DX consultant proved 9/9 generated visuals default to `data_viz` regardless of temperature. Fix: remove the priority hierarchy, add a `config/visual-variety.yaml` with type weights + recency penalty, sample the type in Python before the LLM call, and pass it as a hard constraint. Cost: $0.00 additional API spend.

**Dissent:** The LLM may produce lower-quality visuals for types it's less practiced at. Forcing "architecture diagram" on a post about a single metric may reduce quality. Mitigation: sample from top-2 scored types, not force a single choice.

**Hypothesis:**
> We believe config-driven visual type selection with recency penalty will produce a distribution where no single type exceeds 35% of visuals (vs current 100% data_viz), while maintaining judge scores >= 0.85 average.
> Confidence: HIGH
> Validation: After 20 content cycles, measure visual type distribution + average judge score
> Timeline: 2 weeks of publishing data
> Fallback: If quality drops, increase weight of top-performing type and narrow distribution

### Pipeline Architecture Split
**Chosen:** Hybrid — extract prompts to .md files + split Python into 4 modules
**Vote:** systems-architect: 4 Python modules | ml-engineer: 4 modules + AGENTS.yaml | developer-experience: extract prompts to .md, keep orchestration
**Result:** Unanimous on principle (3-0), hybrid of all 3 approaches

**Rationale:** The pipeline is 810 lines with 6 responsibilities. Prompts change most frequently but are hardcoded as Python constants. The existing PromptLoader 3-layer system and AGENTS.yaml are already built but unused by this pipeline. Split prompts into `.md` files (unlocks A/B testing at zero cost), split Python along responsibility boundaries (readability + testability), keep orchestration in a thin `idea_runner.py`. Don't build per-stage evaluation until trajectory.jsonl hits 500 entries.

**Dissent:** Splitting introduces coordination risk — if a `.md` prompt outputs a different JSON schema than what the Python parser expects, the pipeline breaks silently. Mitigation: Pydantic validation at each stage boundary.

**Hypothesis:**
> We believe separating prompts from orchestration will reduce time-to-change-a-prompt from "find it in 810 lines of Python" to "open the obvious .md file," and enable prompt A/B testing via the existing PromptLoader infrastructure.
> Confidence: HIGH
> Validation: First prompt A/B test runs successfully via PromptLoader
> Timeline: After trajectory.jsonl hits 500 entries
> Fallback: If coordination failures exceed 2 incidents, consolidate back to monolith

## Action Items
- [ ] Add `config/visual-variety.yaml` with type weights + recency penalty config
- [ ] Add `_pick_visual_type()` function (weighted sampling + recency decay)
- [ ] Remove `DECISION PRIORITY` from VISUAL_DESIGNER_SYSTEM prompt
- [ ] Extract 3 prompt constants to `agentic/agents/specialists/` as `.md` files
- [ ] Register `idea-planner`, `idea-generator`, `visual-designer` in AGENTS.yaml
- [ ] Split idea_runner.py into 4 modules + idea_utils.py
- [ ] Add Pydantic validation at stage boundaries

## Assumptions
| Assumption | Why We Made It | How to Validate | Risk if Wrong |
|---|---|---|---|
| LLM ignores priority hierarchy | 9/9 visuals were data_viz empirically | Already validated | N/A |
| Recency penalty produces variety | Standard exploration/exploitation pattern | Measure type distribution after 20 cycles | Pipeline gets stuck on same 2-3 types |
| PromptLoader handles .md migration | Code already exists at idea_runner.py:108 | First prompt loads from .md successfully | Need to fix PromptLoader integration |
| Splitting doesn't increase LLM cost | Same number of calls, different file locations | Compare cost before/after | Hidden overhead in inter-module communication |
