---
last_updated: 2026-03-04
review_cadence: 30d
next_review: 2026-04-03
owner: juan
dependent_specs: []
---

# Stack Research — Holus

Last updated: 2026-03-04
Review cadence: 30 days (AI/ML stack changes fast)
Next review: 2026-04-03

---

## 1. Orchestration Framework

### 1.1 Current State

Holus uses LangGraph for agent orchestration. Decision made at project inception based on its human-in-the-loop capabilities and Python-native API.

### 1.2 Options Evaluated

| Framework | HITL Support | State Persistence | Multi-Agent | License | Verdict |
|-----------|-------------|------------------|-------------|---------|---------|
| LangGraph | Native `interrupt()` API | Built-in checkpointers | Supervisor + Swarm patterns | MIT | **Selected** — best HITL primitives |
| LangChain Agents | Limited | External only | Basic | MIT | Rejected — no native HITL |
| CrewAI | Task-level only | Limited | Yes | MIT | Rejected — less flexible |
| Custom Python | Manual | Manual | Manual | — | Rejected — reinventing the wheel |

### 1.3 LangGraph Key Facts

- **License:** MIT open source — free to use [VERIFIED — langchain.com/langgraph, 2026-03-04]
- **Control flows:** Single agent, multi-agent, hierarchical — all in one framework [VERIFIED — langchain.com/langgraph, 2026-03-04]
- **Memory:** Built-in memory stores conversation history and maintains context across sessions [VERIFIED — langchain.com/langgraph, 2026-03-04]
- **Streaming:** Native token-by-token streaming for real-time UX [VERIFIED — langchain.com/langgraph, 2026-03-04]
- **Production adoption:** AWS published official LangGraph + Amazon Bedrock multi-agent guide (April 14, 2025) [VERIFIED — aws.amazon.com/blogs/machine-learning, April 2025]

### 1.4 Update Trigger

New LangGraph major version, new HITL primitive, breaking API change.

---

## 2. LLM Models

### 2.1 Current Model Strategy

Holus uses Claude exclusively (one provider = one prompt format, one cache, one failure mode).

### 2.2 Claude API Pricing (verified 2026-03-04)

| Model | Input (per MTok) | Output (per MTok) | Cache Hit | Context | Role in Holus |
|-------|-----------------|------------------|-----------|---------|---------------|
| Claude Opus 4.5 | $5.00 | $25.00 | $0.50 | 200K | Strategy decisions |
| Claude Opus 4.6 | $5.00 | $25.00 | $0.50 | 200K | Strategy decisions (latest) |
| Claude Sonnet 4 | $3.00 | $15.00 | $0.30 | 200K | Content generation (high volume) |
| Claude Sonnet 4.5 | $3.00 | $15.00 | $0.30 | 200K | Content generation (high volume) |
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.10 | 200K | Health checks, monitoring |
| Claude Haiku 3.5 | $0.80 | $4.00 | $0.08 | 200K | Monitoring (cheapest) |

[VERIFIED — platform.claude.com/docs/en/about-claude/pricing, accessed 2026-03-04, Grade A]

**Prompt caching multipliers:**
- 5-min cache write: 1.25× base input price
- 1-hour cache write: 2× base input price
- Cache read (hit): 0.10× base input price

### 2.3 Model Selection per Task

| Task | Model | Rationale |
|------|-------|-----------|
| Content strategy (weekly analysis, platform decisions) | Opus 4.5 | Requires genuine reasoning; low frequency justifies cost |
| Content generation (copywriting, translation, adaptation) | Sonnet 4 | High-volume, good quality, 5× cheaper than Opus |
| Monitoring, health checks, simple routing | Haiku 4.5 | Cost-optimized for frequent, simple tasks |

### 2.4 Quality Notes

- Claude excels at creative writing quality and voice/personality [UNVERIFIED — Type.ai blog Jan 2026, Grade C, single source]
- Claude Opus 4.1 and Sonnet 4 (released May 2025) are hybrid reasoning models with extended thinking mode [VERIFIED — Type.ai Jan 2026, Grade B]

### 2.5 Cost Projections

| Scenario | Monthly Cost | Breakdown |
|----------|-------------|-----------|
| Weekly cycle × 52/year | ~$120/month | Opus strategy (~$40) + Sonnet content (~$70) + Haiku monitoring (~$10) |
| Daily cycle | ~$500/month | Opus strategy (~$200) + Sonnet content (~$280) + Haiku (~$20) |

*Based on typical content generation volumes, with prompt caching enabled for system prompts.*

### 2.6 Update Trigger

New Claude model release, pricing change, or Anthropic deprecation notice.

---

## 3. Translation Engine

### 3.1 Options Evaluated

| Engine | Strength | Weakness | Cost | Verdict |
|--------|----------|----------|------|---------|
| Claude (LLM) | Context, tone, cultural nuance, idiomatic marketing copy | Slower than MT-only systems | Already paid (part of LLM cost) | **Selected** — fits content pipeline |
| DeepL API | High fidelity, fewer literal errors (vendor claim) | Limited tone customization, extra API dependency | $7.49/month Starter, $57/month Advanced | Rejected — redundant with Claude |
| Google Translate API | Wide language support | Lower quality for creative content | Usage-based | Rejected — quality insufficient for marketing |

### 3.2 Evidence for LLM Translation

- For marketing content (where tone and cultural nuance matter), top LLMs deliver comparable or superior results to DeepL [VERIFIED — getblend.com Oct 2025, vincentschmalbach.com Apr 2025 — two independent secondary sources, Grade B]
- DeepL claims 2-3× fewer edits than Google Translate and 3× fewer than ChatGPT-4 in blind tests [UNVERIFIED — source is DeepL's own blog (deepl.com/en/blog/next-gen-language-model), vendor self-report, Grade C]
- ~~LLMs are 800x cheaper than DeepL~~ [PHANTOM — Reddit claim, no methodology, no source]

### 3.3 Recommendation

Use Claude Sonnet 4 for both content generation and EN↔ES translation in a unified pipeline. No additional translation API needed. Prompt engineering controls formality and cultural register.

---

## Sources

1. LangChain, "Agent Orchestration Framework for Reliable AI Agents", https://www.langchain.com/langgraph (accessed 2026-03-04)
2. LangChain, "Interrupts - Docs by LangChain", https://docs.langchain.com/oss/python/langgraph/interrupts (accessed 2026-03-04)
3. AWS, "Build multi-agent systems with LangGraph and Amazon Bedrock", https://aws.amazon.com/blogs/machine-learning/build-multi-agent-systems-with-langgraph-and-amazon-bedrock/ (April 14, 2025)
4. Anthropic, "Pricing - Claude API Docs", https://platform.claude.com/docs/en/about-claude/pricing (accessed 2026-03-04)
5. Type.ai Blog, "Who Wrote it Better? A Definitive Guide to Claude vs. ChatGPT vs. Gemini", https://blog.type.ai/post/claude-vs-gpt (January 31, 2026)
6. Vincent Schmalbach, "DeepL vs LLMs for Translation", https://www.vincentschmalbach.com/deepl-vs-llms-for-translation/ (April 25, 2025)
7. Blend, "Best LLMs for Translation in 2025: GPT-4 vs Claude, Gemini", https://www.getblend.com/blog/which-llm-is-best-for-translation/ (October 17, 2025)
8. DeepL, "DeepL's next-gen LLM outperforms ChatGPT-4, Google, and Microsoft", https://www.deepl.com/en/blog/next-gen-language-model (accessed 2026-03-04)
