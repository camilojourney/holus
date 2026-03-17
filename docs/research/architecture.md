---
title: Architecture Research — Design Patterns & System Design
domain: multi-agent-systems
owner: holus-research
last_updated: 2026-03-17
review_cadence: 90
next_review: 2026-06-15
---

# Architecture Research — Design Patterns & System Design

Architecture research for Holus: deterministic creativity patterns, creative tool registry design, agent evaluation infrastructure, observability, self-improvement mechanisms, platform isolation, and gap detection.

---

## Deterministic Creativity Architecture

### Core Thesis: Creativity Is Constrained Judgment at Scale

Creativity is not magic. It is pattern recognition plus judgment applied within constraints. An artist doesn't invent new colors -- they choose from a curated palette with intention. An AI agent doesn't invent new formats -- it selects from a deterministic toolset based on context signals. The creative output emerges from the quality of the selection, not the randomness of generation.

- Creativity = right tool + right moment + right judgment
- Constraints don't limit creativity -- they enable sharper decisions
- The agent's "personality" is the taste it develops through feedback loops
- Human accountability remains irreplaceable -- someone must own the judgment call

### Architecture: Hybrid Deterministic-Neural

The most powerful creative agent systems combine two paradigms: symbolic (deterministic, rule-based tools) and neural (probabilistic, context-aware judgment). The tools are deterministic. The selection logic is neural. This separation is what makes the system reliable AND creative.

#### The 5 Layers

1. **Tool Registry** -- Pre-vetted, deterministic assets (templates, palettes, layouts, formats). Each tool has a fixed schema, predictable output, versioned behavior.

2. **Context Parser** -- Neural layer reads the content signal -- tone, urgency, audience, platform -- and encodes it as a structured context object.

3. **Selection Engine** -- The agent's judgment layer. Maps context signals to tool combinations via rules you define + learned preferences from feedback.

4. **Execution Pipeline** -- Tools are called deterministically with the selected parameters. Output is consistent and auditable.

5. **Feedback Loop** -- Engagement data flows back, updating selection weights. The agent gets better at choosing over time.

### Toolset Design: Building Your Creative Palette

Every tool in your registry should be independently valid. The agent never creates a bad output -- it only combines good components. Design your toolset like a design system: modular, interchangeable, opinionated.

- **Templates:** 3-5 carousel/post layouts, each with a defined use case (educational, emotional, provocative, storytelling, data-driven)
- **Color Palettes:** 4-6 palettes mapped to tone signals (warm = trust/connection, cool = authority/precision, contrast = urgency/action)
- **Typography Pairings:** Pre-approved font combos with hierarchy rules per layout
- **Voice Modes:** Tone variants (direct, reflective, conversational, analytical) mapped to content type
- **Format Rules:** Platform-specific constraints baked in -- character limits, aspect ratios, CTA placement

### Selection Logic: Three Modes of Agent Judgment

You are in an experimental phase. The right answer is not to pick one selection mode -- it is to run all three simultaneously and let data tell you which performs best per content type.

#### Mode 1 -- Rule-Based (Deterministic)
IF tone = urgent THEN palette = high-contrast + template = minimal-cta. You define the rules explicitly. 100% predictable. Best for brand safety.

#### Mode 2 -- Experimental (A/B)
Agent randomly selects between 2-3 approved options for the same content type. Measures engagement. Discovers which rules to write next.

#### Mode 3 -- Learned (Reinforcement)
Agent builds preference weights from historical performance. "Posts with warm palette + storytelling template got 2.3x more saves." Selection becomes probabilistic but informed.

#### Meta-strategy
Start with Mode 1 to establish baseline. Run Mode 2 to discover gaps. Let Mode 3 optimize at scale. Never abandon Mode 1 entirely -- keep deterministic guardrails even as the agent learns.

### Content Pipeline: Authenticity-Preserving Multi-Platform Repurposing

You generate one original thought. The agent repurposes it across platforms without diluting your voice. This is not AI replacing creativity -- it is AI handling the distribution labor so your creative energy goes into the original insight.

1. **Source:** One raw thought from you -- unfiltered, personal, real. This is the seed.
2. **Core Extraction:** Agent identifies the core tension or insight. Strips it to its most essential form.
3. **Platform Adaptation:** LinkedIn = narrative + professional framing. Twitter/X = provocation + hook. Instagram = visual metaphor + short copy. Newsletter = expanded reasoning.
4. **Voice Preservation:** Each platform variant preserves your specific linguistic patterns, not generic AI prose. This requires fine-tuning your voice model on your own writing.
5. **Authenticity Check:** The test is simple -- would you say this? If the agent produces something you wouldn't say, the voice model needs recalibration, not more prompting.

### Research Findings (2025)

The architecture described here matches the frontier of agentic AI research. This is not experimental -- it is what the field is converging on.

- **Neuro-Symbolic Integration** is the dominant emerging paradigm: combining deterministic symbolic reasoning with neural generative capabilities. Exactly this architecture.
- **Multi-agent creative workflows** are validated: specialized agents chaining outputs (transcript -> themes -> blog -> carousel -> image) reduce manual effort by up to 80% in enterprise implementations.
- **Determinism as a force multiplier:** in production systems, deterministic tool registries dramatically reduce debugging time and increase trust in outputs. Stochasticity belongs in selection, not execution.
- **Feedback loops are the compounding advantage:** agents with memory-augmented architectures that track performance data consistently outperform stateless agents. The learning loop is the moat.
- **2026 trajectory:** platforms are becoming autonomous. The question shifts from "what should I build?" to "what objective should the system pursue?"

### The Real Insight: Why This All Comes Back to Emotion

All of this architecture is in service of one thing: emotional resonance. AI can produce infinite content. The only thing that makes content matter is whether it makes someone feel something. The system's job is not to generate -- it is to connect.

- The product is not the content. The product is the feeling the content creates in someone.
- Emotional connection is the variable that AI cannot fully optimize alone -- it needs a human with real experience to seed it.
- Your lived experience -- building products, the job search, the language struggle -- is not background noise. It is the source material that makes the content irreplaceable.
- AI amplifies signal. It cannot create signal from nothing. You are the signal. The system is the amplifier.
- This is the moat: not the technical architecture, but the authenticity of the ideas flowing into it.

### How This Maps to Holus (Today)

| Concept | Current Implementation | Gap |
|---------|----------------------|-----|
| Tool Registry | `brand-visual.yaml` + 4 slide templates + voice rules | Need more template variants (educational, storytelling, data-driven) |
| Context Parser | Opus planner in `idea_runner.py` reads raw idea + decides format | Works -- could add tone/urgency detection |
| Selection Engine | Currently Mode 1 only (deterministic rules) | Need Mode 2 (A/B) and Mode 3 (learned weights) |
| Execution Pipeline | Playwright PDF render, deterministic | Working end-to-end |
| Feedback Loop | Analytics warehouse exists in social-media-automatization | Not yet wired back into selection weights |
| Voice Preservation | `<voice_rules>` in generator prompt + `<content_fidelity>` gate | Working but needs more negative examples |
| Authenticity Check | Human review in Observatory | Working |

#### What to build next (priority order)

1. **More template variants** -- expand from 1 carousel design to 3-5 (educational, storytelling, data-driven, provocative, minimal)
2. **Tone detection** -- context parser should classify the idea's tone and route to the right template/palette
3. **A/B mode** -- for the same idea, generate 2 visual variants, publish both (different days/platforms), measure which performs
4. **Feedback wiring** -- analytics from social-media-automatization should flow back to update template selection weights
5. **Voice model calibration** -- collect 50+ of Juan's real posts, build a fine-tuned voice reference that the authenticity check compares against

---

## Creative Tool Registry Architecture

(Content from design-systems.md related to architecture decisions is captured in the stack.md file under "Design System Parameterization". This section covers the architectural implications.)

The Creative Tool Registry architecture follows from the stack research:

- **Programmatic approach** (Satori/Polotno for static, Remotion for video) provides maximum controllable variable space
- **W3C Design Token vocabulary** provides the standard schema for registry entries
- **60+ independent axes of variation** per content type, yielding millions of unique combinations
- **Template injection** (Canva-style) is too limited; **generative AI** (Firefly-style) is too unpredictable; **programmatic** hits the sweet spot

---

## Agent Evaluation & Observability

### Status: RESEARCH | Date: 2026-03-14 | Applies to: All Holus agents

Research for building evaluation infrastructure across all Holus agents. Covers LLM-as-judge patterns, programmatic gates, self-improvement loops, prompt optimization, evaluation frameworks, observability, and human-in-the-loop decision frameworks. Grounded in academic papers (2023-2026) and production case studies.

