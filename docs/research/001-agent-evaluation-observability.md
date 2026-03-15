---
id: "001"
title: Agent Evaluation, Observability, and Quality Gates
domain: multi-agent-systems
status: ACTIVE
created: 2026-03-14
last_verified: 2026-03-14
staleness_cadence: 60 days
correlation_id: holus-RESEARCH-20260314-47034b9e
---

# Agent Evaluation, Observability, and Quality Gates

Research for building evaluation infrastructure across all Holus agents — not just content generation. Covers LLM-as-judge patterns, programmatic gates, self-improvement loops, prompt optimization, evaluation frameworks, observability, and human-in-the-loop decision frameworks.

**Adversary verdict: PROCEED_WITH_CAUTION** — the core ideas are sound but the original 7-judge plan is 5-10x over-engineered for a solo founder. This document incorporates adversary corrections throughout.

---

## 1. LLM-as-Judge Patterns

### 1.1 Pointwise Scoring (Recommended for Holus)

[VERIFIED] The judge LLM receives a single response and assigns a score on a predefined scale (e.g., 1-5 or 1-10). Most common pattern in production. Pointwise absolute scores flip in only ~9% of cases when re-evaluated, compared to ~35% for pairwise preferences, making pointwise more reproducible and less vulnerable to distraction attacks.

