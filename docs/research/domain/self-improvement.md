---
title: Self-Improvement Mechanisms — Technical Reference
domain: self-improvement
owner: holus-research
last_updated: 2026-03-17
review_cadence: 30
next_review: 2026-04-16
---

# Self-Improvement Mechanisms — Technical Reference

Complete technical reference for how Holus improves autonomously. Covers the six
optimization mechanisms, their activation gates, and the reward signal design that
ties them together. Each section maps research to Holus-specific implementation.

---

## 1. Constitutional AI Evaluation

### Research Foundation

Anthropic's Constitutional AI (Bai et al., 2022) introduced the pattern of using AI
feedback to replace human labels. Instead of hiring annotators to score outputs, a
separate model evaluates against a written constitution (a set of principles). This
decouples evaluation cost from human availability and makes evaluation scalable to
thousands of pieces per day.

Meta's **Self-Taught Evaluator** (Wang et al., 2024) proved the pattern works at
scale: a Llama-70B trained on its own synthetic preference data improved from 75.4
to 88.3 on RewardBench, matching GPT-4-as-judge without any human labels in the
training loop. The key insight: iterative self-training with contrasting chain-of-thought
rationales (one correct, one flawed) teaches the model to distinguish quality better
than direct scoring.

### Holus Implementation

Holus uses 7 domain-expert judges, each a Haiku instance with a specialized rubric.
Evaluation is dispatched by `evaluate_with_routing()` based on content type and
platform.

**2-tier evaluation pipeline:**

| Tier | Model | Triggers on | What it scores |
|------|-------|-------------|----------------|
| Text judge | Haiku | All content | Hook strength, voice fidelity, content depth, platform fit |
| Visual judge | Sonnet (vision) | Carousel, image posts | Rendered PNG — layout, hierarchy, readability, brand consistency |

The text judge runs on every piece. The visual judge only activates when the content
has a rendered visual component — it receives the actual PNG, not a description.

**Evaluator routing by content type:**

- LinkedIn text post: `written-content-judge` + `brand-safety-judge`
- Carousel/PDF: `visual-content-judge` + `written-content-judge` + `brand-safety-judge`
- Video brief: `written-content-judge` + `brand-safety-judge`
- Image post: `visual-content-judge` + `brand-safety-judge`

Each judge outputs structured JSON: dimension scores (1-10), CoT rationale, and a
pass/revise/reject verdict. Scores use the G-Eval pattern (Wei et al., 2023): the
judge writes chain-of-thought reasoning before emitting a numeric score, which
reduces positional bias and improves calibration.

### Goodhart's Law Prevention

Judges must remain **FROZEN for 90 days** after deployment. If the content generator
can observe judge updates in real-time, it will overfit to the judge's quirks rather
than improving actual quality. The 90-day freeze ensures:

1. The generator optimizes against a stable target.
2. Judge drift is measured explicitly (compare frozen vs. updated judge on the same
   holdout set before promoting a new judge version).
3. No feedback loop where generator and judge co-evolve into a degenerate equilibrium.

After 90 days, a new judge version can be promoted if it scores higher on a human-labeled
holdout set of 50 pieces. The old judge is archived, not deleted.

---

## 2. Thompson Sampling

### Research Foundation

Thompson Sampling (Thompson, 1933; tutorial: Russo et al., 2018, Stanford) is a
Bayesian approach to the multi-armed bandit problem. Instead of epsilon-greedy
exploration or UCB bounds, it samples from the posterior distribution of each arm's
reward and plays the arm with the highest sample. This naturally balances exploration
and exploitation: uncertain arms get explored because their posterior is wide, while
well-estimated good arms get exploited because their posterior is concentrated high.

**Real-world deployments at scale:**
- Netflix: thumbnail selection (billions of impressions, Thompson Sampling outperformed
  contextual bandits for cold-start)
- TikTok: content ranking (explore new creators by sampling from uncertain reward
  distributions)
- Spotify: playlist curation (balance known hits vs. discovery)

### Mathematical Details

For **binary rewards** (click/no-click, save/no-save):
- Prior: Beta(alpha=1, beta=1) — uniform
- Update: observe success → alpha += 1; observe failure → beta += 1
- Sample: draw from Beta(alpha, beta) for each arm, play the highest