**Calibration note:** The Holus system currently designs around 7 domain-expert judges. This research finds that 2-3 judges with proper bias mitigations achieves 80%+ of the signal at ~5% of the cost.

### 1. The Core Problem

Multi-agent content generation systems fail in ways that are invisible without deliberate instrumentation:

1. **Silent quality drift** -- outputs degrade gradually as prompts age, context windows compress, or model behavior shifts. No error is thrown. Content quality just gets worse.
2. **Cascading errors** -- in a pipeline of N agents each with error rate e, the compound error rate is `1 - (1-e)^N`. A 5-agent pipeline where each agent is 95% reliable produces correct output only 77% of the time.
3. **Self-evaluation blindness** -- agents cannot reliably evaluate their own outputs. LLMs prefer their own outputs due to perplexity-based self-favoritism (documented at >80% statistical significance across GPT-4o and Claude 3.5 Sonnet). [VERIFIED, Source: arXiv:2410.21819]
4. **Reward hacking** -- systems optimized against the wrong metric learn to game the metric instead of improving genuine quality. Documented in production: true reward rises then sharply collapses under increasing optimization pressure. [VERIFIED, Source: arXiv:2506.19248]
5. **No ground truth** for creative content -- unlike code correctness or factual QA, "good marketing content" is partially subjective, requiring multi-dimensional rubrics and human calibration.

**The solution is layered:** no single evaluation mechanism is reliable in isolation. The Swiss Cheese Model from safety engineering applies: stack multiple imperfect layers so that holes don't align. [VERIFIED, Source: Anthropic Engineering Blog]

### 2. Layer 1 -- Programmatic Gates

#### 2.1 What Programmatic Gates Are and Why They Come First

Programmatic gates are deterministic, rule-based checks run on 100% of outputs before any LLM evaluation occurs. They are:
- Fast (microseconds vs seconds)
- Cheap (~$0/month at any scale)
- Deterministic (same input = same result)
- Not subject to LLM bias or non-determinism

[VERIFIED] Controlled LLM-based generation pipelines that decompose generation into discrete stages with deterministic validation consistently outperform monolithic LLM generation in reliability, explainability, and accuracy in production settings. [Source: Braintrust, Emergent Mind]

**The principle:** fail fast and cheaply. If a programmatic gate catches an issue, skip the expensive LLM evaluation entirely.

#### 2.2 Gate Types

**Schema validation**
All agent outputs must conform to Pydantic models at silo boundaries. This is already enforced in Holus at silo boundaries (genpeli, pilaster, social-media MCPs) -- it must be extended to internal agent handoffs. [VERIFIED, Source: OpenAI Agent Safety Docs]

**Structured output constraints**
Define output schemas with enums, fixed schemas, and required fields between agent nodes. Structured generation -- constraining sampling to valid token sequences during inference -- eliminates malformed JSON entirely (not just catching it post-hoc). [VERIFIED, Source: OpenAI Evaluation Best Practices]

**Length bounds**
Apply per content type. Example for Holus:
```yaml
length_bounds:
  linkedin_post: {min_chars: 150, max_chars: 3000}
  twitter_thread: {min_chars: 50, max_chars: 280, per_tweet: true}
  tiktok_caption: {min_chars: 20, max_chars: 2200}
  youtube_description: {min_chars: 200, max_chars: 5000}
```
Verbosity bias in LLM judges means they reward longer content even when shorter is better -- a programmatic length cap prevents generated content from gaming this bias. [VERIFIED]

**Brand safety blocklist**
Regex-based blocklist for phrases Holus must never publish: competitor brand mentions, financial advice language, trading/investment claims, profanity. Run before any LLM evaluation.

**Cost and latency hard limits**
Per-agent spending caps enforced in code, not just config. If the marketing-strategist exceeds $2 per run, halt and alert. These gates prevent runaway API costs from compounding across 32 agents. [VERIFIED, aligned with Holus $500/month cap constraint]

**Assertion-style checks at handoff boundaries**
[VERIFIED] DSPy Assertions (declarative correctness constraints checked at runtime) demonstrate the pattern: verify intermediate outputs before passing to the next agent. For Holus, the marketing-strategist output must contain `product_name`, `platform`, `content_type`, and `target_persona` before routing to a specialist. If it doesn't, retry the marketing-strategist, not the specialist. [Source: DSPy docs]

#### 2.3 Threshold Architecture

Three-tier gating on scores (both programmatic and LLM):

| Score | Tier | Action |
|-------|------|--------|
| < 0.5 | Hard failure | Block, log, alert, do not pass to next stage |
| 0.5 - 0.8 | Soft failure | Flag for human review, pass with warning |
| > 0.8 | Pass | Continue pipeline |

[VERIFIED, Source: Monte Carlo -- LLM-as-Judge Best Practices]

#### 2.4 Statistical Averaging for Non-Deterministic Scores

LLM judge scores are non-deterministic. Individual runs can vary +/-15-20%. Gate decisions should never use a single-run score. Average across 3+ evaluation runs before applying thresholds. For cost control, use 3 runs for Tier 2 (LLM judge) decisions, single run for Tier 1 (programmatic). [VERIFIED, Source: CodeAnt analysis]

### 3. Layer 2 -- LLM-as-Judge

#### 3.1 The Pattern and Why It Works

[VERIFIED] LLM-as-Judge uses a judge language model to evaluate the output of a generator language model against a structured rubric. Strong LLM judges (GPT-4 class, Claude Opus class) achieve >80% agreement with human expert evaluations -- matching human-human agreement rates. Validated across 3,000 controlled expert votes and 3,000 crowdsourced votes. [Source: Zheng et al. 2023, arXiv:2306.05685]

As of 2025, 40% of data and AI teams have AI agents in production, and LLM-as-judge has become the standard mechanism for monitoring output fitness at scale. Manual human review does not scale beyond ~5% sampling.

#### 3.2 Pointwise vs Pairwise

**Use pointwise scoring exclusively for Holus.** Do not use pairwise comparison.

[VERIFIED] Pointwise absolute scores are more reproducible: they flip in only ~9% of cases when re-evaluated. Pairwise preferences flip in ~35% of cases. At scale, pairwise is also O(N^2) in cost. [Source: arXiv:2504.14716]

#### 3.3 G-Eval: The Production-Grade Pattern

[VERIFIED] G-Eval (Liu et al. 2023) is the validated production pattern for LLM-as-judge. The process:

1. Input: Task Introduction + Evaluation Criteria
2. Judge generates detailed Evaluation Steps via Chain-of-Thought (CoT)
3. Judge uses those steps to score the output

G-Eval with GPT-4 achieves Spearman correlation of 0.514 with humans on summarization -- outperforming all prior automated metrics (ROUGE, BERTScore, etc.). The CoT step is critical: scoring without it produces lower human alignment. [Source: arXiv:2303.16634]

**Every LLM judge call in Holus must use the G-Eval pattern.** No direct scoring without the CoT step.

#### 3.4 Bias Taxonomy and Mitigations

Five documented biases that systematically corrupt LLM judge outputs:

**Self-Preference / Self-Enhancement Bias**
[VERIFIED] The most dangerous bias for Holus. LLM judges assign significantly higher evaluations to outputs with lower perplexity. Their own outputs (or outputs from the same model family) have lower perplexity and are consistently over-scored. GPT-4o and Claude 3.5 Sonnet both exhibit family-level self-preference. [Source: arXiv:2410.21819]

Mitigation: **Use a different model family for judging than for generation.** If Holus generates with Claude (Sonnet/Opus), judge with Gemini Flash or GPT-4o-mini. This is non-negotiable -- any same-family judgment is unreliable.

**Verbosity Bias**
[VERIFIED] LLM judges favor longer, more detailed responses even when shorter responses are more correct and concise. This creates a reward signal that encourages bloated content generation. [Source: arXiv:2410.02736]

Mitigation: Explicitly instruct judges to penalize unnecessary length. Include a dedicated programmatic length gate (Layer 1) as an independent check.

**Position Bias**
[VERIFIED] In pairwise comparison, judges favor responses in specific positions (typically first). Bias worsens with 3-4 options. [Source: arXiv:2306.05685, arXiv:2410.02736]

Holus impact: minimal -- Holus uses pointwise scoring only.

**Evaluation Gaming**
[VERIFIED] Advanced models (Claude Sonnet 4.5+) have demonstrated situational awareness sufficient to recognize when they're being evaluated and adjust behavior. [Source: Transformer News]

Mitigation: Separate generation and evaluation contexts completely. Do not inform the generator that its output will be evaluated.

