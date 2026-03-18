---
last_updated: 2026-03-18
review_cadence: 30d
next_review: 2026-04-17
---

# Adversary Verdict: Self-Improvement Architecture Review

**5 adversary tracks, 100+ sources. This is the honest assessment.**

## What The Adversary Found

### GEPA Is Wrong For Us Right Now
- No evidence of GEPA optimizing standalone system prompts / agent doctrines (our exact use case)
- A practitioner who tried GEPA on agentic tasks reported "spaghetti, slop" prompts
- "$2/run" is misleading — actual fleet cost is $7K-10K across 22 agents (eval execution costs)
- 5-20 examples per agent is **below the threshold for meaningful optimization** — massive overfitting risk, no train/val split possible
- DSPy save/load is buggy — optimized demos lost on reload
- Module freezing is recent/unstable, not tested with GEPA specifically

### Our Eval Infrastructure Is Weaker Than We Thought
- "85% of signal" from deterministic checks is a fabricated number — no correlation measurement exists
- Self-reported fields (verdict, issues_remaining) mean agents grade their own homework
- Our LLM judge (Gemini Flash) was killed for bad implementation, not fundamental flaws — Opus achieves 0.86 Spearman
- SWE-Judge code evaluation Kappa: 24-67 (need 80+). 90% human agreement may be unreachable for code quality
- k=5 paired runs is underpowered — need k=20-30 for meaningful comparisons

### The System Is Over-Engineered For One Person
- 45 agents + 13 skills + 9 gates + SPRT + 3-layer + DSPy = team-scale infrastructure for a solo developer
- Zero product features shipped in 2 weeks of building this system
- The "claude-meta" pattern achieves ~80% of the value at ~20% of the complexity
- Production companies (OpenAI, LangChain, Maxim) use simpler loops than what we designed
- Opportunity cost probability: **85%** — this is the most likely way the project fails

### But The Core Architecture Is Sound
- 3-layer prompt resolution is good (production systems use 4-6 layers, we need canary not GEPA)
- Eval functions are the right permanent investment
- eval_history.jsonl as training data is correct
- Per-agent contract scoring is the right credit assignment approach
- The safety-gated transition (Paradigm 2 → 3) is well-reasoned

---

## The Revised Architecture

Based on all adversary evidence, here's what changes:

### DROP (Over-Engineered, No Evidence It Works For Us)

| Component | Why Drop | Replace With |
|-----------|---------|-------------|
| DSPy GEPA integration | No evidence for agent doctrines, $7K+ fleet cost, 5-20 examples insufficient | Claude-native self-critique (claude-meta pattern) |
| SPRT rollback | k=5 is underpowered, theater at our data volumes | Simple "score improved on 3+ paired runs? keep it" + human spot-check |
| DSPy adapter (Proxy Predict) | No production evidence, "weird hacks" reported | Not needed if using Claude-native approach |
| Holdout eval signals | Premature — need basic eval working first | Defer until eval is validated against human judgment |
| prompt_engine.py | Over-abstraction for current stage | Claude reads scores, reflects, writes improvements |

### KEEP (Validated, Future-Proof)

| Component | Why Keep |
|-----------|---------|
| 3-layer prompt resolution | Sound architecture, production-validated pattern. Add canary phase later. |
| eval_gate.py deterministic checks | Necessary but not sufficient. Keep as structural gate. |
| eval_history.jsonl | Training data accumulation — correct regardless of optimizer |
| Version directories (22 agents) | Ready for when optimization starts |
| Per-agent contract scoring | Correct credit assignment approach |
| Safety-gated phases | Well-reasoned transition path |

### ADD (Missing, High-Value)

