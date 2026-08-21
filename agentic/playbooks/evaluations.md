# Evaluations Playbook - Holus

How content and agents are evaluated in the Holus system.

## Evaluation Architecture

### Three Evaluation Layers

1. **Quality Scorer** (`quality_score.py`) - rule-based automated scoring at generation time
   - Runs synchronously during content creation, before any LLM judge is invoked
   - Pass threshold: score >= 60. Content below this is auto-rejected and logged, not queued.
   - Content starts at 100 and loses points per violation (penalty-based, not additive)
   - Checks run in order:
     - `char_limit` - exceeds platform character limit (penalty: 30)
     - `anti_pattern` - contains corporate-speak phrases from `DEFAULT_ANTI_PATTERN_PHRASES` (penalty: 15 each)
     - `content_anti_pattern` - forbidden topics: trading, financial advice, pythia, milo-to-the-moon (penalty: 50 each)
     - `weak_hook` - first line shorter than 10 chars (penalty: 15)
     - `missing_pillar` - invalid or absent content pillar (penalty: 10)
     - `exclamation_density` - more than 3% of chars are `!` (penalty: 10)
     - `emoji_density` - emoji chars exceed 2% of total (penalty: 10)

2. **Domain-Expert Judges** (`agentic/agents/evaluators/`) - LLM-based evaluation after generation
   - Runs asynchronously after content passes the quality gate
   - Each judge is a domain expert with a category-specific rubric defined in `agentic/agents/AGENTS.yaml`
   - 7 domain judges + 1 cross-cutting brand-safety gate (runs on all content)
   - Model tier: `classification` (cost-efficient - same principle as `judge.py` using Haiku)
   - Output: scored rubric dimensions with specific, actionable feedback

3. **Self-Improvement Judge** (`src/holus/self_improvement/judge.py`) - agent output evaluator
   - Used by the self-improvement loop, not the content pipeline
   - Evaluates agent task outputs (trade signals, code reviews, general tasks) - not marketing content
   - Model: `claude-haiku-3-5-20241022` - deliberately separate from worker models to avoid self-evaluation bias
   - Verdicts: `PASS` (score >= 0.8, no critical errors), `PARTIAL` (score >= 0.5), `FAIL` (score < 0.5 or critical errors)
   - Scoring dimensions: correctness, completeness, reasoning_quality, actionability
   - NEVER optimized by DSPy - circular dependency: you cannot optimize the grader

### Quality Gate Tiers

| Score Range | Tier | Action |
|---|---|---|
| 60-100 | PASS | Admitted to judge queue |
| 0-59 | FAIL | Auto-rejected, violation log written, not queued |

Note: the 70/50 breakdown used by the domain judges (PASS/PARTIAL/FAIL) is separate from this gate.

### Evaluator Routing

Each specialist in `agentic/agents/AGENTS.yaml` declares which evaluator scores it via `evaluated_by`. The brand-safety-judge runs as a cross-cutting gate on all content flagged with `gate: true`.

| Specialist Category | Primary Evaluator |
|---|---|
| written-authority (hook-architect, storyteller, technical-translator, cta-strategist) | written-content-judge |
| visual (carousel-architect, data-visualizer, before-after-designer, brand-designer) | visual-content-judge |
| video (script-writer, brief-composer, caption-specialist) | video-content-judge |
| growth (lead-magnet-designer, comment-trigger-expert, community-builder) | engagement-judge |
| research (niche-researcher, seo-strategist, audience-analyst, competitive-intel) | seo-judge |
| repurposing (platform-adapter, bilingual-localizer, format-converter) | platform-fit-judge |
| voice-guardian (gate) | brand-safety-judge |
| brand-designer (gate) | visual-content-judge + brand-safety-judge |

### Evaluator Rubrics

Each evaluator has weighted rubric dimensions defined in `agentic/agents/AGENTS.yaml`:

**written-content-judge:**
- hook_strength - Does the hook stop the scroll?
- narrative_arc - Is there a clear story with tension?
- voice_fidelity - Does it match the builder-philosopher archetype?
- authority_signal - Does it demonstrate expertise?
- readability_score - Is it scannable and clear?