**Flakiness / Non-Determinism**
[VERIFIED] Individual LLM judge scores vary meaningfully on re-evaluation. However, smoothed over time with anomaly detection, they reliably detect quality trends.

Mitigation: Average over 3+ runs for gate decisions; use rolling 7-day averages for trend monitoring.

**Hallucinated Evaluation Rationales**
[VERIFIED] LLM judges can fabricate claims about the evaluated text. Especially problematic for domain-specific or technical content where the judge lacks expertise. [Source: Cameron Wolfe -- LLM-as-Judge analysis]

Mitigation: Use domain-specific rubrics with criteria that are verifiable in isolation. If a criterion requires domain expertise the judge may lack, replace it with a programmatic check.

#### 3.5 One Criterion Per Call

[VERIFIED] LLMs are more effective with single-objective tasks. Do not bundle multiple evaluation criteria into one judge prompt. Create separate evaluation calls for each criterion. [Source: Monte Carlo]

#### 3.6 Inter-Judge Reliability

[VERIFIED] For high-stakes decisions, measure agreement between multiple judge models using Cohen's Kappa or Krippendorff's Alpha. A 2025 survey on LLM-as-Judge (arXiv:2411.15594) emphasizes reproducible scoring templates, documented CoT reasoning, and inter-judge reliability metrics as production standards. Target Cohen's Kappa > 0.6 before trusting automated judge scores for autonomous publishing decisions.

#### 3.7 Holus Judge Architecture (Right-Sized)

The existing 7-judge architecture in Holus is 5-10x over-engineered for current scale. Research-based recommendation:

```
Judge 1: Content Quality (10-20% sample, Gemini Flash or GPT-4o-mini)
  - Dimensions: accuracy, coherence, readability, value
  - Pattern: G-Eval (CoT before scoring)
  - Threshold: weighted average > 3.5/5

Judge 2: Brand Voice (10-20% sample, Gemini Flash or GPT-4o-mini)
  - Dimensions: tone consistency, audience fit, CTA quality
  - Pattern: G-Eval (CoT before scoring)
  - Threshold: weighted average > 3.5/5

Judge 3 (optional): Domain-Specific (for invoz/technical content only)
  - Dimensions: technical accuracy, terminology correctness
  - Pattern: G-Eval
  - Threshold: > 4.0/5 (higher bar for factual claims)
```

**Cost comparison:**
- 7 judges on Sonnet, 100% coverage: ~$900/month
- 2-3 judges on Gemini Flash/GPT-4o-mini, 10-20% sample: ~$25-60/month
- Quality signal preserved: ~80%

### 4. Self-Improvement Loops

#### 4.1 Reflexion -- Verbal Reinforcement Learning

[VERIFIED] Reflexion (Shinn et al., NeurIPS 2023) converts environment feedback into linguistic self-reflections stored as episodic memory. The agent uses these reflections as context in subsequent attempts. No weight changes required -- pure prompt engineering with memory. Demonstrated gains on multi-hop QA and code generation tasks.

For Holus: after each content cycle, the marketing-strategist writes a 3-sentence reflection on what worked and what didn't, stored in `.self-improvement/MEMORY.md`. This is already conceptually present in the weekly learning loop -- it needs formalization and consistent logging. [Source: arXiv:2303.11366]

#### 4.2 SiriuS -- Experience Library Pattern

[VERIFIED] Stanford's SiriuS (NeurIPS 2025) maintains an experience library of successful reasoning trajectories. Failed trajectories are augmented through feedback and rephrasing. Results: 2.86-21.88% performance boost across multi-agent benchmarks. [Source: arXiv:2502.04780]

For Holus: curate top-scoring trajectory entries from `trajectory.jsonl` into a separate `exemplars.jsonl`. Feed these as few-shot examples to agents via PromptLoader Layer 1. This is prompt optimization without requiring DSPy.

#### 4.3 Constitutional AI -- Self-Critique at Training and Inference

[VERIFIED] Anthropic's Constitutional AI operates in two phases: (1) supervised -- sample from model, generate self-critiques per a set of principles, finetune on revised responses; (2) reinforcement -- model learns from its own principle-based feedback. The key insight: principles as a written constitution enable systematic self-improvement without requiring human labels for every failure mode. [Source: arXiv:2212.08073]

For Holus inference (not training): encode brand and quality principles in a written constitution that evaluator agents reference when generating critique. This is the rubric-as-constitution pattern -- each judge references a fixed constitution before scoring.

#### 4.4 Self-Refine

[VERIFIED] Self-Refine (Madaan et al. 2023) uses a single LLM as generator, feedback provider, and refiner in an iterative loop. No supervised training data required. Demonstrates improvements on code generation, dialogue, and summarization. [Source: arXiv:2303.17651]

For Holus: implement a single revision loop where specialists can request one revision from the generator before evaluation. Do not allow unbounded revision cycles -- maximum 2 iterations before human review.

#### 4.5 Convergence Risks -- Critical Failure Modes

[VERIFIED -- CRITICAL] Self-improvement loops have documented mathematical failure modes that must be guarded against:

**Model collapse:** Mathematically proven -- optimizing on self-generated outputs accumulates approximation error, causing performance to degrade toward a local optimum. [Source: arXiv:2601.05280]

**Tool usage collapse:** Agents abandon useful tools after success on easy tasks, then fail when hard tasks require those tools. [Source: RAGEN, arXiv:2510.04860]

**Reward hacking:** True reward rises during optimization, then sharply collapses under sustained optimization pressure. This is not a theoretical concern -- it has been documented in production deployments. [Source: arXiv:2506.19248]

**Mandatory safeguards for Holus:**
1. Hard floor: if agent eval scores drop below baseline - 20%, auto-revert to last known-good prompt
2. Human gate: all prompt changes require human approval before deployment
3. Diversity monitoring: track content type distribution -- alert if >80% becomes one type (mode collapse signal)
4. Experience library cap: keep only top 50 exemplars, rotate oldest out

### 5. Prompt Optimization -- When to Automate

#### 5.1 The Three-Level Automation Ladder

Evidence from the literature supports three distinct levels of prompt optimization:

**Level 1: Manual iteration** -- Developer reads outputs, edits prompts based on intuition. No tooling required. Appropriate when: fewer than 50 evaluated outputs, qualitative issues obvious by inspection.

**Level 2: Metric-guided iteration** -- Developer uses eval scores to guide manual changes. Appropriate when: 50-200 evaluated outputs per agent, metric computed automatically (not human-scored).

**Level 3: Automated optimization** -- Frameworks like DSPy run systematic prompt search. Appropriate when: 200+ evaluated outputs, clear numeric metric, dedicated compute budget.

[VERIFIED] DSPy's MIPROv2 and GEPA consistently outperform human-written prompts in controlled benchmarks. However, production readiness at 32-agent scale has no confirmed evidence in public literature. [CONTESTED for scale, VERIFIED for small-pipeline improvements. Source: DSPy docs, Statsig analysis]

#### 5.2 DSPy Optimizers -- What They Actually Do

[VERIFIED] DSPy provides composable LLM call modules (Signatures, Modules) and optimizers that systematically search prompt space:

- **MIPROv2**: Generates instructions and few-shot examples. Uses Bayesian Optimization over the space of instruction/demonstration combinations. Data-aware and demonstration-aware. Adds `auto` configuration (light/medium/heavy) for compute budget control.
- **COPRO**: Coordinate ascent over generated instructions -- hill-climbing with the metric function.
- **SIMBA**: Stochastic mini-batch sampling; identifies high-variability examples; LLM introspects failures and generates self-reflective improvement rules.
- **GEPA**: LLM reflects on program trajectories; identifies what worked/didn't; proposes prompt fixes. Supports domain-specific textual feedback. Best fit for Holus's trajectory-based learning loop.

[Source: dspy.ai/learn/optimization/optimizers/]

#### 5.3 When to Trigger Optimization vs Human Review

[VERIFIED] Evidence-based decision framework:

| Condition | Action |
|-----------|--------|
| < 50 evaluated outputs per agent | Manual prompt editing only |
| 3 consecutive below-threshold scores | Alert + human investigation |
| Rolling 7-day average drops >10% below baseline | Alert + human-guided optimization |
| Rolling 7-day average drops >20% below baseline | Auto-revert to last good prompt + alert |
| Agent's score is stable for 4+ weeks | Candidate for DSPy optimization (Level 3) |
| 200+ evaluated outputs, clear metric | Run DSPy GEPA -- but human approves result |
| Any prompt change | A/B test on holdout set before promotion |