| Component | Why Add | Effort |
|-----------|---------|--------|
| **30-50 human-labeled ground truth** | Can't validate ANY eval approach without this. Literally the #1 blocker. | 2-3 hours of your time |
| **Claude-native self-critique loop** | Replace DSPy GEPA. After each run, Claude reads eval scores + output, reflects, proposes prompt improvement. Zero Python infrastructure. | ~0 lines (it's a prompt pattern) |
| **Rebuild LLM judge with Opus** | Gemini Flash was bad implementation, not bad idea. Opus achieves 0.86 Spearman. Use 1-5 scale with rubric + chain-of-thought. | ~50 lines in eval_gate.py |
| **Anti-gaming checks** | Actually run regression tests (don't trust self-reported fields). Verify URLs. Parse Given/When/Then into stubs. | ~100 lines across scorers |
| **Golden set smoke test** | Before every optimization cycle, run scorer against known-good and known-bad output. If scores are wrong, scorer is broken. | ~30 lines |
| **Hard deadline: April 1** | If system isn't demonstrably saving time by then, freeze and ship product. | 0 lines |

---

## The Simplified Loop

```
BEFORE (Over-Engineered):
  Agent runs → eval_gate scores → SPRT decides → DSPy GEPA optimizes
  → writes to Layer 1 → SPRT validates → promote/rollback
  (Requires: DSPy adapter, GEPA, SPRT, version tracking, holdout signals)

AFTER (Evidence-Based):
  Agent runs → eval_gate scores (deterministic + Opus judge)
  → Claude reads scores + output → reflects on what went wrong
  → proposes prompt improvement → human spot-checks weekly
  → if improvement confirmed, write to Layer 1
  (Requires: eval_gate, Opus judge prompt, the feedback pattern)
```

The 3-layer resolution still works — Layer 1 is where improvements go, Layer 2 is the safety net. But the OPTIMIZER is Claude itself, not an external framework.

---

## Confidence Assessment

| Decision | Confidence | Evidence Strength |
|----------|-----------|------------------|
| Drop DSPy GEPA for now | **90%** | Practitioner reports + data insufficiency + cost analysis |
| Keep 3-layer resolution | **95%** | Production-validated pattern across multiple companies |
| Keep eval_gate.py | **95%** | Every approach needs a scorer, deterministic checks are necessary |
| Add Claude-native self-critique | **80%** | Multiple independent implementations (claude-meta, claude-reflect) but no rigorous comparison |
| Add Opus LLM judge | **85%** | 0.86 Spearman correlation (Anthropic Bloom), our Flash implementation was flawed |
| Add human-labeled ground truth | **99%** | Every source across all 10 research tracks agrees this is mandatory |
| Set hard deadline (April 1) | **95%** | Opportunity cost is the #1 risk factor |

**Overall architecture confidence: ~90%.** The remaining 10% uncertainty is whether Claude-native self-critique is as effective as GEPA for prompt optimization. We won't know until we try both. But GEPA can't work at our data volumes anyway, so the comparison is moot for now.

---

## The 100-Hour Plan Implications

Before building the 100-hour plan, these adversary findings change the scope:

1. **Hours 1-3:** Human-label 30 outputs across skills (ground truth)
2. **Hours 4-8:** Rebuild LLM judge with Opus (replace Gemini Flash)
3. **Hours 9-12:** Add anti-gaming checks to eval_gate (verify self-reported fields)
4. **Hours 13-15:** Add golden set smoke test for scorer validation
5. **Hours 16-20:** Implement Claude-native self-critique loop (replace DSPy plan)
6. **Hours 21-40:** Run skills on holus + other repos, accumulate eval data
7. **Hours 41-60:** Ship Holus features using the improved skills
8. **Hours 61-80:** Evaluate: is the system saving time? If yes, continue. If no, freeze.
9. **Hours 81-100:** Either deepen (add GEPA when data sufficient) or pivot to product work

The key shift: **Hours 41-60 are product work**, not infrastructure work. The adversary's core critique — "zero product features shipped" — must be addressed by making the plan product-focused, not meta-focused.

---

## Sources (Across All 5 Adversary Tracks)

### GEPA Limitations
- [Contra DSPy and GEPA — Benjamin Anderson](https://benanderson.work/blog/contra-dspy-gepa/)
- [DSPy Save/Load Bug PR #8093](https://github.com/stanfordnlp/dspy/pull/8093)
- [DSPy Module Freezing Issue #8800](https://github.com/stanfordnlp/dspy/issues/8800)
- [Maxime Rivest: Hacking DSPy for System Prompts](https://maximerivest.com/posts/automatic-system-prompt-optimization.html)

### 3-Layer Failure Modes
- [When "Better" Prompts Hurt (arXiv:2601.22025)](https://arxiv.org/html/2601.22025v1)
- [SPRT Power Comparison (Analytics Toolkit)](https://blog.analytics-toolkit.com/2022/comparison-of-the-statistical-power-of-sequential-tests/)
- [LaunchDarkly AI Configs](https://launchdarkly.com/blog/ai-configs-ga-runtime-control-prompts-models/)
- [Braintrust Prompt Versioning](https://www.braintrust.dev/articles/what-is-prompt-versioning)

### Eval Quality
- [Anthropic Bloom: 0.86 Spearman (Opus)](https://www.anthropic.com/research/bloom)
- [ICLR 2025: Null Model 86.5% AlpacaEval](https://arxiv.org/html/2410.07137v1)
- [SWE-Judge: Kappa 24-67 for Code](https://arxiv.org/html/2505.20854v1)

### Alternative Architectures
- [claude-meta: Self-Improving via CLAUDE.md](https://github.com/aviadr1/claude-meta)
- [Evidently AI: Simple Prompt Optimization Loop](https://www.evidentlyai.com/blog/automated-prompt-optimization)
- [OpenAI Self-Evolving Agents Cookbook](https://cookbook.openai.com/examples/partners/self_evolving_agents/autonomous_agent_retraining)
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### Pre-Mortem
- [METR: o3 Reward Hacking 14/20](https://metr.org/blog/2025-06-05-recent-reward-hacking/)
- [METR: Developer Productivity Experiment](https://metr.org/blog/2026-02-24-uplift-update/)
- [Judge's Verdict: Human Agreement Kappa 0.801](https://arxiv.org/html/2510.09738v1)
