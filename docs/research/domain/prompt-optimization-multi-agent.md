---
last_updated: 2026-03-18
review_cadence: 30d
next_review: 2026-04-17
---

# Research: Automated Prompt Optimization for Multi-Agent Systems

**CID:** holus-RESEARCH-20260318-16439686
**Mode:** TECHNICAL_OPTIONS
**Question:** What's the best approach for automated prompt optimization in multi-agent systems? Compare DSPy, TextGrad, and custom approaches for optimizing 32 agent prompts with limited scored runs per agent.

## Options Compared

| Option | Mechanism | Min Data | Multi-Agent Support | Cost/Run | Production Ready |
|--------|-----------|----------|--------------------|---------:|-----------------|
| **DSPy GEPA** | Evolutionary prompt evolution + reflective teacher | ~10 examples | Yes (freeze modules) | ~$2 | Yes (in DSPy) |
| **DSPy MIPROv2** | Bayesian optimization (TPE) on instructions + demos | 200+ examples | Yes (freeze modules) | $5-20 | Yes (production) |
| **DSPy BootstrapFewShot** | Teacher-generated demonstrations | ~5-10 examples | Yes (freeze modules) | <$1 | Yes (production) |
| **TextGrad** | LLM "text gradients" for per-instance optimization | "A handful" | No native support | ~36 LLM calls | No (academic only) |
| **MASPOB** | Bandit (UCB) + GNN + coordinate ascent | Not specified | **Yes — designed for this** | Not specified | No (paper, March 2026) |
| **MAPRO** | MAP inference + downstream blame | Not specified | **Yes — credit assignment** | Not specified | No (paper, Oct 2025) |
| **MASS** | 3-stage: local → topology → global | Not specified | **Yes — per-agent local** | Not specified | No (paper, Feb 2025) |
| **EvoPrompt** | Evolutionary (mutation + crossover) | <20 samples | No | Low | Partial |
| **OPRO** | LLM as optimizer with scoring trajectory | 20-50 entries | No | Moderate | Partial |
| **SPO** | Self-supervised prompt optimization | Similar to TextGrad | No | **1.1-5.6% of TextGrad** | No (paper) |

## Recommendation

DECISION_POINT: primary_optimizer
OPTIONS: A) DSPy GEPA (~$2/run, evolutionary, works with small data, built into DSPy) B) TextGrad (per-instance text gradients, academic only, progressive degradation risk) C) MASPOB (multi-agent native, coordinate ascent, but paper-only March 2026) D) Custom A/B testing (simplest, least intelligent, statistical)
RECOMMENDATION: A
CONFIDENCE: HIGH
EVIDENCE: [VERIFIED] GEPA is production-ready within DSPy, costs ~$2/run, works with small datasets, and supports freezing individual modules — https://dspy.ai/api/optimizers/GEPA/overview/. [VERIFIED] DSPy can freeze modules via `module._compiled = True` for per-agent optimization — https://dspy.ai/faqs/. [VERIFIED] TextGrad has zero production deployments and known progressive degradation — https://github.com/zou-group/textgrad/issues/112

DECISION_POINT: multi_agent_credit_assignment
OPTIONS: A) DSPy freeze-all-but-one (optimize one agent at a time while others fixed) B) MASPOB coordinate ascent with GNN topology model C) MAPRO MAP inference with downstream blame D) Score each agent independently against its own contract (no pipeline-level optimization)
RECOMMENDATION: D (now) → A (when DSPy integrated) → B (when MASPOB matures)
CONFIDENCE: MEDIUM
EVIDENCE: [VERIFIED] MASPOB decomposes combinatorial search into per-agent univariate updates via coordinate ascent — https://arxiv.org/abs/2603.02630. [VERIFIED] DSPy's module freezing is available today — https://dspy.ai/faqs/. [UNVERIFIED] MASPOB and MAPRO are paper-only with no public implementations.

DECISION_POINT: low_data_strategy
OPTIONS: A) DSPy BootstrapFewShot (5-10 examples, cheapest) B) GEPA (evolutionary, ~$2, reads execution traces) C) TextGrad (per-instance, no minimum, but degradation risk) D) EvoPrompt (evolutionary, <20 samples)
RECOMMENDATION: A (bootstrap to 30+ examples) → B (GEPA for ongoing optimization)
CONFIDENCE: HIGH
EVIDENCE: [VERIFIED] BootstrapFewShot works with ~10 examples by using teacher-generated demonstrations — https://dspy.ai/api/optimizers/BootstrapFewShot/. [VERIFIED] GEPA reads full execution traces for diagnosis, unlike RL methods that collapse to scalar reward — https://arxiv.org/abs/2507.19457

## Adversary Notes

### What could go wrong with DSPy GEPA

1. **DSPy assumes end-to-end evaluation.** Our consulting skills produce decision records — evaluating "was this a good decision?" is harder than "was this answer correct?" DSPy optimizers work best when the metric is objective (accuracy, pass/fail). Subjective quality metrics may lead to gaming.

2. **GEPA is new (2025).** Less battle-tested than MIPROv2 or BootstrapFewShot. The evolutionary approach could overfit to a small evaluation set. [VERIFIED] Prompt overfitting is prevalent with small evaluation sets — https://arxiv.org/abs/2410.19920.