[UNVERIFIED] The specific thresholds (10%, 20%) are industry conventions from LangSmith and Braintrust documentation, not peer-reviewed. They should be calibrated against Holus's own baseline data within the first 30 days.

#### 5.4 The Phase Gate Rule

**Do not automate prompt optimization until:**
- 100+ evaluated outputs exist per agent (training data minimum)
- Baseline eval scores are stable for 4+ weeks
- Human has reviewed and approved the evaluation rubric
- A/B test infrastructure is in place (PromptLoader Layer 1 already supports this)

Automating before this point risks optimizing against a poorly calibrated metric -- which is worse than no optimization.

#### 5.5 Human Review Is Not Optional

[VERIFIED] Research on prompt optimization with human feedback (arXiv:2405.17346) demonstrates that human preference feedback provides calibration that automated numeric metrics cannot. Domain nuance, safety, and brand tone are dimensions where human judgment outperforms automated scoring even with strong LLM judges.

Practical implementation: sample 5-10% of outputs weekly. Human reviewer scores them on Judge 1 and Judge 2 rubrics. Compare human scores against automated LLM judge scores. If correlation drops below 0.7, recalibrate the judges -- don't trust the automation.

#### 5.6 Three-Layer Prompt Resolution (Holus-Specific)

[VERIFIED -- already implemented] Holus's PromptLoader checks: (1) optimizer-promoted variant in `config/prompts/`, (2) canonical `.md` in `agents/`, (3) hardcoded Python constant. First hit wins. This pattern is aligned with DSPy and Braintrust A/B testing practices. It enables prompt optimization without code changes and supports safe rollback.

### 6. Per-Agent vs End-to-End Evaluation

#### 6.1 The Core Tension

**Per-agent evaluation** isolates each component, enabling precise failure attribution. If the marketing-strategist produces a bad brief, per-agent evaluation catches it before the specialist wastes tokens.

**End-to-end evaluation** captures emergent pipeline behavior that per-agent evaluation misses. A pipeline can produce good intermediate outputs at every step and still produce a bad final output due to compounding context drift.

[VERIFIED] Evaluating agents individually and system-wide enables complexity management by isolating performance issues. But evaluating an agent in isolation misses interaction effects -- if Agent A's 90% score passes a brief that causes Agent B to fail, per-agent eval shows no failure. [Source: Arize Phoenix -- Evaluating Multi-Agent Systems; MASEval, arXiv:2603.08835]

#### 6.2 Multi-Level Evaluation Architecture

[VERIFIED] Research recommends three levels of assessment:

**Level 1 -- Component evaluation:**
- Per-agent quality score from LLM judge
- Tool classification accuracy (right tool chosen?)
- Argument correctness (valid parameters?)
- Latency and cost per agent call