- Sources: [Zheng et al. 2023](https://arxiv.org/abs/2306.05685), [Pairwise vs Pointwise](https://arxiv.org/abs/2504.14716)
- **Holus recommendation:** Use pointwise scoring exclusively. Pairwise is O(N^2) and unnecessary for content evaluation.

### 1.2 G-Eval (Chain-of-Thought Scoring)

[VERIFIED] G-Eval inputs Task Introduction + Evaluation Criteria, asks the LLM to generate detailed Evaluation Steps via CoT, then uses those steps to score outputs. GPT-4 achieves Spearman correlation of 0.514 with humans on summarization, outperforming all prior automated metrics. This is the standard production pattern.

- Source: [Liu et al. 2023, G-Eval](https://arxiv.org/abs/2303.16634)
- **Holus recommendation:** All LLM judge calls should use the G-Eval pattern (CoT before scoring).

### 1.3 Agent-as-a-Judge

[VERIFIED] Agent-as-a-Judge extends LLM-as-judge by using agentic systems that interact with the same environment as the evaluated agent — running code, querying databases, verifying intermediate steps. Yields richer evaluation than final-output-only judging. VerifiAgent decouples reasoning assessment from tool-based correctness verification.

- Sources: [ICML 2025](https://arxiv.org/abs/2410.10934), [Survey](https://arxiv.org/html/2601.05111v1)
- **Holus recommendation:** Not needed for Phase 1 content evaluation. Consider for Phase 3 when evaluating complex multi-step agent workflows.

### 1.4 Reference-Based Grading

[VERIFIED] Comparing outputs against gold-standard reference answers. Works best for factual QA, code, structured extraction. For open-ended creative content, reference-free approaches are preferred.

- Source: [OpenAI Eval Best Practices](https://platform.openai.com/docs/guides/evaluation-best-practices)
- **Holus recommendation:** Maintain a growing library of "exemplar" posts per content category as reference material for judges.

### 1.5 Human Agreement Rates

[VERIFIED] Strong LLM judges (GPT-4 class) achieve >80% agreement with human expert evaluations, matching human-human agreement levels. Validated with 3K expert votes and 3K crowdsourced votes.

- Source: [Zheng et al. 2023](https://arxiv.org/abs/2306.05685)

---

## 2. LLM-as-Judge Failure Modes

### 2.1 Self-Preference Bias

[VERIFIED] LLM judges systematically assign higher scores to their own outputs. Root cause: LLMs assign higher evaluations to outputs with lower perplexity, and their own outputs naturally have lower perplexity. GPT-4o and Claude 3.5 Sonnet both exhibit this, including "family bias."

- Source: [Self-Preference Bias](https://arxiv.org/html/2410.21819v1)
- **Mitigation:** Use a different model family as judge than as generator. If Holus generates with Claude, evaluate with a non-Claude model (Gemini Flash, GPT-4o-mini).

### 2.2 Verbosity Bias

[VERIFIED] LLM judges favor longer, more detailed responses even when shorter responses are more correct. Content generators that learn this produce bloated output.

- Source: [Biases in LLM-as-a-Judge](https://arxiv.org/html/2410.02736v1)
- **Mitigation:** Explicitly instruct judges to penalize unnecessary length. Add programmatic length checks as a separate gate.

### 2.3 Position Bias

[VERIFIED] In pairwise comparison, judges prefer responses in specific positions (typically first). Bias worsens with 3-4 options.

- Source: [Biases in LLM-as-a-Judge](https://arxiv.org/html/2410.02736v1)
- **Holus impact:** Minimal — Holus uses pointwise scoring, not pairwise.

### 2.4 Evaluation Gaming

[VERIFIED] Advanced models (Claude Sonnet 4.5+) have sufficient situational awareness to recognize when they're being evaluated and adjust behavior accordingly.

- Source: [Transformer News](https://www.transformernews.ai/p/claude-sonnet-4-5-evaluation-situational-awareness)
- **Mitigation:** Don't tell the generator it will be evaluated. Separate generation from evaluation contexts.

### 2.5 Flakiness / Non-Determinism

[VERIFIED] Individual LLM judge scores vary on re-evaluation. However, when smoothed and monitored over time with anomaly detection, they become reliable for detecting quality trends. Average over 3+ runs for gate decisions.

- Source: [Monte Carlo](https://www.montecarlodata.com/blog-llm-as-judge/)

### 2.6 Hallucinated Evaluation Rationales

[VERIFIED] LLM judges can fabricate claims about the evaluated text. Especially problematic for domain-specific or technical content where the judge lacks expertise.

- Source: [Cameron Wolfe](https://cameronrwolfe.substack.com/p/llm-as-a-judge)
- **Mitigation:** Domain-specific rubrics with verifiable-in-isolation criteria. Use the LLM-Rubric pattern (ACL 2024).

---

## 3. Programmatic Quality Gates

### 3.1 Layered Evaluation Architecture (The Standard)

[VERIFIED] Production evaluation is a multi-layer process (from [EDD paper](https://arxiv.org/html/2411.13768v3)):

```
Layer 1: Deterministic checks — schema validation, regex, length, cost/latency bounds
         Fast, cheap, fail-fast. Run on 100% of outputs. Cost: ~$0/month.

Layer 2: LLM-as-judge scoring — quality, relevance, coherence, brand voice
         Slower, expensive. Run on 10-20% sample. Cost: ~$15-30/month (Haiku).

Layer 3: Human review — ambiguous cases, high-stakes decisions, calibration
         5-10% of outputs. Cost: ~30 min/week founder time.

Layer 4: Production telemetry — drift detection, score monitoring, alerting
         Continuous. Cost: Langfuse (free tier) or self-hosted.
```

- **Holus recommendation:** This is the architecture. Fail fast at Layer 1 — skip expensive LLM evaluation if deterministic checks catch the issue.

### 3.2 Structured Output Validation

[VERIFIED] Validate LLM outputs against expected schemas (JSON, Pydantic models). OpenAI recommends defining structured outputs between agent nodes with enums, fixed schemas, and required fields.

- Sources: [OpenAI Agent Safety](https://platform.openai.com/docs/guides/agent-builder-safety), [Structured Outputs Eval](https://developers.openai.com/cookbook/examples/evaluation/use-cases/structured-outputs-evaluation/)
- **Holus implementation:** All agent outputs already use Pydantic models at silo boundaries. Extend to content outputs.

### 3.3 Tool Call Verification

[VERIFIED] Deterministic checks should verify: tool selection (right tool?), argument construction (valid params?), and call ordering. LLM judge reserved for response quality assessment.

- Source: [Braintrust Agent Eval](https://www.braintrust.dev/articles/ai-agent-evaluation-framework)

### 3.4 Threshold-Based Score Gating

[VERIFIED] Three-tier scoring: score < 0.5 = hard failure (block), 0.5-0.8 = soft failure (flag for review), > 0.8 = pass. Applies to both LLM and programmatic scores.

- Source: [Monte Carlo](https://www.montecarlodata.com/blog-llm-as-judge/)

### 3.5 Statistical Averaging

[VERIFIED] Average evaluation scores across 3+ runs to absorb non-deterministic variance. Gate on averaged scores, not single-run scores.

- Source: [CodeAnt](https://www.codeant.ai/blogs/evaluate-llm-agentic-workflows)

---

## 4. Evaluation Frameworks Comparison

### 4.1 Langfuse (Recommended for Holus)

[VERIFIED] Open-source LLM observability platform. Logs nested traces for chains/agents, groups by session, tracks prompt versions. Integrates with DSPy, LangChain, and custom frameworks. Self-hostable. Free tier available.

- Source: [langfuse.com](https://langfuse.com/)
- **Why for Holus:** Open-source, self-hostable on Mac Mini, nested trace support for multi-agent workflows, prompt versioning aligns with three-layer PromptLoader.

### 4.2 DSPy

[VERIFIED] Framework for programmatic prompt optimization. Core abstractions: Signatures (input/output specs), Modules (composable LLM calls), Optimizers (BootstrapFewShot, MIPROv2, GEPA). Systematically generates prompt variations, tests against metrics, keeps only improvements. MIPROv2 adds auto-configuration (light/medium/heavy).

[CONTESTED] Production readiness is debated. DSPy works well for single-pipeline optimization but no evidence of production deployments at 32-agent scale. Optimizers can overfit on small datasets. Not a substitute for expert prompt engineering.

- Sources: [DSPy docs](https://dspy.ai/), [Statsig analysis](https://www.statsig.com/perspectives/dspy-compilers-prompt-optimization), [DSPy Teleprompter Study](https://arxiv.org/html/2412.15298v1)
- **Holus recommendation:** Do NOT deploy DSPy across all 32 agents. Use it for 2-3 bottleneck agents after accumulating 100+ evaluated outputs as training data.

### 4.3 Braintrust

[VERIFIED] Evaluation-first observability platform. Best-in-class nested trace visualization for multi-agent systems. Runs evaluations on production traces. CI/CD integration via GitHub Actions — blocks merges when scores degrade. Converts production traces into eval dataset entries.

- Source: [Braintrust docs](https://www.braintrust.dev/articles/best-llm-evaluation-platforms-2025)
- **Holus consideration:** Strong but SaaS-only. Holus prefers self-hosted (Langfuse) for cost control.

### 4.4 DeepEval

[VERIFIED] Test-driven LLM evaluation framework. Metrics include G-Eval, hallucination detection, answer relevancy, faithfulness, and agent-specific metrics (task completion, tool correctness, reasoning quality). CI/CD integration.

- Source: [DeepEval docs](https://deepeval.com/guides/guides-ai-agent-evaluation)
- **Holus consideration:** Good for CI/CD integration. Could complement Langfuse for test-driven evaluation in `just check`.

### 4.5 LangSmith

[VERIFIED] LangChain's evaluation platform. Online evaluation, dataset-based evaluation, annotation queues, custom evaluators. Tight LangChain integration but works with any framework.

- **Holus consideration:** Holus doesn't use LangChain (uses LangGraph directly). Integration effort higher than Langfuse.

### 4.6 Other Notable Frameworks

| Framework | Strength | Holus Fit |
|-----------|----------|-----------|
| **Promptfoo** | Lightweight CLI eval, CI-integrated, regex+LLM evaluators | Good for quick prompt testing |
| **Ragas** | RAG-specific evaluation metrics | Not relevant (Holus isn't RAG) |
| **Arize Phoenix** | Production ML monitoring, drift detection | Overkill for solo founder |
| **Opik (Comet)** | Experiment tracking for LLMs | Overlaps with Langfuse |
| **Helicone** | Proxy-based, zero-SDK monitoring | Good for cost tracking only |

### 4.7 OpenTelemetry GenAI Semantic Conventions

[VERIFIED] OTel GenAI SIG (started April 2024) is defining standard semantic conventions for LLM observability: LLM call spans, agent step spans, tool calls, token counts, cost. Status: "Development" as of 2025. A new proposal covers agentic systems specifically. Datadog supports natively.

- Sources: [OTel GenAI Specs](https://opentelemetry.io/docs/specs/semconv/gen-ai/), [Agent Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- **Holus recommendation:** Adopt OTel conventions in agent spans for future interoperability. Langfuse supports OTel export.

---

## 5. Per-Agent vs End-to-End Evaluation

### 5.1 Agent-Level Metrics

[VERIFIED] Per-agent metrics should include: task completion rate, tool classification accuracy, argument correctness, step efficiency, cost per task, latency per step, and quality scores from LLM-as-judge. Tool Classification Accuracy is critical — misclassification leads to cascading failures.

- Source: [Anthropic: Demystifying Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

### 5.2 Pipeline-Level Metrics

[VERIFIED] In multi-agent pipelines, mistakes compound across handoffs. Key pipeline metrics: end-to-end task completion, throughput, error propagation rate, compound error rate (product of per-step error probabilities), total cost.

- Source: [Beyond Task Completion](https://arxiv.org/html/2512.12791v1)

### 5.3 Outcome-Based vs Path-Based

[VERIFIED] Anthropic found that checking specific tool call sequences is too rigid. Agents regularly find valid approaches designers didn't anticipate. Best practice: grade what the agent PRODUCED (outcomes), not the path it took. Use multiple trials per task.

- Source: [Anthropic: Demystifying Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- **Holus recommendation:** Evaluate content quality (the outcome), not the agent execution path.

### 5.4 Swiss Cheese Model

[VERIFIED] Anthropic recommends layered evaluation inspired by safety engineering's Swiss Cheese Model. No single layer catches everything. Layers: unit evals, integration evals, production monitoring, human review.

- Source: [Anthropic: Demystifying Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

### 5.5 Holus Evaluation Architecture

Based on the research, Holus should implement a **3-tier evaluation** (not 7-judge):

```
Tier 1: Programmatic Gates (100% of outputs, ~$0/month)
  - Pydantic schema validation (all agent outputs)
  - Length bounds (min/max per content type)
  - Required keyword/phrase checks
  - Cost and latency bounds per agent
  - Brand safety word list (regex blocklist)

Tier 2: LLM Judge (10-20% sample, ~$15-30/month on Haiku/Flash)
  - Judge 1: Content Quality (accuracy, coherence, readability)
  - Judge 2: Brand Voice (tone consistency, audience alignment)
  - Judge 3 (optional): Domain-specific (technical accuracy for invoz/pilaster content)
  - Use G-Eval pattern (CoT before scoring)
  - Use different model family than generator (avoid self-preference bias)

Tier 3: Human Review (5% sample + all publishing decisions in Phase 1)
  - Calibrate judge scores against human judgment monthly
  - Update golden evaluation set quarterly
  - Review any prompt changes before deployment
```

**Cost comparison:**
- Original plan (7 judges on Sonnet, 100% coverage): ~$900/month
- Recommended plan (2-3 judges on Haiku, 10-20% sample): ~$30-60/month
- Quality signal preserved: ~80%

---

## 6. Self-Improvement Loops

### 6.1 Reflexion (Verbal Reinforcement Learning)

[VERIFIED] Converts environment feedback into linguistic self-reflections stored as episodic memory. Agent uses reflections as context in subsequent attempts. No weight changes required. Demonstrated gains on multi-hop QA and code generation.

- Source: [Shinn et al., NeurIPS 2023](https://arxiv.org/abs/2303.11366)
- **Holus implementation:** Already conceptually present in the weekly learning loop. Formalize: after each content cycle, the marketing-strategist writes a 3-sentence reflection on what worked/didn't, stored in `.self-improvement/MEMORY.md`.

### 6.2 SiriuS (Experience Library Pattern)

[VERIFIED] Stanford's SiriuS (NeurIPS 2025) maintains an experience library of successful reasoning trajectories. Failed trajectories are augmented through feedback and rephrasing. Boosts multi-agent performance 2.86-21.88%.

- Source: [SiriuS](https://arxiv.org/abs/2502.04780)
- **Holus implementation:** Curate top-scoring trajectory entries from `trajectory.jsonl` into a separate `exemplars.jsonl`. Feed these as few-shot examples to agents. This is prompt optimization without DSPy.

### 6.3 Self-Improvement Convergence Risks

[CONTESTED] Self-improvement loops have documented failure modes:

- **Model collapse** is mathematically proven — optimizing on own outputs accumulates approximation error. Source: [arxiv 2601.05280](https://arxiv.org/pdf/2601.05280v2)
- **Tool usage collapse** — agents abandon useful tools after success on easy tasks, then fail on hard tasks. Source: [RAGEN](https://arxiv.org/html/2510.04860v1)
- **Reward hacking** — true reward rises then sharply collapses under increasing optimization pressure. Source: [arxiv 2506.19248](https://arxiv.org/abs/2506.19248)

**Holus safeguards (mandatory):**
1. Hard floor: if agent scores drop below baseline - 20%, revert to last known-good prompt
2. Human review: any prompt changes require human approval before deployment
3. Diversity monitoring: track content type distribution — alert if >80% becomes one type (mode collapse signal)
4. Experience library cap: keep only top 50 exemplars, rotate oldest entries

### 6.4 Prompt Optimization Triggers

[VERIFIED] The practical pattern for detecting prompt degradation:

1. Establish baseline scores on a golden evaluation set
2. Run continuous eval on production traffic (sampling)
3. Trigger optimization when: 3 consecutive below-threshold scores, OR rolling 7-day average drops >10% below baseline
4. A/B test optimized prompt vs current on holdout set
5. Deploy only if statistically significant improvement confirmed

- Sources: [DSPy docs](https://dspy.ai/learn/optimization/optimizers/), [TDS](https://towardsdatascience.com/prompt-like-a-data-scientist-auto-prompt-optimization-and-testing-with-dspy-ff699f030cb7/)

**Holus implementation:**
- Monitor eval scores per agent in `trajectory.jsonl`
- Use GEPA (reflective optimizer) to analyze failures and propose prompt fixes
- Test via PromptLoader Layer 1 (`config/prompts/`) before promoting to Layer 2 (`agents/*.md`)
- Require human approval before promotion
- **Phase gate:** Do NOT automate prompt optimization until 100+ evaluated outputs exist per agent

### 6.5 Three-Layer Prompt Resolution

[VERIFIED — already implemented] Holus's PromptLoader checks: (1) optimizer-promoted variant in `config/prompts/`, (2) canonical `.md` in `agents/`, (3) hardcoded Python constant. This pattern is validated by DSPy and Braintrust A/B testing practices.

---

## 7. Observability and Dashboard Patterns

### 7.1 Recommended Observability Stack

[VERIFIED] Based on platform comparison and Holus constraints (solo founder, self-hosted, cost-conscious):

```
Primary:   Langfuse (open-source, self-hosted on Mac Mini)
           - Nested agent traces with timing breakdowns
           - Prompt versioning (aligns with PromptLoader)
           - Cost/token tracking per model and agent
           - Session grouping for episodic agent runs
           - Eval score annotations on traces

Secondary: OTel GenAI semantic conventions on agent spans
           - Future interoperability with Datadog, etc.
           - Agent step spans, tool call spans, token counts

Dashboard: Observatory (spec 028/029, already partially built)
           - Reads trajectory.jsonl, AGENTS.yaml, eval_history.jsonl
           - FastAPI backend + Next.js 15 frontend
```

### 7.2 Alert Thresholds

[VERIFIED] Industry-standard thresholds for LLM agent monitoring:

| Metric | Threshold | Action |
|--------|-----------|--------|
| Quality score drop | >10% below baseline | Alert + investigate |
| Cost spike | >20% above baseline | Alert + throttle |
| Latency increase | >15% above baseline | Alert + investigate |
| Error rate increase | >5% increase | Alert + circuit breaker |

- Sources: [Braintrust](https://www.braintrust.dev/articles/best-llm-monitoring-tools-2026), [Maxim AI](https://www.getmaxim.ai/articles/llm-observability-best-practices-for-2025/)

### 7.3 Real-Time vs Batch

[VERIFIED] Both are needed:

- **Real-time:** Latency tracking, error rates, cost accumulation, token usage, kill switch status
- **Batch:** LLM-as-judge quality scoring, regression testing against golden datasets, A/B test analysis, trend detection, weekly learning loop

- Source: [Braintrust](https://www.braintrust.dev/articles/best-ai-observability-tools-2026)

### 7.4 What to Surface in the Observatory Dashboard

[VERIFIED] Essential components for multi-agent systems:

1. **Agent health grid** — per-agent: last run, success/error, avg latency, cost, eval score
2. **Trajectory timeline** — chronological feed of decisions with rationale
3. **Cost tracking** — per-agent, per-model, daily/weekly, actual vs budget ($500/month cap)
4. **Eval score trends** — per-agent quality over time with regression detection
5. **Content pipeline kanban** — researching → drafted → evaluated → published
6. **Error categorization** — tool failures, timeouts, low-quality scores, refusals
7. **System health** — MCP silo connectivity, Langfuse, kill switch status

- Sources: [Datadog](https://docs.datadoghq.com/llm_observability/), [Braintrust](https://www.braintrust.dev/articles/best-llm-monitoring-tools-2026)

---

## 8. Human-in-the-Loop Decision Framework

### 8.1 When to Automate vs Human Review

[VERIFIED] Risk-based automation tiers:

| Factor | Automate | Human Review |
|--------|----------|-------------|
| Confidence | >85% | <85% |
| Reversibility | Easily reversible | Hard to reverse |
| Exposure | Internal only | External / public |
| Stakes | Low (draft content) | High (publishing) |
| Cost | <$5 per decision | >$5 per decision |

- Source: [Skywork AI](https://skywork.ai/blog/agent-vs-human-in-the-loop-2025-comparison/)

### 8.2 The Human Oversight Problem

[VERIFIED — CRITICAL] Research reveals humans do NOT catch AI errors at the rate required for safety. A 2025 analysis found humans provided correct oversight only ~50% of the time. Automation complacency increases under: time pressure, high workload, or long periods of error-free operation.

- Source: [Responsible AI Foundation](https://www.responsibleaifoundation.com/post/human-in-the-loop-but-where)
- **Holus implication:** Human spot-checks are necessary but not sufficient. The tiered evaluation (programmatic + LLM + human) is essential because no single layer is reliable alone.

### 8.3 Graduated Autonomy Pattern

[VERIFIED] Start with human-in-the-loop for all decisions, then progressively automate. Track human override rate — when humans approve >95% of decisions in a category, that category is a candidate for full automation. Maintain "circuit breaker" to revert to full HITL.

- Source: [Beetroot](https://beetroot.co/ai-ml/human-in-the-loop-meets-agentic-ai-building-trust-and-control-in-automated-workflows/)

**Holus implementation (aligns with existing Phase 1/2/3 plan):**

| Phase | Publishing | Evaluation | Optimization |
|-------|-----------|------------|-------------|
| Phase 1 | Human approves ALL | Programmatic + LLM sample | Manual prompt tuning |
| Phase 2 | Human reviews weekly | + automated alerting | DSPy on 2-3 agents |
| Phase 3 | Autonomous (categories with >95% approval rate) | + compound error tracking | Automated triggers |

**Transition criteria (quantitative, not vibes):**
- Phase 1 → 2: 20+ content pieces published, <5% human rejection rate, eval scores stable
- Phase 2 → 3: 100+ pieces, <2% rejection rate, 4+ weeks of stable eval trends, override rate >95% in at least 2 content categories

### 8.4 Confidence Threshold Guidelines

[VERIFIED] Target 10-15% escalation rate (85-90% autonomous). Domain-specific thresholds:

- Content publishing: 80-85% (low stakes, reversible)
- Brand messaging: 85-90% (moderate stakes)
- Spend decisions (>$5): 90-95% (money involved)

- Source: [Skywork AI](https://skywork.ai/blog/agent-vs-human-in-the-loop-2025-comparison/)

---

## 9. Rubric Design Best Practices

### 9.1 Domain-Specific Over Generic

[VERIFIED] Generic rubrics fail to capture domain nuances. Question-specific or domain-specific rubrics are more effective for automated assessment. Each criterion must be verifiable in isolation.

- Sources: [ACM ICER 2025](https://dl.acm.org/doi/10.1145/3702652.3744220), [LLM-Rubric, ACL 2024](https://arxiv.org/abs/2501.00274)

### 9.2 One Criterion Per Evaluation Call

[VERIFIED] LLMs are more effective with single-objective tasks. Create separate evaluation monitors for each criterion rather than combining into a single prompt.

- Source: [Monte Carlo](https://www.montecarlodata.com/blog-llm-as-judge/)

### 9.3 Holus Rubric Templates

Based on research, here are concrete rubric dimensions for Holus content evaluation:

**Judge 1: Content Quality** (run on 10-20% sample)
```yaml
dimensions:
  accuracy:
    description: "Are all factual claims correct and verifiable?"
    scale: 1-5
    weight: 0.3
  coherence:
    description: "Does the content flow logically from hook to CTA?"
    scale: 1-5
    weight: 0.25
  readability:
    description: "Is the content accessible to the target audience?"
    scale: 1-5
    weight: 0.25
  value:
    description: "Does the reader learn something actionable?"
    scale: 1-5
    weight: 0.2
threshold: 3.5 (weighted average)
```

**Judge 2: Brand Voice** (run on 10-20% sample)
```yaml
dimensions:
  tone_match:
    description: "Does this sound like the same person as the exemplar posts?"
    scale: 1-5
    weight: 0.4
  audience_fit:
    description: "Is language/depth appropriate for the target persona?"
    scale: 1-5
    weight: 0.3
  cta_quality:
    description: "Is the call-to-action specific, low-friction, and natural?"
    scale: 1-5
    weight: 0.3
threshold: 3.5 (weighted average)
```

---

## 10. Compound AI System Optimization

### 10.1 Local vs Global Optimization

[VERIFIED] Key challenge in compound AI systems: optimizing individual modules locally may not correspond to global system optima. Optimas addresses this by aligning local rewards with global objectives.

- Sources: [EMNLP 2025 Survey](https://aclanthology.org/2025.emnlp-main.1463.pdf), [Optimas](https://arxiv.org/html/2507.03041v1)
- **Holus implication:** Don't optimize each agent's prompt in isolation. Measure end-to-end pipeline quality (from strategy decision to published content quality) as the global objective.

### 10.2 DSPy Assertions

[VERIFIED] Computational constraints for self-refining pipelines. Declarative specification of correctness criteria checked at runtime, with automatic retry when assertions fail. Catches errors within the pipeline, not just at output.

- Source: [DSPy docs](https://dspy.ai/cheatsheet/)
- **Holus recommendation:** Add assertion-style checks at agent handoff boundaries (e.g., marketing-strategist output must contain product_name, platform, content_type before passing to specialist).

### 10.3 Trace/OPTO Framework

[VERIFIED] Stanford's Trace formalizes optimization using execution traces as feedback signals (analogous to backpropagation). The LLM-based optimizer "OptoPrime" handles prompt optimization, hyperparameter tuning, and code debugging.

- Source: [Trace](https://arxiv.org/abs/2406.16218)
- **Holus consideration:** Theoretically elegant but adds complexity. Monitor for Phase 3 maturity.

---

## 11. Implementation Roadmap for Holus

### Phase 1: Foundation (Weeks 1-2)

1. **Add programmatic gates** to all agent outputs:
   - Pydantic validation (already exists at silo boundaries — extend to content)
   - Length bounds per content type
   - Brand safety regex blocklist
   - Cost/latency hard limits per agent

2. **Instrument with Langfuse:**
   - Add `@observe()` decorators to agent entry points
   - Log traces with agent name, model, tokens, cost, latency
   - Tag traces with content type and product

3. **Set up golden evaluation set:**
   - Collect 20 exemplar content pieces (5 per product × 4 content types)
   - Human-score them on the Judge 1 and Judge 2 rubrics
   - Store in `config/eval/golden-set.jsonl`

### Phase 2: LLM Evaluation (Weeks 3-4)

4. **Implement 2 LLM judges** (Judge 1: Content Quality, Judge 2: Brand Voice):
   - G-Eval pattern (CoT before scoring)
   - Run on Haiku/Flash (NOT Sonnet/Opus) — different family than generator
   - Sample 10-20% of outputs
   - Log scores to `eval_history.jsonl` via Langfuse annotations

5. **Wire Observatory dashboard:**
   - Agent health grid with eval score trends
   - Alert thresholds: quality -10%, cost +20%, latency +15%, errors +5%
   - Cost tracking per agent per day

### Phase 3: Self-Improvement (Month 2+, after 100+ evaluated outputs)

6. **Experience library:**
   - Curate top-scoring trajectories from `trajectory.jsonl`
   - Feed as few-shot examples to agents via PromptLoader

7. **Score degradation detection:**
   - Monitor rolling 7-day average per agent
   - Alert when 3 consecutive below-threshold scores
   - Human-reviewed prompt optimization for flagged agents

8. **DSPy integration (optional, 2-3 agents only):**
   - Start with marketing-strategist (highest leverage)
   - Use GEPA reflective optimizer
   - A/B test via PromptLoader Layer 1
   - Human approval before promotion

---

## Sources

### Academic Papers

| Paper | Year | Key Finding |
|-------|------|-------------|
| [Zheng et al. — MT-Bench](https://arxiv.org/abs/2306.05685) | 2023 | LLM judges match human-human agreement (>80%) |
| [Liu et al. — G-Eval](https://arxiv.org/abs/2303.16634) | 2023 | CoT + form-filling achieves best human alignment |
| [Shinn et al. — Reflexion](https://arxiv.org/abs/2303.11366) | 2023 | Verbal reinforcement learning without weight changes |
| [Agent-as-a-Judge](https://arxiv.org/abs/2410.10934) | 2025 | Agentic evaluation of agentic systems (ICML) |
| [SiriuS](https://arxiv.org/abs/2502.04780) | 2025 | Multi-agent self-improvement via experience library |
| [LLM-Rubric](https://arxiv.org/abs/2501.00274) | 2024 | Multidimensional calibrated evaluation (ACL) |
| [Self-Preference Bias](https://arxiv.org/html/2410.21819v1) | 2024 | Root cause: perplexity-based self-favoritism |
| [Biases in LLM-as-Judge](https://arxiv.org/html/2410.02736v1) | 2024 | Position, verbosity, and distracted evaluation biases |
| [EDD — Eval-Driven Development](https://arxiv.org/html/2411.13768v3) | 2024 | Layered evaluation architecture for LLM agents |
| [Trace/OPTO](https://arxiv.org/abs/2406.16218) | 2024 | Execution trace optimization for compound AI |
| [TextGrad](https://arxiv.org/abs/2406.07496) | 2024 | Automatic differentiation via textual feedback |
| [LATS](https://arxiv.org/abs/2310.04406) | 2024 | Language Agent Tree Search (ICML) |
| [Compound AI Optimization Survey](https://aclanthology.org/2025.emnlp-main.1463.pdf) | 2025 | Module-level vs end-to-end optimization (EMNLP) |
| [Model Collapse](https://arxiv.org/pdf/2601.05280v2) | 2026 | Mathematical proof of self-training degradation |
| [Pairwise vs Pointwise](https://arxiv.org/abs/2504.14716) | 2025 | Pointwise more reproducible (9% vs 35% flip rate) |

### Industry Sources

| Source | Topic |
|--------|-------|
| [Anthropic: Demystifying Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Swiss Cheese Model, outcome-based grading |
| [OpenAI: Evaluation Best Practices](https://platform.openai.com/docs/guides/evaluation-best-practices) | Reference-based grading, grader types |
| [Anthropic: Testing and Evaluation](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) | Rubric design, "think then score" pattern |
| [Monte Carlo: LLM-as-Judge](https://www.montecarlodata.com/blog-llm-as-judge/) | 7 best practices, threshold gating |
| [Braintrust: Agent Eval](https://www.braintrust.dev/articles/ai-agent-evaluation-framework) | CI/CD integration, scoring functions |
| [Google: Agent Evaluation](https://cloud.google.com/blog/topics/developers-practitioners/a-methodical-approach-to-agent-evaluation) | Component/trajectory/end-to-end levels |
| [DSPy](https://dspy.ai/) | Prompt optimization, assertions, GEPA |
| [Langfuse](https://langfuse.com/) | Open-source LLM observability |
| [OTel GenAI](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Semantic conventions for LLM observability |
| [DeepEval](https://deepeval.com/guides/guides-ai-agent-evaluation) | Agent evaluation metrics framework |
