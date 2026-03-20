# ADR-0002: Claude-First Intelligence Layer (No Local LLMs for Reasoning)

## Status

Accepted

## Context

Every agent in Holus needs an LLM for reasoning, planning, and decision-making. The choice is between:

1. **Cloud-only:** All reasoning goes through Claude Opus 4 (strategic) and Claude Sonnet 4.5 (operational) via the Anthropic API.
2. **Hybrid:** Use local open-source models (Llama 3, Mistral, Phi-3) on the Mac Mini M4 for routine tasks, Claude for complex tasks only.
3. **Local-first:** Run quantized models locally for most tasks, use Claude only as a fallback.

The Mac Mini M4 (16GB or 24GB) can run quantized 7B-8B parameter models via MLX. These are adequate for classification and extraction tasks but perform significantly worse on multi-step reasoning, planning, and novel problem-solving -- exactly the tasks that determine agent quality.

The AI-Trader benchmark (HKUDS, December 2025) found that "general intelligence does not automatically translate to effective trading capability, with most agents exhibiting poor returns and weak risk management." The key word is *general* -- a properly prompted, memory-equipped frontier model significantly outperforms generic setups. This holds across all four domains: trading risk evaluation, content strategy synthesis, complex code debugging, and workflow optimization analysis.

## Decision

**Claude-first, always.** Every agent runs on Claude. The routing logic is simple:

- **Claude Opus 4** ($15/$75 per MTok input/output): Strategic decisions, risk validation, cross-project synthesis, complex debugging, architecture decisions, weekly reviews, prompt optimization, novel problem-solving.
- **Claude Sonnet 4.5** ($3/$15 per MTok input/output): Content generation, routine code review, standard signal evaluation, image quality assessment, documentation, test generation, data extraction, summarization.

**No local models for reasoning.** The Mac Mini runs infrastructure (databases, orchestration, workflow automation, memory systems) and specialized ML (FinBERT for sentiment classification, ComfyUI for image generation) -- tasks where local hardware is the right tool. Cloud APIs handle all LLM reasoning.

**Cost optimization without sacrificing intelligence:**

| Technique | Savings | How |
|-----------|---------|-----|
| Prompt caching | 60-70% | Stable system prompt prefix cached at 90% discount |
| Batch API | 50% | Non-urgent tasks (weekly reports, DSPy runs, content drafts) |
| Opus/Sonnet routing | 40-60% | Only use Opus when the decision matters |

Estimated total API cost: $140-210/month for all four agents combined.

## Consequences

### Positive

- **Maximum reasoning quality** on every decision that matters (trading risk, content strategy, code architecture)
- **Simpler infrastructure:** No model hosting, no GPU memory management, no quantization debugging
- **Always up-to-date:** Claude improves without us redeploying anything
- **Prompt caching** reduces costs dramatically without quality loss
- **Single provider:** One API key, one billing relationship, one set of documentation

### Negative

- **API dependency:** If Anthropic has an outage, all agents stop reasoning (launchd will retry on the next scheduled cycle)
- **Cost floor:** Cannot drop below ~$140/month even with aggressive optimization. Local models would be $0 inference after setup.
- **Latency:** Cloud API calls add 1-3 seconds per reasoning step vs. ~200ms for local inference
- **Privacy:** All reasoning data passes through Anthropic's API (mitigated by their enterprise privacy guarantees on API traffic)

### Risks

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Anthropic API outage | Low | launchd retries on next scheduled cycle; Python agent loop handles transient errors with backoff |
| Significant price increase | Low | Prompt caching and Batch API provide buffer; architecture allows adding Sonnet for more tasks |
| Model quality regression on update | Very Low | Pin model versions (`claude-opus-4-6`, `claude-sonnet-4-6`); test before migrating |

## Alternatives Considered

### Alternative A: Hybrid Local + Cloud

- Use Llama 3 70B (quantized) locally for routine tasks, Claude for strategic only
- Rejected because: 16GB Mac Mini cannot run 70B models. 7B-8B models are adequate for classification but significantly worse at multi-step reasoning. The marginal API cost savings (~$50-80/month) does not justify the infrastructure complexity and quality degradation on operational tasks.

### Alternative B: Local-First with Claude Fallback

- Run quantized Phi-3 or Mistral locally for most tasks, escalate to Claude when confidence is low
- Rejected because: Requires building a confidence-based routing system, managing model loading, and accepting degraded quality on the majority of tasks. The "fallback" model becomes a crutch that is rarely triggered, meaning most decisions are made by the weaker model.

### Alternative C: Multi-Provider (Claude + GPT-4 + Gemini)

- Route tasks to the best model per benchmark for each task type
- Rejected because: Adds three API relationships, three prompt formats, three caching strategies, and three failure modes. Benchmark differences between frontier models are small; operational complexity differences are large.

## References

- [AI_OS_Blueprint_Intelligence_First.md](../../AI_OS_Blueprint_Intelligence_First.md) -- Intelligence tier section
- [HOLUS-ARCHITECTURE-DECISIONS.md](../../HOLUS-ARCHITECTURE-DECISIONS.md) -- Section 6: Cost Optimization
- AI-Trader benchmark (HKUDS, Dec 2025): general intelligence vs. domain-specific trading capability
- Anthropic prompt caching documentation: 90% read discount, 5-minute TTL

---

**Date:** 2026-02-24
**Author:** Camilo Martinez