For **continuous rewards** (engagement score, judge score):
- Prior: Normal-Inverse-Gamma(mu_0, lambda_0, alpha_0, beta_0)
- Conjugate update after each observation
- Sample: draw (mu, sigma^2) from the posterior, then draw reward ~ N(mu, sigma^2)

**Convergence:** approximately 30 observations per arm to stabilize posterior estimates
to within 0.1 of the true mean. With 5 arms, this means ~150 total observations
before the sampler reliably exploits the best arm >80% of the time.

### Holus Implementation

Arms are defined as the cross-product: `(product x content_type x platform)`.

Example arms:
- (pilaster, tutorial, linkedin)
- (invoz, technical_post, twitter)
- (genpeli, demo, tiktok)

**Cap: 5 active arms maximum.** More arms = slower convergence. When a new arm is
proposed (e.g., new platform or content type), the worst-performing arm with >30
observations is retired.

**Reward signal:** Platform engagement score (see Section 6). During cold start,
judge score is used as a proxy reward until real engagement data is available.

**Decision flow:**
1. For each active arm, sample from its posterior.
2. Play the arm with the highest sample.
3. After the content is published and engagement is observed, update the arm's posterior.
4. Log the arm, the sampled value, the observed reward, and the posterior parameters
   to `trajectory.jsonl`.

---

## 3. Genetic Prompt Evolution (PromptBreeder)

### Research Foundation

**PromptBreeder** (Fernando et al., ICLR 2024) introduced evolutionary prompt
optimization: maintain a population of prompt variants, apply mutation and crossover
operators, and select based on task performance. On Big-Bench Hard, PromptBreeder
beat the best human-engineered prompts by 25%.

The breakthrough innovation is **self-referential mutation**: the mutation instructions
themselves are part of the genome and evolve alongside the prompts. This means the
system discovers not just better prompts, but better ways to generate better prompts.

**EvoPrompt** (Guo et al., ICLR 2024) confirmed the pattern with a simpler framework:
differential evolution and genetic algorithms on prompt populations, beating both
manual prompts and gradient-based optimization on 9 datasets.

### Why Genetic Algorithms Over TextGrad

TextGrad (Yuksekgonul et al., 2024) uses LLM-generated gradients to optimize prompts
via backpropagation-style updates. It works well for single-step tasks with immediate
feedback. For Holus, GAs are superior because:

1. **Delayed rewards.** Content performance is measured days after generation. TextGrad
   needs immediate loss signals.
2. **Multi-step generation.** Content passes through strategy → brief → draft → edit →
   judge → publish. Attributing credit to a specific prompt change across this pipeline
   is noisy. GAs handle noisy fitness landscapes naturally.
3. **Noisy signals.** Engagement metrics vary by time of day, trending topics, platform
   algorithm changes. GAs are robust to noise because selection operates on aggregate
   fitness, not individual gradients.
4. **Population diversity.** GAs maintain multiple variants simultaneously, reducing the
   risk of mode collapse to a single prompt style.

### Holus Implementation

**Population management:**

| Stage | Population size | Trigger |
|-------|----------------|---------|
| Cold start (n < 500) | 2 (canonical + challenger) | Challenger created by mutating canonical |
| Growth (n >= 500) | 3 | Third variant added via crossover of top 2 |
| Steady state | 3 (hard cap) | Worst performer replaced every 30 days |

**Three-layer prompt resolution** (from ARCHITECTURE.md) enables this:
1. `config/prompts/` — optimizer-promoted variant (the current winner)
2. `agents/*.md` — canonical prompt (the original)
3. Python fallback — hardcoded constant (never used in practice)

The optimizer writes winning variants to layer 1. The canonical in layer 2 is always
preserved as a baseline. PromptLoader checks layers in order — first hit wins.

