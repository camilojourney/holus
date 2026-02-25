# Vision -- Holus

## One Sentence

Holus becomes the federated AI operating system that runs a solo founder's entire portfolio -- trading, content, code, and creative -- through coordinated autonomous agents that learn from each other without tight coupling.

---

## Why This Exists

Solo founders cannot scale beyond their own hours. Hiring is expensive, slow, and introduces management overhead that defeats the purpose of being solo. The alternative -- dozens of disconnected automations, cron jobs, and scripts -- creates a maintenance burden that grows faster than the value it produces.

The insight: a federated system of AI agents, each owning one domain, sharing a lightweight event bus for cross-project learning, captures 80% of the value of a unified AI OS while avoiding the compound error problem that makes unified systems brittle. Every production multi-agent system studied (Replit, Vercel, Cognition/Devin, Anthropic) converges on this same pattern: independent agents with bounded communication channels.

Holus is not a chatbot. It is not a wrapper around Claude. It is an operational system where agents make real decisions -- execute trades, publish content, review code, optimize workflows -- with safety guardrails, memory, and genuine self-improvement loops.

The core philosophy: **intelligence is the primary constraint, not cost.** Every agent runs on the highest-capability model available. Claude Opus 4 handles strategic decisions. Claude Sonnet 4.5 handles high-volume operations. The Mac Mini serves as infrastructure only -- databases, orchestration, workflow automation, memory systems -- not as an AI inference layer. When you are paying for maximum intelligence, the marginal cost of smarter decisions far exceeds the marginal cost of API tokens.

---

## What Success Looks Like

### Phase 1 (Months 1-2): Foundations

- Infrastructure running: PostgreSQL, Redis, n8n, Temporal, Langfuse via Docker Compose
- Configuration management working: YAML + env vars + pydantic-settings
- Claude API client operational with prompt caching (>80% cache hit rate)
- Kill switch system tested from CLI, SSH, and webhook
- Event bus publishing and consuming events between agents

### Phase 2 (Months 2-4): Independent Agents

- **4 autonomous agents** running daily with <5% error rate requiring human intervention
- **Trading agent** achieves Sharpe ratio >1.0 on paper trading within 60 days, graduates to live
- **Content pipeline** publishes 30+ pieces/month across 13 platforms with measurable engagement growth
- **Coding agent** handles 70%+ of routine PRs (reviews, bug fixes, dependency updates) autonomously
- **Pilaster agent** manages ComfyUI workflows with version control and quality assessment
- DSPy prompt optimization running monthly on all agents (15-30% accuracy improvement per cycle)

### Phase 3 (Months 4-6): Federated Intelligence

- **Cross-project learning** produces at least 1 actionable insight per week
- Cognee knowledge graph stores 100+ cross-project relationships
- Coordinator daily synthesis identifies optimization opportunities across all agents
- Self-improvement loop operational: Manager -> Code Improver -> Judge -> Optimizer

### Ongoing Metrics

- **Total cost** stays under $500/month for full intelligence-forward operation
- **Recovery time** from any single agent crash is <5 minutes (automatic restart, no data loss)
- **Founder cognitive load** drops: system is understandable and debuggable at 2 AM
- **Compound error rate** stays below 5% per agent session

---

## What We Explicitly Don't Do

- **Local LLM inference for reasoning** -- we use cloud Claude (Opus 4 + Sonnet 4.5). Local models save tokens but sacrifice the reasoning quality that makes agents genuinely useful. The Mac Mini runs infrastructure, not intelligence. Exception: FinBERT for financial sentiment classification (specialized fine-tuned model, not a reasoning task).

- **Real-time trading** -- we use daily/swing timeframes. Sub-second execution requires co-located infrastructure and latency optimization that is a completely different system.

- **General-purpose chatbot** -- Holus is not a conversational interface. It is a headless operational system triggered by schedules, events, and webhooks. There is no chat UI.

- **Multi-tenant / SaaS** -- this is built for one founder's portfolio. No user management, no billing, no multi-tenancy abstractions. If this ever becomes a product, it is a complete rewrite.

- **Custom model training** -- we optimize prompts (DSPy, TextGrad, Reflexion), not weights. Fine-tuning is a supplement for classification tasks via LoRA on local 7B-8B models, not a core capability.

- **Unified real-time orchestration** -- the coordinator runs daily, not in real-time. Making it real-time reintroduces the compound error and coordination overhead the federated architecture avoids. If the coordinator becomes too complex, the system degrades to independent agents with no rewrite.

- **Multiple LLM providers** -- Claude-only. Adding GPT-4, Gemini, or others triples the operational complexity (three prompt formats, three caching strategies, three failure modes) for marginal intelligence gains.

---

## Related Documents

- [ADR-0001: Federated over unified](decisions/0001-federated-over-unified.md)
- [ADR-0002: Claude-first intelligence](decisions/0002-claude-first-intelligence.md)
- [ADR-0003: LangGraph for agents](decisions/0003-langgraph-for-agents.md)
- [Roadmap](roadmap.md)

---

## Last reviewed: 2026-02