3. **Integration complexity.** DSPy expects modules to be DSPy `Predict` or `Module` objects. Our agents are Claude subagents dispatched via the Agent tool or Codex CLI. Wrapping them as DSPy modules requires an adapter layer that maps: input → agent dispatch → output → metric score.

4. **The 3-layer resolution adds complexity.** DSPy writes optimized prompts, but our system needs those prompts to land in Layer 1 (`versions/current.md`) and be loaded by SKILL.md's resolution logic. This is glue code, not fundamental, but it's where bugs will hide.

### What would make us regret this in 6 months

- If MASPOB or MAPRO release production-ready implementations that natively solve multi-agent credit assignment, our DSPy per-agent approach will feel crude by comparison.
- If TextGrad's progressive degradation issue is fixed and SPO-like cost reductions are integrated, the "TextGrad has no production deployments" claim becomes stale.
- If DSPy GEPA turns out to game our eval functions (optimizing for format compliance, not actual quality), we'll need to invest heavily in eval function robustness — the eval function gap we already identified.

### Confirmation bias check

We entered this research already committed to DSPy+TextGrad. The data shows TextGrad should NOT be our primary optimizer (zero production use, degradation risk, high cost). We were wrong about TextGrad. DSPy GEPA or BootstrapFewShot is the correct starting point. The multi-agent-specific papers (MASPOB, MAPRO, MASS) are more relevant to our architecture than TextGrad — we should track them closely.

## Discarded Claims

> No [PHANTOM] claims detected in this research — all URLs were consistent with claimed content during gathering.

## Key Findings Summary

1. **DSPy GEPA is the right starting optimizer** — evolutionary, ~$2/run, works with small data, reads execution traces for diagnosis. Production-ready within DSPy ecosystem.

2. **TextGrad is NOT production-ready** — zero deployments found, known progressive degradation, 36 LLM calls/run. SPO achieves similar at 1-6% of the cost. Drop TextGrad from our architecture.

3. **Multi-agent optimization is an active research area** — MASPOB (March 2026), MAPRO (Oct 2025), MASS (Feb 2025) all tackle per-agent optimization with credit assignment. None have public implementations yet. Track for future integration.

4. **DSPy's module freezing solves our immediate need** — `module._compiled = True` lets us optimize one agent while others stay fixed. Combined with per-agent contract scoring (our existing approach), this is sufficient for now.

5. **BootstrapFewShot for cold start** — with only 5-10 examples, BootstrapFewShot generates synthetic demonstrations. Use this to bootstrap from our small eval history, then switch to GEPA for ongoing optimization.

6. **Eval function quality is the real bottleneck** — all optimizers are only as good as the metric they optimize against. Our broken/missing scorers are a bigger problem than optimizer choice. Fix eval first.

7. **Overfitting risk with small datasets** — use 20/80 train/validation split (DSPy's recommendation, inverted from ML norms). Add holdout eval signals that the optimizer never sees.

## Sources

1. [DSPy Optimizers Documentation](https://dspy.ai/learn/optimization/optimizers/) — PRIMARY
2. [DSPy MIPROv2 API](https://dspy.ai/api/optimizers/MIPROv2/) — PRIMARY
3. [DSPy BootstrapFewShot API](https://dspy.ai/api/optimizers/BootstrapFewShot/) — PRIMARY
4. [DSPy GEPA Overview](https://dspy.ai/api/optimizers/GEPA/overview/) — PRIMARY
5. [DSPy FAQ (module freezing)](https://dspy.ai/faqs/) — PRIMARY
6. [GEPA Paper (arXiv:2507.19457)](https://arxiv.org/abs/2507.19457) — PRIMARY
7. [MIPRO Paper (arXiv:2406.11695)](https://arxiv.org/abs/2406.11695) — PRIMARY
8. [TextGrad Paper (Nature, arXiv:2406.07496)](https://arxiv.org/abs/2406.07496) — PRIMARY
9. [TextGrad Progressive Degradation (GitHub #112)](https://github.com/zou-group/textgrad/issues/112) — PRIMARY
10. [SPO: 1-6% of TextGrad Cost (arXiv:2502.06855)](https://arxiv.org/abs/2502.06855) — PRIMARY
11. [MASPOB (arXiv:2603.02630)](https://arxiv.org/abs/2603.02630) — PRIMARY
12. [MAPRO (arXiv:2510.07475)](https://arxiv.org/abs/2510.07475) — PRIMARY
13. [MASS (arXiv:2502.02533)](https://arxiv.org/abs/2502.02533) — PRIMARY
14. [EvoPrompt (arXiv:2309.08532)](https://arxiv.org/abs/2309.08532) — PRIMARY
15. [OPRO (arXiv:2309.03409)](https://arxiv.org/abs/2309.03409) — PRIMARY
16. [Prompt Overfitting (arXiv:2410.19920)](https://arxiv.org/abs/2410.19920) — PRIMARY
17. [LangChain Prompt Optimization Blog](https://blog.langchain.com/exploring-prompt-optimization/) — SECONDARY
18. [Opik Agent Optimizer](https://www.comet.com/docs/opik/agent_optimization/overview) — SECONDARY