**Mutation operators:**
- **Paraphrase mutation:** Rewrite a section while preserving intent.
- **Addition mutation:** Add a new instruction or constraint.
- **Deletion mutation:** Remove a low-signal instruction.
- **Crossover:** Combine sections from two parent prompts.
- **Self-referential mutation:** Evolve the mutation instruction itself (e.g., "when
  mutating, focus on the hook section" → "when mutating, focus on the CTA and
  remove filler words").

**Fitness function:** Weighted average of judge score (0.3) and platform engagement
(0.7) for pieces generated with that prompt variant, measured over a 14-day window.
Minimum 10 pieces per variant before comparison.

---

## 4. Reflexion with Episodic Memory

### Research Foundation

**Reflexion** (Shinn et al., 2023) defines a loop: execute → evaluate → reflect →
retry. The agent generates a natural-language reflection on its failure and stores it
in episodic memory. On the next attempt, it retrieves relevant reflections and avoids
repeating the same mistakes. On HumanEval, Reflexion improved pass@1 from 80.1% to
91.0%.

The key insight: linguistic reflection is more sample-efficient than parameter updates.
A single well-written reflection ("I failed because I used engagement bait instead of
genuine expertise") transfers across tasks, while fine-tuning requires hundreds of
examples.

### Holus Implementation

**ReflexionLoop** (421 lines, LangGraph) runs after every evaluation:

```
content_piece → JudgeAgent scores it → below threshold?
  → YES: ReflexionLoop activates
    → 1. Classify failure (see below)
    → 2. Generate natural-language reflection
    → 3. Store in Mem0 episodic memory
    → 4. Retry generation with reflection injected into context
    → 5. Re-evaluate. If still below threshold, log and move on (max 2 retries)
  → NO: Log success trajectory, no reflection needed
```

**Failure classification** (4 categories):

| Category | Description | Resolution path |
|----------|-------------|-----------------|
| `PROMPT_ISSUE` | The prompt led the generator astray | Feed to PromptBreeder as negative signal |
| `CAPABILITY_GAP` | Missing tool or API (e.g., cannot render video) | Log to `capability-requests/`, human resolves |
| `DATA_GAP` | Missing domain knowledge (e.g., competitor analysis) | Log to `knowledge/requests/`, expert agent auto-resolves |
| `QUALITY_ISSUE` | Execution was fine but output quality is low | Retry with reflection, then log pattern to MEMORY.md |

**ReflectionMemoryManager** interfaces with Mem0 for cross-task episodic learning:
- Stores reflections with metadata: content_type, platform, failure_category, timestamp.
- Retrieves top-3 most relevant reflections (by embedding similarity) when generating
  new content of the same type.
- Reflections expire after 90 days unless explicitly promoted to MEMORY.md.

### Cross-Task Transfer

Reflexion is most powerful when lessons from one content type transfer to another.
Example: a reflection "LinkedIn audience responds better to data-backed claims than
opinion statements" learned from a failed text post also improves carousel content.
Mem0's semantic retrieval enables this — the reflection is retrieved based on meaning,
not exact content_type match.

---

## 5. DSPy (Stanford)

### Research Foundation

**DSPy** (Khattab et al., Stanford, 2023) treats LLM prompts as differentiable
programs. Instead of manually engineering prompts, you write a program with typed
signatures (`context, question -> answer`) and DSPy compiles it by optimizing the
instructions and few-shot examples against a metric.

Key optimizers:
- **BootstrapFewShot:** Automatically selects the best few-shot examples from a
  labeled dataset. Runs the program on each example, keeps the ones that score highest,
  and inserts them as demonstrations.
- **MIPROv2:** Jointly optimizes instructions AND examples. Generates instruction
  candidates, evaluates them with bootstrapped examples, and selects the best
  combination. Typically 5-15% improvement over BootstrapFewShot alone.

**Data requirement:** 30-50 labeled examples minimum for BootstrapFewShot. MIPROv2
benefits from 100+. Below 30, the optimizer overfits to the small sample.

### Holus Implementation (Sprint 5)

DSPy activation is gated behind **500+ trajectory entries**. Before that threshold,
the labeled dataset is too small for reliable optimization.

**Data pipeline for DSPy:**
1. `trajectory.jsonl` accumulates every content piece with its judge scores and
   engagement metrics.
2. At n=500, a curation script selects the top-scoring 50 pieces (by combined judge +
   engagement score) as positive examples.
3. The bottom 50 pieces serve as negative examples (for contrastive learning).
4. DSPy compiles the content generation program against the curated dataset.

**Target signatures:**
```python
# Strategy decision
class DecideContent(dspy.Signature):
    """Decide what content to create given analytics and product state."""
    analytics: str = dspy.InputField()
    product_state: str = dspy.InputField()
    memory: str = dspy.InputField()
    decision: ContentDecision = dspy.OutputField()

# Content generation
class GenerateContent(dspy.Signature):
    """Generate content for a specific platform and product."""
    brief: str = dspy.InputField()
    platform: str = dspy.InputField()
    examples: list[str] = dspy.InputField()
    content: str = dspy.OutputField()
```

**Optimization schedule:**
- At n=500: first BootstrapFewShot compilation.
- Every 200 new entries after that: re-compile with expanded dataset.
- At n=1000: switch to MIPROv2 (enough data for joint optimization).
- Compiled programs are versioned and stored in `config/prompts/dspy/`.

---

## 6. Reward Signal Design

### Platform-Specific Weights

Each platform has a different signal for "this content worked." Using the same metric
everywhere misses what each platform's algorithm actually rewards.

| Platform | Primary metric | Weight | Secondary metric | Weight | Rationale |
|----------|---------------|--------|-----------------|--------|-----------|
| LinkedIn | Comments | 0.5 | Reposts | 0.3 | Comments signal authority; LinkedIn algorithm boosts comment-heavy posts |
| LinkedIn | Profile views | 0.2 | — | — | Proxy for "this person seems worth following" |
| Instagram | Saves | 0.5 | Shares | 0.3 | Saves = bookmark = high intent; IG algorithm weights saves heavily |
| Instagram | Reach | 0.2 | — | — | Distribution signal |
| TikTok | Watch time (%) | 0.6 | Shares | 0.2 | Completion rate is TikTok's primary ranking signal |
| TikTok | Comments | 0.2 | — | — | Engagement depth |
| Twitter | Retweets | 0.4 | Replies | 0.3 | Amplification + conversation |
| Twitter | Link clicks | 0.3 | — | — | Drives traffic to products |

### Dynamic Blending: Judge vs. Engagement

The reward signal evolves as data accumulates:

| Stage | Observations | Reward formula | Rationale |
|-------|-------------|----------------|-----------|
| Cold start | 0-99 paired | 1.0 x judge_score | No engagement data yet; judge is the only signal |
| Transition | 100-299 paired | 0.5 x judge_score + 0.5 x engagement | Both signals available; equal weight during calibration |
| Steady state | 300+ paired | 0.3 x judge_score + 0.7 x engagement | Engagement is ground truth; judge prevents quality collapse |

"Paired observation" = a piece that has both a judge score AND engagement data (i.e.,
it was published and enough time passed to measure performance).

The judge never drops below 0.3 weight. Without the quality floor, the system would
optimize for engagement bait (clickbait headlines, rage content) that scores well on
metrics but damages brand.

### Per-Platform Z-Score Normalization

Raw engagement numbers are not comparable across platforms (1000 views on TikTok is
nothing; 1000 views on LinkedIn is strong). At n >= 30 per platform, engagement scores
are z-score normalized:

```
normalized_score = (raw_score - platform_mean) / platform_std
```

This makes "2 standard deviations above LinkedIn average" comparable to "2 standard
deviations above TikTok average." Below n=30, raw scores are used with a
platform-specific floor to prevent division by near-zero standard deviation.

### Drift Detector

The system monitors its own performance trajectory. If the 30-day rolling average
engagement score drops 0.1 (in z-score terms) from its all-time peak, it triggers:

1. **Alert:** Telegram notification to the operator.
2. **Diagnosis:** Run Reflexion on the last 10 pieces to classify failure patterns.
3. **Optimization trigger:** If the prompt variant has been stable for >14 days,
   trigger a PromptBreeder mutation cycle.
4. **Escalation:** If drift persists for 14 days after optimization, freeze publishing
   and request human review.

---

## 7. Gap Detection

### Failure-Driven Improvement

Every Reflexion cycle classifies failures into 4 categories (see Section 4). Two of
those categories drive automated gap detection:

**Capability gaps** (`CAPABILITY_GAP`):
- Written to `capability-requests/` as structured YAML files.
- Each request includes: what was attempted, why it failed, what tool or API would
  resolve it.
- These are resolved by the human operator (e.g., adding a new MCP tool, purchasing
  an API subscription).
- Telegram notification sent on new capability requests.

**Knowledge gaps** (`DATA_GAP`):
- Written to `knowledge/requests/` as structured YAML files.
- Each request includes: what knowledge was missing, what content type needed it,
  how the gap manifested.
- Expert agents can auto-resolve these by running research and writing the result to
  `knowledge/facts/`.
- The SEO researcher agent (Gemini Pro, web search enabled) is the primary resolver
  for market/competitor knowledge gaps.

### Gap Lifecycle

```
Failure detected
  → Reflexion classifies it
  → Gap file written to appropriate directory
  → Telegram notification sent
  → For DATA_GAP: expert agent attempts auto-resolution
  → For CAPABILITY_GAP: waits for human resolution
  → Once resolved, the gap file is moved to `resolved/` with resolution metadata
  → Resolution is added to MEMORY.md for future reference
```

### Pattern Aggregation

Weekly, the `WeeklyLearningLoop` scans all gaps from the past 7 days and identifies
patterns:
- 3+ `DATA_GAP` in the same domain → create a knowledge brief and assign to research agent
- 2+ `CAPABILITY_GAP` for the same tool → escalate priority in NEXT.md
- Any `PROMPT_ISSUE` appearing 3+ times → force a PromptBreeder mutation cycle

---

## 8. Activation Gates

### Minimum Data Thresholds

All optimization mechanisms are gated behind minimum data thresholds to prevent
premature optimization on insufficient evidence.

| Mechanism | Gate | Minimum data | Rationale |
|-----------|------|-------------|-----------|
| Judge evaluation | Always on | 0 | No data needed; evaluates each piece independently |
| Reflexion + episodic memory | Always on | 0 | Learning from failures is valuable from day 1 |
| Thompson Sampling | Active | 5 observations per arm | Posterior too flat below 5; random selection is equivalent |
| PromptBreeder | Active | 10 pieces per variant | Need enough fitness signal to compare variants |
| Z-score normalization | Per-platform | 30 per platform | Below 30, std estimate is unreliable |
| Dynamic blending (transition) | Global | 100 paired observations | Need enough engagement data to be meaningful |
| Dynamic blending (steady state) | Global | 300 paired observations | Engagement signal is reliable enough to dominate |
| DSPy compilation | Sprint 5 | 500 trajectory entries | BootstrapFewShot needs 30-50 curated examples from a larger pool |
| PromptBreeder population=3 | Growth | 500 trajectory entries | Third variant only justified with enough evaluation data |

### Cold Start Protocol

For the first 30 days (or until 100 paired observations, whichever comes later):

1. **Systematic content calendar.** Instead of Thompson Sampling choosing arms, cycle
   through all (product x content_type x platform) combinations systematically. This
   ensures every arm gets at least 5 observations before the bandit takes over.

2. **Judge + Reflexion only.** No prompt evolution, no engagement-based optimization.
   The judge provides immediate quality feedback. Reflexion captures lessons from
   failures. This is sufficient for rapid improvement in the first month.

3. **Baseline measurement.** Every piece is published and its engagement tracked. This
   builds the paired observation dataset needed for dynamic blending and z-score
   normalization.

4. **No automated optimization.** All prompt changes during cold start are manual
   (canonical prompt updates by the operator). This prevents the system from
   "optimizing" against noise when the sample size is tiny.

**Exit criteria:** Cold start ends when ALL of the following are true:
- 30+ days have elapsed since first publish
- 100+ paired observations accumulated
- Every active arm has 5+ observations
- At least 3 platforms have 30+ observations (for z-score normalization)

---

## References

1. Bai, Y. et al. (2022). **Constitutional AI: Harmlessness from AI Feedback.**
   Anthropic. arXiv:2212.08073.

2. Wang, T. et al. (2024). **Self-Taught Evaluators.** Meta FAIR.
   arXiv:2408.02666.

3. Fernando, C. et al. (2024). **PromptBreeder: Self-Referential Self-Improvement
   via Prompt Evolution.** ICLR 2024. arXiv:2309.16797.

4. Guo, Q. et al. (2024). **Connecting Large Language Models with Evolutionary
   Algorithms Yields Powerful Prompt Optimizers (EvoPrompt).** ICLR 2024.
   arXiv:2309.08532.

5. Khattab, O. et al. (2023). **DSPy: Compiling Declarative Language Model Calls
   into Self-Improving Pipelines.** Stanford. arXiv:2310.03714.

6. Shinn, N. et al. (2023). **Reflexion: Language Agents with Verbal Reinforcement
   Learning.** NeurIPS 2023. arXiv:2303.11366.

7. Russo, D. et al. (2018). **A Tutorial on Thompson Sampling.** Foundations and
   Trends in Machine Learning. Stanford. arXiv:1707.02038.

8. Wei, J. et al. (2023). **G-Eval: NLG Evaluation using GPT-4 with Better Human
   Alignment.** arXiv:2303.16634.

9. Yuksekgonul, M. et al. (2024). **TextGrad: Automatic Differentiation via Text.**
   arXiv:2406.07496.