**visual-content-judge:**
- visual_hierarchy - Clear information flow?
- brand_alignment - Consistent with brand identity?
- info_clarity - Is the message clear at a glance?
- scroll_stop_power - Would you stop scrolling?
- slide_pacing - Right amount per slide?

**video-content-judge:**
- hook_timing - First 3 seconds compelling?
- pacing_score - Right speed throughout?
- retention_prediction - Will viewers watch to end?
- caption_quality - Readable when muted?
- cta_strength - Clear next step?

**engagement-judge:**
- conversion_potential - Does it drive action?
- authenticity_score - Does it feel genuine?
- brand_safety - Does it stay within brand bounds?
- audience_match - Right fit for the target persona?
- frequency_compliance - Respects content cadence rules?

**seo-judge:**
- keyword_relevance - Target keywords present naturally?
- search_intent_match - Matches what the audience is searching for?
- topical_authority - Builds domain credibility?
- competitive_gap_fill - Addresses underserved topics?
- uniqueness - Distinct from existing content?

**platform-fit-judge:**
- algorithm_signal_strength - Optimized for platform algorithm?
- format_compliance - Follows platform format requirements?
- native_feel - Reads like platform-native content?
- timing_appropriateness - Right cadence for the platform?

**brand-safety-judge** (cross-cutting gate):
- voice_deviation_score - Any corporate speak or off-brand tone?
- anti_pattern_count - Matches against brand.yaml anti-patterns
- reputation_risk - Could this harm the brand?
- forbidden_content_check - Trading, financial advice, or competitor mentions?

## Company OS Skill Evaluations

Company OS domain skill contracts are project-local in `.agents/skills/` and
are evaluated offline by `tests/unit/agentic/test_company_os_skill_contracts.py`.
The shared adapter reads `agentic/evals.yaml`; it receives only frozen source
paths and non-sensitive scorecard summaries. The contract verifies trigger
cases, the `COMPANY_KILL` halt behavior, explicit approval routing, and that a
handoff never becomes an external action.

```bash
uv run pytest tests/unit/agentic/test_company_os_skill_contracts.py -q
```

## Running Evaluations

```bash
just evaluate          # Run judge on last 7 days of trajectory
just learn             # Extract patterns from evaluations
just costs             # Show per-agent cost breakdown
```

## Adding a New Evaluator

1. Create `agentic/agents/evaluators/{name}.md` following the KERNEL template (Role, Scope, Steps, Negatives, Output Contract, Contrastive Examples)
2. Add entry to `agentic/agents/AGENTS.yaml` under the evaluators section with `type: evaluator`, `model_tier: classification`, and `rubric` list
3. Update specialist entries in `agentic/agents/AGENTS.yaml` - set `evaluated_by: {name}` on the relevant specialists
4. If it is a blocking gate (like brand-safety-judge), add `gate: true` to the evaluator entry
5. Run `just check` to verify no test breakage

## Evaluation Data Flow

```
Content generated
  → quality_score.py (sync, rule-based gate)
      score < 60: auto-reject, log violation, stop
      score >= 60: admit to judge queue
  → domain evaluator selected via AGENTS.yaml evaluated_by
  → evaluator .md prompt loaded (agentic/agents/evaluators/{name}.md)
  → LLM scores rubric dimensions (classification model tier)
  → brand-safety-judge runs cross-cutting on all gated content
  → Results written to trajectory.jsonl
  → Weekly: learning_loop.py reads trajectory, extracts patterns
  → Updates MEMORY.md and knowledge files
```

## Design Constraints

- **Judges are never the same model as the worker.** Self-evaluation bias inflates scores. The judge model (Haiku for self-improvement, classification tier for content) is always a separate call.
- **Judges are never optimized.** DSPy or prompt optimizers cannot touch evaluator prompts - that would close a feedback loop that invalidates the evaluation signal.
- **Quality gate is rule-based, not LLM.** The sync gate (`quality_score.py`) uses deterministic rules so it cannot be gamed by generation prompt changes.
- **Forbidden content is a hard block.** `content_anti_pattern` violations carry 50-point penalties per match - a single mention of trading or financial advice fails the gate outright.
- **brand-safety-judge is the last line.** Even content that passes the quality gate and domain judge can be blocked by brand-safety. It is the only evaluator that can override a domain PASS.