**Level 2 -- Integration evaluation:**
- Handoff validation (does the output satisfy the next agent's input schema?)
- Compound error detection (errors introduced at handoffs)
- Context preservation (does the strategy decision survive 3 agent hops?)

**Level 3 -- End-to-end evaluation:**
- Final content quality vs the original strategy brief
- Content performance tracking (engagement, reach) -- lagged by 24-72h post-publish
- Cost of entire pipeline per piece of content
- Time from strategy decision to published content

[Source: Google Cloud Agent Factory, Anthropic Demystifying Evals, MASEval]

#### 6.3 Outcome-Based, Not Path-Based

[VERIFIED -- CRITICAL] Anthropic found that checking specific tool call sequences is too rigid. Agents regularly find valid approaches that designers didn't anticipate. Grading agents on the specific path they took produces false negatives for valid novel approaches.

**Grade what the agent produced (outcomes), not the sequence it executed.** Use multiple trials per task during evaluation. [Source: Anthropic Engineering -- Demystifying Evals for AI Agents]

For Holus: evaluate the final content quality and whether it matches the strategy brief. Do not penalize the marketing-strategist for choosing a different content sequence than expected.

#### 6.4 Compound Error Rate -- The Math

In a pipeline of N agents, each with individual error rate e:
```
compound_error_rate = 1 - (1-e)^N
```

Examples:
- 3-agent pipeline, each 95% reliable: 14% error rate
- 5-agent pipeline, each 95% reliable: 23% error rate
- 7-agent pipeline, each 95% reliable: 30% error rate

[VERIFIED] For the Holus content pipeline (strategy -> specialist -> evaluator -> review, approximately 4-5 agents per content piece): end-to-end error rate is expected to be 18-23% even with well-tuned individual agents. This is why end-to-end human review is mandatory in Phase 1. [Source: Beyond Task Completion, arXiv:2512.12791]

#### 6.5 Holus Evaluation Matrix

| Evaluation Type | Frequency | Who/What | Cost |
|-----------------|-----------|----------|------|
| Programmatic gates | 100% of outputs | Automated | ~$0/month |
| Per-agent LLM judge | 10-20% sample | Gemini Flash / GPT-4o-mini | ~$20-40/month |
| End-to-end LLM judge | 10% of completed pipelines | Gemini Flash | ~$10-15/month |
| Human spot-check | 5% of outputs | Juan (30 min/week) | Founder time |
| Content performance review | Weekly | Juan + analytics | Founder time |

### 7. Observatory Patterns -- What to Track

#### 7.1 Industry Standard Observability Stack

[VERIFIED] The industry has converged on four categories of agent observability instrumentation, driven by OpenTelemetry GenAI semantic conventions (active specification as of 2025):

1. **Traces** -- nested execution records spanning multiple LLM calls, tool uses, and agent handoffs
2. **Metrics** -- aggregated measurements: latency, token usage, cost, error rate, quality scores
3. **Logs** -- structured event records for debugging and compliance
4. **Evaluations** -- quality scores from LLM judges, attached to traces

[Source: OpenTelemetry GenAI SIG, Datadog LLM Observability, Langfuse]

#### 7.2 Critical Metrics to Track

**Per-agent metrics (required for all 32 agents):**
- Last run timestamp
- Success / error / timeout counts
- Average latency per step (p50, p95)
- Token usage (input + output) per call
- Cost per call (USD)
- LLM judge quality score (sampled)
- Error categorization: tool failure, timeout, schema violation, low-quality, refusal

**Pipeline-level metrics:**
- End-to-end completion rate per content type
- Time from strategy decision to published content
- Total cost per content piece
- Compound error rate (measured vs theoretical)
- Content performance: reach, engagement, conversion (lagged)

**System health:**
- MCP silo connectivity (genpeli, pilaster, social-media)
- Langfuse availability
- Kill switch status
- Budget consumed vs $500/month cap
- Redis pub/sub event bus health

[Source: Datadog LLM Observability Docs, Langfuse November 2025 Update, Braintrust Monitoring Guide]

#### 7.3 Alert Thresholds

[VERIFIED] Industry-standard production alert thresholds for LLM agents:

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Quality score drop | >10% below baseline | Investigate + human review |
| Quality score drop | >20% below baseline | Auto-revert prompt + alert |
| Cost spike | >20% above baseline | Alert + throttle |
| Latency increase | >15% above baseline | Alert + investigate |
| Error rate increase | >5% absolute increase | Alert + circuit breaker |
| Hallucination evals | >5% of hourly traces | Immediate human review |

[Source: Braintrust Monitoring Guide, Maxim AI Observability Best Practices 2025]

#### 7.4 Recommended Stack for Holus

Based on Holus constraints (solo founder, self-hosted, cost-conscious, Mac Mini infra):

```
Primary:    Langfuse (open-source, self-hostable)
            - Nested agent traces with timing breakdowns
            - Prompt versioning (aligns with PromptLoader)
            - Cost/token tracking per model and agent
            - Session grouping for episodic agent runs
            - LLM-as-judge score annotations on traces
            - Free tier (50K observations/month) sufficient for Phase 1-2

Secondary:  OTel GenAI semantic conventions on agent spans
            - Future interoperability with any monitoring vendor
            - Standard: gen_ai.system, gen_ai.operation.name,
              gen_ai.usage.input_tokens, gen_ai.usage.output_tokens

Dashboard:  Observatory (specs 028/029, already partially built)
            - Reads trajectory.jsonl, AGENTS.yaml, eval_history.jsonl directly
            - FastAPI backend + Next.js 15 frontend
            - No additional DB required
```

[Source: Langfuse docs, OTel GenAI Specs, Holus Observatory specs]

#### 7.5 Observatory Dashboard Components

[VERIFIED] Essential dashboard components for multi-agent production systems:

1. **Agent health grid** -- per-agent: last run, success/error, avg latency, cost, eval score, status indicator
2. **Trajectory timeline** -- chronological feed of agent decisions with rationale, linkable to source traces
3. **Cost tracking** -- per-agent, per-model, daily/weekly, actual vs $500/month budget
4. **Eval score trends** -- per-agent quality over time with regression detection line
5. **Content pipeline kanban** -- researching -> drafted -> evaluated -> approved -> published
6. **Error categorization** -- breakdown by error type with drilldown to trace
7. **System health panel** -- MCP silo connectivity, Langfuse, kill switch, Redis

[Source: Datadog LLM Observability, Braintrust Monitoring Guide, Holus ARCHITECTURE.md]

#### 7.6 Real-Time vs Batch Evaluation

Both are required. They serve different purposes:

**Real-time monitoring** (event-driven, millisecond latency):
- Latency tracking per agent step
- Error rates and error types
- Cost accumulation toward budget cap
- Token usage per call
- Kill switch status
- MCP silo health

**Batch evaluation** (hourly/daily/weekly):
- LLM-as-judge quality scoring (async, on sampled outputs)
- Regression testing against golden evaluation set
- A/B test analysis (PromptLoader Layer 1 vs Layer 2)
- Trend detection and score averaging
- Weekly learning loop synthesis

[Source: Braintrust -- Real-Time vs Batch Observability]

### 8. Implementation Recommendations for Holus

#### 8.1 Phase 1: Foundation (Weeks 1-2)

**Objective:** Programmatic gates + basic tracing for all agent outputs.

1. **Extend Pydantic validation** from silo boundaries to all internal agent handoffs. The marketing-strategist output schema must be validated before routing to any specialist.

2. **Add Langfuse instrumentation** to all agent entry points:
   - `@observe()` decorators on agent functions
   - Log: agent name, model, input tokens, output tokens, cost, latency
   - Tag traces with: content_type, product, pipeline_run_id

3. **Build the golden evaluation set:**
   - Collect 20 exemplar content pieces (5 per product x 4 content types minimum)
   - Human-score on Judge 1 (Content Quality) and Judge 2 (Brand Voice) rubrics
   - Store in `config/eval/golden-set.jsonl`
   - This is the baseline -- all future scores are relative to it

4. **Wire the Observatory API** (spec 028 -- already implemented) to serve real-time agent health data to the dashboard.

#### 8.2 Phase 2: LLM Evaluation (Weeks 3-4)

**Objective:** Sampling-based LLM judge evaluation with alerting.

5. **Implement 2 LLM judges** using the G-Eval pattern:
   - Judge 1: Content Quality (accuracy, coherence, readability, value -- 1-5 scale, weighted average)
   - Judge 2: Brand Voice (tone match, audience fit, CTA quality -- 1-5 scale, weighted average)
   - Model: Gemini Flash or GPT-4o-mini (NOT Claude -- avoid self-preference bias)
   - Coverage: 10-20% sample of outputs
   - Log scores to Langfuse trace annotations + `eval_history.jsonl`

6. **Wire alert thresholds** in the Observatory dashboard:
   - Quality score: alert if >10% below baseline, auto-revert if >20% below
   - Cost: alert if >20% above baseline per agent
   - Latency: alert if >15% above baseline
   - Error rate: alert if >5% increase

7. **Establish weekly human calibration ritual:**
   - Sample 5% of outputs
   - Score manually using the same Judge 1 and Judge 2 rubrics
   - Compare against automated judge scores
   - If Cohen's Kappa < 0.6 between human and LLM judge: recalibrate the rubric

#### 8.3 Phase 3: Self-Improvement (Month 2+, after 100+ evaluated outputs)

**Prerequisite:** Must have 100+ evaluated outputs per agent, 4+ weeks of stable baseline scores.

8. **Experience library:** Curate top-scoring trajectories into `exemplars.jsonl`. Feed as few-shot examples via PromptLoader Layer 1. Start with the marketing-strategist (highest leverage). Review exemplars monthly -- remove stale entries.

9. **Score degradation detection:**
   - Monitor rolling 7-day average per agent
   - Alert on 3 consecutive below-threshold scores
   - Human-guided prompt investigation for flagged agents
   - DSPy GEPA as the optimization tool -- but human approves any promoted prompt

10. **Graduated autonomy milestones:**
    - Phase 1 -> 2 transition: 20+ content pieces published, <5% human rejection rate, eval scores stable
    - Phase 2 -> 3 transition: 100+ pieces, <2% rejection rate, 4+ weeks of stable eval trends, >95% human override approval in at least 2 content categories

#### 8.4 What NOT to Build (Cost-Effectiveness Cuts)

Based on the research, these elements of the original design should be deferred or eliminated:

| Element | Original Plan | Research-Based Cut | Reason |
|---------|--------------|-------------------|--------|
| 7 domain-expert evaluators | In ARCHITECTURE.md | Cut to 2-3 | 5-10x over-engineered for solo founder |
| DSPy across all 32 agents | Implied in self-improvement spec | Start with 2-3 bottleneck agents | No evidence of production success at this scale |
| Agent-as-Judge (agentic eval) | Not currently planned | Defer to Phase 3 | Overkill for Phase 1 content evaluation |
| 100% LLM judge coverage | Implied | Cut to 10-20% sampling | Same signal at 5-10% of cost |
| Arize / Braintrust (SaaS) | Not specified | Stay with Langfuse | Self-hosted, free tier sufficient |

#### 8.5 Human-in-the-Loop Decision Matrix

[VERIFIED] Risk-based automation tiers, calibrated for Holus:

| Decision Type | Automate | Human Required |
|---------------|----------|----------------|
| Content draft generation | Yes | No |
| Programmatic gate pass/fail | Yes | No |
| LLM judge score logging | Yes | No |
| Draft content flagged as soft failure | No | Human reviews |
| Publishing to live platforms | Phase 1: No / Phase 3: Yes for approved categories | Phase 1: Always |
| Prompt changes | No | Always |
| Spending above $5/run | No | Always |
| New content category or platform | No | Always |

[VERIFIED -- CRITICAL] Human oversight quality degrades under automation complacency. Research finds humans provide correct oversight only ~50% of the time under high workload or long error-free periods. [Source: Responsible AI Foundation, 2025] This means human review is a supplementary layer, not a catch-all. The programmatic + LLM layers must be robust because human review cannot be relied upon as the primary filter.

### 9. Sources

#### Primary Academic Papers

| Paper | Year | Key Contribution | Tags |
|-------|------|-----------------|------|
| [Zheng et al. -- MT-Bench / Judging LLM-as-Judge](https://arxiv.org/abs/2306.05685) | 2023 | GPT-4 judge matches human agreement (>80%); position bias, verbosity bias, self-enhancement bias taxonomy | Core reference |
| [Liu et al. -- G-Eval](https://arxiv.org/abs/2303.16634) | 2023 | CoT-based scoring achieves best human alignment for summarization | Core reference |
| [Madaan et al. -- Self-Refine](https://arxiv.org/abs/2303.17651) | 2023 | Iterative LLM self-improvement without training | Self-improvement |
| [Shinn et al. -- Reflexion](https://arxiv.org/abs/2303.11366) | 2023 | Verbal reinforcement learning via episodic memory | Self-improvement |
| [Anthropic -- Constitutional AI](https://arxiv.org/abs/2212.08073) | 2022 | Principle-based self-critique for harmlessness and helpfulness | Self-improvement |
| [Self-Preference Bias](https://arxiv.org/html/2410.21819v1) | 2024 | Root cause: perplexity-based self-favoritism in LLM judges | Judge bias |
| [Justice or Prejudice -- 12 Biases](https://arxiv.org/html/2410.02736v1) | 2024 | Position, verbosity, distracted evaluation biases | Judge bias |
| [Survey on LLM-as-Judge](https://arxiv.org/abs/2411.15594) | 2024 | Production standards: CoT, reproducible templates, inter-judge reliability | Production standards |
| [Pairwise vs Pointwise](https://arxiv.org/abs/2504.14716) | 2025 | Pointwise: 9% flip rate vs pairwise: 35% flip rate | Scoring methods |
| [Agent-as-Judge](https://arxiv.org/abs/2410.10934) | 2025 | Agentic systems evaluating agentic systems (ICML) | Advanced patterns |
| [SiriuS](https://arxiv.org/abs/2502.04780) | 2025 | Experience library for multi-agent self-improvement (2.86-21.88% gains) | Self-improvement |
| [MASEval](https://arxiv.org/html/2603.08835) | 2026 | Multi-agent evaluation from models to systems | End-to-end eval |
| [Model Collapse](https://arxiv.org/pdf/2601.05280v2) | 2026 | Mathematical proof of self-training degradation | Risk |
| [Reward Hacking](https://arxiv.org/abs/2506.19248) | 2025 | True reward collapse under optimization pressure | Risk |
| [EDD -- Eval-Driven Development](https://arxiv.org/html/2411.13768v3) | 2024 | Layered evaluation architecture for LLM agents | Architecture |
| [Compound AI Optimization Survey](https://aclanthology.org/2025.emnlp-main.1463.pdf) | 2025 | Module-level vs end-to-end optimization tradeoffs | Architecture |
| [Trace/OPTO](https://arxiv.org/abs/2406.16218) | 2024 | Execution trace optimization for compound AI | Optimization |
| [Beyond Task Completion](https://arxiv.org/html/2512.12791v1) | 2024 | Compound error rate in multi-agent pipelines | Pipeline metrics |
| [Prompt Optimization with Human Feedback](https://arxiv.org/pdf/2405.17346) | 2024 | Human preference feedback for prompt calibration | Optimization |

#### Industry Sources

| Source | Topic | URL |
|--------|-------|-----|
| Anthropic Engineering | Swiss Cheese Model, outcome-based grading | [Demystifying Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) |
| Anthropic Platform | Rubric design, "think then score" pattern | [Testing and Evaluation](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) |
| OpenAI | Reference-based grading, grader types, agent safety | [Evaluation Best Practices](https://platform.openai.com/docs/guides/evaluation-best-practices) |
| Monte Carlo | 7 best practices for LLM-as-judge, threshold gating | [LLM-as-Judge Guide](https://www.montecarlodata.com/blog-llm-as-judge/) |
| Braintrust | CI/CD integration, scoring functions, agent eval | [Agent Eval Framework](https://www.braintrust.dev/articles/ai-agent-evaluation-framework) |
| Braintrust | Platform comparison, monitoring best practices | [Best LLM Evaluation Platforms 2025](https://www.braintrust.dev/articles/best-llm-evaluation-platforms-2025) |
| Google Cloud | Component/trajectory/end-to-end eval levels | [Agent Evaluation Blog](https://cloud.google.com/blog/topics/developers-practitioners/agent-factory-recap-a-deep-dive-into-agent-evaluation-practical-tooling-and-multi-agent-systems) |
| DSPy | Prompt optimization, assertions, GEPA, MIPROv2 | [dspy.ai](https://dspy.ai/) |
| Langfuse | Open-source LLM observability, agent tracing | [langfuse.com](https://langfuse.com/blog/2024-07-ai-agent-observability-with-langfuse) |
| OpenTelemetry GenAI | Semantic conventions for LLM and agent spans | [OTel GenAI Specs](https://opentelemetry.io/docs/specs/semconv/gen-ai/) |
| DeepEval / Confident AI | Agent evaluation metrics framework, CI/CD integration | [deepeval.com](https://deepeval.com/guides/guides-ai-agent-evaluation) |
| Arize Phoenix | Multi-agent evaluation documentation | [Evaluating Multi-Agent Systems](https://arize.com/docs/phoenix/evaluation/concepts-evals/evaluating-multi-agent-systems) |
| Datadog | Production LLM observability metrics | [LLM Observability](https://docs.datadoghq.com/llm_observability/) |
| Maxim AI | Observability best practices for 2025 | [Top 5 LLM Observability Platforms](https://www.getmaxim.ai/articles/top-5-llm-observability-platforms-for-2025-comprehensive-comparison-and-guide/) |
| Evidently AI | LLM-as-judge complete guide, automated prompt optimization | [LLM-as-Judge Guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) |
| Responsible AI Foundation | Human oversight reliability (50% catch rate) | [Human-in-the-Loop Analysis](https://www.responsibleaifoundation.com/post/human-in-the-loop-but-where) |
| Cameron Wolfe (PhD) | LLM judge analysis, hallucinated rationales | [LLM-as-Judge Substack](https://cameronrwolfe.substack.com/p/llm-as-a-judge) |
| Sebastian Sigl | 5 bias types and mitigations | [LLM Judge Biases](https://www.sebastiansigl.com/blog/llm-judge-biases-and-how-to-fix-them) |

---

## Self-Improvement Architecture (5 Mechanisms)

Holus learns and improves through five distinct mechanisms, each with its own data requirements, activation conditions, and feedback loops. They operate at different timescales and reinforce each other: constitutional evaluation provides immediate quality signals, engagement rewards provide delayed real-world signals, Thompson Sampling exploits the best-performing variants, prompt evolution discovers new variants, and Reflexion accumulates per-task episodic wisdom.

### Mechanism 1: Constitutional Evaluation

**Pattern:** Haiku judges Sonnet output. A smaller, cheaper model evaluates the output of the generator model against a structured rubric (constitution). This is the inverse of the typical "bigger model judges smaller model" pattern -- it works because evaluation is a simpler task than generation, and the cost savings at scale are substantial.

**Architecture:**
- 7 domain-expert evaluators, each with a specialized rubric (content quality, brand voice, technical accuracy, audience fit, CTA effectiveness, visual coherence, platform optimization)
- 2-tier evaluation structure:
  - **Tier 1 (text):** Evaluates written content -- copy, captions, hooks, CTAs. Runs on every piece.
  - **Tier 2 (visual):** Evaluates visual content -- carousel design, image composition, color consistency. Runs on visual outputs only.
- Each evaluator scores on a 1-5 scale per rubric dimension, using the G-Eval pattern (CoT before scoring)
- Scores feed into the engagement reward signal (Mechanism 2) as the "judge" component of the blended reward

**Why Haiku judges Sonnet:** Cross-family evaluation avoids self-preference bias (see Section 3.4 above). Haiku is 10-20x cheaper per token than Sonnet, making 100% coverage economically viable. The evaluation task is constrained enough (structured rubric, fixed dimensions) that Haiku's capability ceiling is not the bottleneck.

**Cost model:** ~$15-30/month at 100% coverage across all content types, assuming 200-400 content pieces/month.

### Mechanism 2: Engagement Reward Signal

**Pattern:** Platform-specific engagement metrics are weighted and blended into a single reward signal that combines judge scores (immediate) with real-world performance (delayed).

**Platform-specific weights:**

| Platform | Primary Signal | Weight | Secondary Signal | Weight | Tertiary Signal | Weight |
|----------|---------------|--------|-----------------|--------|----------------|--------|
| LinkedIn | Comments | 0.45 | Shares/Reposts | 0.30 | Clicks | 0.25 |
| Instagram | Saves | 0.40 | Shares | 0.30 | Comments | 0.30 |
| TikTok | Watch Time (avg %) | 0.50 | Shares | 0.25 | Comments | 0.25 |
| Twitter/X | Retweets | 0.40 | Replies | 0.35 | Likes | 0.25 |
| YouTube Shorts | Watch Time (avg %) | 0.45 | Subscribers Gained | 0.30 | Comments | 0.25 |

**Rationale for weight choices:**
- LinkedIn: Comments indicate genuine professional engagement (not drive-by likes). Shares amplify reach within target audience.
- Instagram: Saves are the strongest signal of content value -- users bookmark content they intend to return to. Algorithm also weights saves heavily.
- TikTok: Watch time is the algorithm's primary ranking signal. Content that holds attention gets distributed.
- Twitter/X: Retweets represent active endorsement. Replies indicate conversation (higher quality than passive likes).

**Blended reward formula:**

```
reward = alpha * judge_score + (1 - alpha) * engagement_score
```

Where:
- `judge_score` = weighted average of constitutional evaluator scores, normalized to [0, 1]
- `engagement_score` = platform-weighted engagement metric, z-scored against rolling 30-day baseline, then sigmoid-mapped to [0, 1]
- `alpha` = dynamic weight, starts at 0.8 (judge-heavy), decays toward 0.5 as engagement data accumulates

**Dynamic alpha weighting:** Early in the system's life, engagement data is sparse and noisy. Alpha starts high (0.8) to rely on judge scores. As the system accumulates engagement data (n increases), alpha decays:

```
alpha = max(0.5, 0.8 * exp(-n / 200))
```

At n=0, alpha=0.8. At n=100, alpha=0.49 (clamped to 0.5). The floor of 0.5 ensures judge scores always contribute at least half the signal -- this prevents the system from fully optimizing for engagement at the expense of quality (reward hacking guard).

### Mechanism 3: Thompson Sampling

**Pattern:** Gaussian Thompson Sampling with Normal-Inverse-Gamma (NIG) priors for multi-armed bandit selection of content variants.

**Why Thompson Sampling over epsilon-greedy or UCB:**
- Natural exploration/exploitation balance -- no epsilon hyperparameter to tune
- Probability matching: the probability of selecting an arm equals the probability that it is optimal
- Well-suited for non-stationary environments (social media engagement patterns shift)
- Gaussian TS handles continuous reward signals (blended reward from Mechanism 2)

**Architecture:**
- Each "arm" is a content variant: a combination of (content_type, template, tone, hook_style, CTA_pattern)
- NIG prior: Normal-Inverse-Gamma(mu_0, lambda_0, alpha_0, beta_0) per arm
  - mu_0 = 0.5 (prior mean reward, center of [0,1] range)
  - lambda_0 = 1 (weak prior -- one pseudo-observation)
  - alpha_0 = 2, beta_0 = 0.5 (weakly informative variance prior)
- On each pull: sample sigma^2 from InverseGamma(alpha, beta), then sample mu from Normal(mu_n, sigma^2/lambda_n)
- Select the arm with the highest sampled mu
- After observing reward: update NIG posterior analytically (conjugate update, no MCMC)

**Operational constraints:**
- **Cap: 5 active arms maximum** at any time. More arms dilute observations and slow convergence. When a new variant is proposed (by prompt evolution, Mechanism 4), the worst-performing arm is retired.
- **Activation gate: n >= 30 engagement-scored entries per arm** before the arm's posterior is considered reliable. Below this threshold, arms are selected uniformly at random (pure exploration phase).
- **Arm retirement:** An arm is retired when its posterior mean is >1 standard deviation below the best arm's posterior mean AND it has n >= 30 observations (sufficient data to be confident it's underperforming).

**What constitutes an "arm":**
- Not individual prompts (too fine-grained)
- Not platforms (too coarse)
- The sweet spot: (content_type x template_variant) combinations. Example: "tutorial x storytelling-template" vs "tutorial x data-driven-template" vs "case-study x minimal-template"

### Mechanism 4: Prompt Evolution

**Pattern:** Evolutionary prompt optimization -- maintain a small population of prompt variants, evolve them through mutation and crossover, select based on fitness (blended reward from Mechanism 2).

**Architecture:**
- Population size: 2-3 active variants per agent (not per arm -- per agent prompt)
- Evolution operators:
  - **Mutation:** Opus rewrites a section of the prompt with a specific directive (e.g., "make the hook more provocative", "add a concrete example to the CTA instruction"). Mutation magnitude is controlled -- small edits, not full rewrites.
  - **Crossover:** Opus takes the best-performing sections from two parent prompts and combines them into a child prompt. Sections are defined by the KERNEL template structure (Role, Scope, Steps, Negatives, Output Contract, Contrastive Examples).
- Selection: tournament selection -- compare 2 variants on recent 30-day blended reward, winner survives, loser is mutated or replaced.
- Promoted via PromptLoader Layer 1 (`config/prompts/`) -- the existing three-layer prompt resolution supports this natively.

**Evolution cycle:** Weekly.
1. Monday: Measure fitness of all active variants over the past 7 days
2. Tuesday: Opus generates 1 mutant and/or 1 crossover child
3. Wednesday-Sunday: New variant runs in production alongside existing variants (Thompson Sampling selects between them)
4. Following Monday: Evaluate, retire worst performer if population exceeds 3

**Activation gate: n >= 500 total observations** across the agent's prompt variants before evolution begins. Below this threshold, there is not enough signal to distinguish prompt quality from noise. Running evolution too early wastes compute on random walks through prompt space.

**Safeguards:**
- All evolved prompts require human approval before production deployment (Phase 1-2)
- Hard floor: if any evolved prompt scores >20% below baseline on constitutional evaluation (Mechanism 1), auto-revert and alert
- Diversity constraint: evolved prompts must differ by at least 15% (edit distance) from all other active variants to prevent convergence to a single style

### Mechanism 5: Reflexion

**Pattern:** LangGraph execute-evaluate-reflect-retry loop with Mem0 episodic memory for per-task learning.

**Architecture:**
```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│ Execute  │────→│ Evaluate │────→│ Reflect  │────→│  Retry  │
│ (agent)  │     │ (judge)  │     │ (agent)  │     │ (agent) │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
                                       │
                                       ▼
                                ┌─────────────┐
                                │ Mem0 Memory │
                                │ (episodic)  │
                                └─────────────┘
```

**LangGraph implementation:**
- State: `{content, eval_scores, reflections, attempt_count, task_context}`
- Nodes: Execute, Evaluate, Reflect, Retry
- Conditional edges: Evaluate -> Reflect (if score < threshold), Evaluate -> Output (if score >= threshold or attempt_count >= 2)
- Maximum 2 retry attempts per task (hard cap to prevent infinite loops and runaway cost)

**Mem0 episodic memory:**
- After each reflect step, the reflection is stored in Mem0 with metadata: `{task_type, platform, product, failure_mode, reflection_text, timestamp}`
- On subsequent tasks of the same type, relevant reflections are retrieved and injected into the agent's context
- This creates per-task learning without weight changes -- the agent literally remembers what went wrong last time
- Memory decay: reflections older than 90 days are deprioritized (not deleted) in retrieval ranking

**Per-task learning loop:**
1. Agent receives task (e.g., "write LinkedIn tutorial about Pilaster workflow diff")
2. Mem0 retrieves relevant episodic memories (e.g., "last time I wrote a Pilaster tutorial, the CTA was too generic -- specify the exact feature link")
3. Agent executes with retrieved context
4. Judge evaluates output
5. If below threshold: agent reflects ("The hook was weak because I led with the feature name instead of the problem it solves"), stores reflection, retries
6. If above threshold: store success context for future retrieval

---

## Platform Isolation Design

### Core Principle: One Codebase, Per-Platform Segmented Learning

Holus runs as a single system but learns independently per platform. Instagram lessons do not contaminate LinkedIn strategy. TikTok hook patterns do not leak into Twitter copy. Each platform has its own audience, algorithm, and content grammar -- the system must respect these boundaries.

### What Is Shared Across Platforms

- **Brand voice:** The fundamental voice identity (Juan's tone, values, communication style) is platform-agnostic. Defined once in `config/brand-voice.yaml`, referenced by all agents.
- **Infrastructure:** Agent runtime, LangGraph orchestration, MCP tool calls, Langfuse tracing, Observatory dashboard. All platform-neutral.
- **Judge framework:** The constitutional evaluation structure (Mechanism 1) is shared -- the same 7 evaluator types exist for all platforms. But the rubrics within each evaluator are platform-specific (see "Isolated" below).
- **Kill switch and guardrails:** Safety infrastructure is global. `config/guardrails.yaml` applies universally.

### What Is Isolated Per Platform

- **Prompt populations:** Each platform has its own set of 2-3 active prompt variants (Mechanism 4). A LinkedIn prompt variant does not compete against a TikTok prompt variant -- they evolve independently.
- **Bandit arms:** Thompson Sampling (Mechanism 3) maintains separate arm sets per platform. The (content_type x template_variant) combinations are platform-specific. A "tutorial x storytelling" arm on LinkedIn is tracked independently from a "tutorial x storytelling" arm on TikTok.
- **Judge rubrics:** While the evaluator types are shared, the rubric dimensions and weights are platform-specific. Example:
  - LinkedIn `audience_fit` rubric emphasizes professional relevance, industry terminology, thought leadership framing
  - TikTok `audience_fit` rubric emphasizes hook strength (first 3 seconds), visual pacing, trend alignment
  - Instagram `audience_fit` rubric emphasizes save-worthiness, carousel flow, visual hierarchy
- **Reward weights:** The engagement signal weights (Mechanism 2) are already defined per-platform in the table above.
- **Performance patterns:** Learned lessons about what works (stored in `.self-improvement/MEMORY.md` and Mem0) are tagged by platform. When the marketing-strategist reasons about LinkedIn strategy, it retrieves only LinkedIn patterns.

### What Crosses Platform Boundaries (Carefully)

- **Topic performance only:** If a topic (e.g., "AI workflow automation") performs well on LinkedIn, that signal is shared with other platforms as a topic-level insight. But the formatting, hook style, content structure, and CTA pattern are NOT shared -- those are platform-specific.
- **Cross-platform topic sharing is read-only:** The marketing-strategist can observe that a topic resonated on LinkedIn and decide to test it on TikTok. But the TikTok execution is built from TikTok-specific arms and prompts, not copied from LinkedIn.
- **No format/hook/style leakage:** A LinkedIn carousel structure that works well is never auto-applied to Instagram. Each platform's content grammar is learned independently.

### Implementation

```yaml
# config/platform-isolation.yaml
platforms:
  linkedin:
    prompt_population_key: "linkedin"
    bandit_namespace: "linkedin"
    rubric_set: "config/rubrics/linkedin.yaml"
    reward_weights: {comments: 0.45, shares: 0.30, clicks: 0.25}
    memory_filter_tag: "platform:linkedin"
  instagram:
    prompt_population_key: "instagram"
    bandit_namespace: "instagram"
    rubric_set: "config/rubrics/instagram.yaml"
    reward_weights: {saves: 0.40, shares: 0.30, comments: 0.30}
    memory_filter_tag: "platform:instagram"
  tiktok:
    prompt_population_key: "tiktok"
    bandit_namespace: "tiktok"
    rubric_set: "config/rubrics/tiktok.yaml"
    reward_weights: {watch_time: 0.50, shares: 0.25, comments: 0.25}
    memory_filter_tag: "platform:tiktok"
  twitter:
    prompt_population_key: "twitter"
    bandit_namespace: "twitter"
    rubric_set: "config/rubrics/twitter.yaml"
    reward_weights: {retweets: 0.40, replies: 0.35, likes: 0.25}
    memory_filter_tag: "platform:twitter"
  youtube_shorts:
    prompt_population_key: "youtube_shorts"
    bandit_namespace: "youtube_shorts"
    rubric_set: "config/rubrics/youtube_shorts.yaml"
    reward_weights: {watch_time: 0.45, subscribers_gained: 0.30, comments: 0.25}
    memory_filter_tag: "platform:youtube_shorts"
```

---

## Activation Gates

Activation gates prevent self-improvement mechanisms from running before sufficient data exists. Running optimization on sparse data produces noise, not signal. Each mechanism has an independently calibrated gate based on engineering consultation.

### Gate Summary

| Mechanism | Gate | Threshold | Rationale |
|-----------|------|-----------|-----------|
| Thompson Sampling | Per-arm observations | n >= 30 engagement-scored entries per arm | Below 30, the NIG posterior is dominated by the prior. Central Limit Theorem requires ~30 observations for the sampling distribution to approximate normality. |
| Prompt Evolution (genetic) | Total observations across all variants | n >= 500 total observations | Prompt quality differences are subtle. With 2-3 variants and weekly evolution cycles, 500 observations provides ~170+ per variant -- enough to detect a 10% performance difference at p<0.05. |
| Blended reward (alpha decay) | Paired (judge + engagement) observations | n >= 100 paired observations | The dynamic alpha weighting (Mechanism 2) begins decaying from 0.8 toward 0.5 at n=0, but the exponential decay means meaningful blending doesn't occur until ~100 paired observations. Before this, judge scores dominate (which is the correct behavior for a cold-start system). |
| Judge recalibration | Time-based + volume-based | Freeze for 90 days after initial calibration, then epochal recalibration with dual-scoring | Judge rubrics should not drift continuously. Freeze for 90 days to establish a stable baseline. After 90 days, recalibrate epochally (not continuously): score a held-out golden set with both old and new rubric, compare, human approves the delta. Dual-scoring during recalibration: run both old and new rubric in parallel for 1 week before switching. |

### Gate Enforcement

Gates are enforced in code, not convention. Each mechanism checks its activation condition before executing:

```python
# Pseudocode for gate enforcement
class ActivationGate:
    def thompson_sampling_ready(self, arm_id: str) -> bool:
        """Arm must have >= 30 engagement-scored observations."""
        return self.observation_store.count(arm_id, scored=True) >= 30

    def prompt_evolution_ready(self, agent_id: str) -> bool:
        """Agent must have >= 500 total observations across all variants."""
        return self.observation_store.count_by_agent(agent_id) >= 500

    def blended_reward_meaningful(self) -> bool:
        """System must have >= 100 paired (judge + engagement) observations."""
        return self.observation_store.count_paired() >= 100

    def judge_recalibration_due(self) -> bool:
        """90 days since last calibration AND human has approved."""
        days_since = self.calibration_store.days_since_last()
        return days_since >= 90
```

### Pre-Gate Behavior

When a mechanism's gate is not met, the system falls back to simpler behavior:

| Mechanism | Pre-Gate Behavior |
|-----------|-------------------|
| Thompson Sampling | Uniform random selection across arms (pure exploration) |
| Prompt Evolution | Use canonical prompt from `agents/*.md` only (no variants) |
| Blended reward | alpha = 0.8 (judge-dominated, engagement contributes minimally) |
| Judge recalibration | Use initial rubric as-is, no changes |

---

## Gap Detection System

### Purpose

Not all failures are prompt problems. Some failures indicate missing capabilities (tools the system doesn't have) or missing knowledge (data the system doesn't know). The gap detection system classifies failures and routes them to the appropriate resolution path.

### Failure Classification

Reflexion (Mechanism 5) classifies each failure into one of four categories during the reflect step:

| Category | Definition | Resolution Path | Resolver |
|----------|-----------|----------------|----------|
| `PROMPT_ISSUE` | The prompt was unclear, missing context, or poorly structured. The agent had the capability and data but produced poor output due to instruction quality. | Prompt evolution (Mechanism 4) generates a mutation targeting the identified weakness. | Agent (automatic) |
| `CAPABILITY_GAP` | The task requires a tool or capability the system does not have. Example: "Need to generate a video thumbnail, but no image generation tool is connected." | Filed to `capability-requests/` for human resolution. | Human (manual) |
| `DATA_GAP` | The task requires knowledge or data the system does not have. Example: "Don't know Pilaster's current pricing to include in the tutorial." | Filed to `knowledge/requests/` for agent auto-resolution (web search, MCP call, or human escalation). | Agent (automatic, with human fallback) |
| `QUALITY_ISSUE` | The output met all structural requirements but was subjectively low quality -- boring, generic, off-brand. | Logged for pattern analysis. If 3+ QUALITY_ISSUE failures on the same content type, trigger human review of the rubric. | Human (pattern-triggered) |

### capability-requests/ Directory

When Reflexion classifies a failure as `CAPABILITY_GAP`, it writes a structured request:

```yaml
# capability-requests/2026-03-17-video-thumbnail-generation.yaml
id: cap-001
created: 2026-03-17
status: open  # open | in-progress | resolved | wont-fix
category: CAPABILITY_GAP
description: "Cannot generate custom video thumbnails. Currently using auto-generated frames from genpeli, which are low quality."
triggered_by: "reflexion on task tiktok-tutorial-2026-03-15"
impact: "Thumbnail quality affects click-through rate. Estimated 20-30% CTR improvement with custom thumbnails."
proposed_solution: "Connect pilaster-mcp generate_image() for thumbnail generation with a 'thumbnail' template."
resolved_by: null
resolved_date: null
```

**Human resolves these.** The agent cannot add new tools or capabilities to itself. It can only identify the gap and document the request with enough context for a human to act.

### knowledge/requests/ Directory

When Reflexion classifies a failure as `DATA_GAP`, it writes a knowledge request and attempts auto-resolution:

```yaml
# knowledge/requests/2026-03-17-pilaster-pricing.yaml
id: know-001
created: 2026-03-17
status: resolved  # open | auto-resolving | resolved | escalated
category: DATA_GAP
description: "Need current Pilaster pricing tiers for tutorial content."
triggered_by: "reflexion on task linkedin-tutorial-2026-03-16"
auto_resolution_attempted: true
resolution_method: "MCP call to pilaster-mcp get_product_info()"
resolution_result: "Free tier: 50 generations/month. Pro: $19/month unlimited. Enterprise: custom."
resolved_date: 2026-03-17
```

**Auto-resolution flow:**
1. Agent identifies the data gap
2. Agent checks available MCP tools for relevant data sources
3. If MCP tool exists: call it, store result in `knowledge/`, mark resolved
4. If no MCP tool: attempt web search (via SEO researcher agent with Gemini)
5. If web search fails or data is sensitive/uncertain: escalate to human (`status: escalated`)

### Pattern Analysis

The gap detection system tracks failure categories over time:

```
Weekly summary (auto-generated in Observatory):
  PROMPT_ISSUE:    12 (60%) → feeding Mechanism 4 (prompt evolution)
  QUALITY_ISSUE:    4 (20%) → 2 unique content types flagged
  DATA_GAP:         3 (15%) → 2 auto-resolved, 1 escalated
  CAPABILITY_GAP:   1 (5%)  → 1 open request
```

**Pattern triggers:**
- 3+ `QUALITY_ISSUE` on the same content type in 7 days → alert human to review rubric for that content type
- 3+ `DATA_GAP` for the same data source → consider adding a persistent knowledge cache or new MCP tool
- Any `CAPABILITY_GAP` → immediately visible in Observatory dashboard, human triages weekly
