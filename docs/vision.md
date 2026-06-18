# Vision -- Holus

## One Sentence

Holus is the Thought Studio for a solo founder's content portfolio -- one thought
from a person or online source becomes platform-native text, images, carousels,
reviewed posts, scheduled publishing, and learning.

---

## Why This Exists

Solo founders cannot scale beyond their own hours. Hiring is expensive, slow, and introduces management overhead that defeats the purpose of being solo. The alternative -- dozens of disconnected automations, cron jobs, and scripts -- creates a maintenance burden that grows faster than the value it produces.

The insight: a federated system of AI agents, each owning one domain, sharing a lightweight event bus for cross-project learning, captures 80% of the value of a unified AI OS while avoiding the compound error problem that makes unified systems brittle. Every production multi-agent system studied (Replit, Vercel, Cognition/Devin, Anthropic) converges on this same pattern: independent agents with bounded communication channels.

Holus is not a chatbot. It is not a wrapper around Claude. It is an operational
system where agents turn source thoughts into useful content sets, brief visual
specialists, schedule publishing through Holus Social API, and evaluate what
worked -- with safety guardrails, memory, and genuine self-improvement loops.

The core philosophy: **intelligence is the primary constraint, not cost.** Every agent runs on the highest-capability model appropriate for its task. Claude Opus handles strategic decisions. Claude Sonnet handles high-volume content generation and evaluation. The Mac Mini serves as infrastructure only -- databases, orchestration, workflow automation, memory systems -- not as an AI inference layer.

---

## What Success Looks Like

### Phase 1 (Months 1-2): One Working Loop

- Thought Studio creates content sets from text and URL thoughts
- Text, image, and carousel variants render locally and enter human review
- Holus Social API is wired for explicit dry-run, schedule, and publish calls
- 4+ content pieces per week across active products and founder thoughts
- Every decision logged to `trajectory.jsonl` — the memory that makes learning possible
- Observatory dashboard reads from file-based state: agent status, recent decisions, evaluation scores

### Phase 2 (Months 2-4): Autonomous Output at Scale

- **Content pipeline** publishes 30+ pieces/month across 13 platforms with measurable engagement growth
- **32 agents** running with <5% error rate requiring human intervention
- **Self-improvement loop** operational: JudgeAgent evaluates outputs → patterns extracted weekly → prompt variants A/B tested
- **Cost discipline**: full intelligence-forward operation under $500/month

### Phase 3 (Months 4-6): Compounding Intelligence

- Performance data is rich enough to detect what content categories convert per product
- Coordinator synthesis identifies cross-product patterns (e.g., tutorial posts for Pilaster drive invoz signups)
- Prompt optimizer has run 3+ cycles with statistically significant A/B test results
- Observatory dashboard serves as a portfolio artifact: shows a fully autonomous agent system operating live

### Ongoing Metrics

- **Total cost** stays under $500/month for full intelligence-forward operation
- **Recovery time** from any single agent crash is <5 minutes (automatic restart, no data loss)
- **Founder cognitive load** drops: system is understandable and debuggable at 2 AM
- **Compound error rate** stays below 5% per agent session

---

## Agent Intelligence System

Holus operates as a team of 32 agents organized the way a senior marketing director builds a team: a strategist at the top, specialist teams by content category, domain-expert evaluators, and ops agents running the plumbing.

### The Brain: marketing-strategist (ReAct loop)

One Opus-powered manager runs the full thought -> content set -> review ->
schedule/post -> learn cycle. It reads analytics from Holus Social API, decides
what content will drive growth, briefs the right specialist team, and logs every
decision for the learning loop.

### Specialist Teams (22 agents, 6 categories)

**Written Authority** (50% of output) — the highest-ROI category:
- `hook-architect` — opens that stop the scroll
- `storyteller` — narrative arc from founding to feature
- `technical-translator` — complex ideas made accessible
- `voice-guardian` — ensures every post sounds like the same person
- `cta-strategist` — converts readers into users

**Visual Content** (25%):
- `carousel-architect` — 5-10 slide educational carousels
- `data-visualizer` — metrics and benchmarks as shareable graphics
- `before-after-designer` — transformation stories as split visuals
- `brand-designer` — visual consistency across all products

**Future Video Content** (deferred):
- `script-writer` — short-form video scripts (60-90 seconds)
- `brief-composer` — production briefs for Genpeli when video becomes active
- `caption-specialist` — hooks, hashtags, platform-specific formatting

**Growth** (frequency-capped to avoid spam):
- `lead-magnet-designer` — downloadable tools and templates
- `comment-trigger-expert` — posts engineered to start conversations
- `community-builder` — relationship content that builds audience loyalty

**Research** (feeds all other specialists):
- `niche-researcher` — trend and topic discovery
- `seo-strategist` — keyword targeting and search intent
- `audience-analyst` — ICP refinement from engagement patterns
- `competitive-intel` — what competitors are doing that works

**Repurposing** (every piece × 4 platforms):
- `platform-adapter` — LinkedIn post → Twitter thread → Instagram caption
- `bilingual-localizer` — English and Spanish versions
- `format-converter` — text → carousel brief, blog → script

### Evaluators (7 domain-expert judges)

Not generic quality judges. Domain experts who know what good looks like in their category: a hook expert judges hooks, an SEO expert judges SEO, a narrative expert judges storytelling. Each evaluator returns a score + structured critique that feeds the learning loop.

### Ops Agents (2)

- `security-sentinel` — scans for leaked credentials, reviews API usage anomalies
- `knowledge-keeper` — maintains `.self-improvement/MEMORY.md` and extracts patterns from trajectory data

### Agent Registry

`agents/AGENTS.yaml` is the single source of truth for all 32 agents: name, model, role, input/output contract, and which evaluation rubric applies.

---

## Self-Improvement Loop

Every content output is evaluated. Every evaluation feeds learning. The system gets measurably better over time.

**JudgeAgent** evaluates every content piece using domain-specific rubrics -- not "is this good?" but "does the hook follow the 3-second rule?", "is the CTA specific and low-friction?", "does this match the product's audience profile?"

**Weekly pattern extraction** reads `trajectory.jsonl` and identifies what is working: which content categories are outperforming, which platforms are rewarding which post structures, which specialist combinations produce the best evaluation scores.

**Prompt optimizer** A/B tests prompt variants once enough data has accumulated. Variant A ships to 50% of runs, variant B to the other 50%. After 20+ samples, the winner becomes the new baseline. Tracked in `config/prompts/`.

**Reflexion** provides verbal reinforcement learning: after each cycle, the agent reads its own trajectory and writes a short reflection on what it would do differently. This reflection seeds the next cycle's reasoning.

**Langfuse tracing** provides full observability: tokens, cost, latency, and evaluation scores per agent per run. The Observatory dashboard reads from Langfuse and `eval_history.jsonl` to surface trends.

---

## Three-Layer Prompt Architecture

Prompts are the product. Code is the plumbing.

**Layer 1 — Human-authored baselines** (`agents/*.md`): Written by hand, following the KERNEL template (Role, Scope, Steps, Negatives, Output Contract, Contrastive Examples). Git-versioned. These are the source of truth for agent behavior.

**Layer 2 — Optimizer-generated variants** (`config/prompts/`): A/B test variants produced by the prompt optimizer. Named by agent + variant ID. Never edited by hand -- only the optimizer writes here.

**Layer 3 — Hardcoded constants** (Python): Migration fallback only. If the prompt file cannot be loaded, the agent uses a minimal hardcoded version that keeps the system alive while the file issue is debugged.

Promotion path: optimizer generates a variant → A/B test runs → winner gets promoted to Layer 1 by a human → old variant archived.

---

## Observatory Dashboard

Holus runs headless. But the work it does should be visible -- both for operational debugging and as a portfolio artifact for interviews and demos.

The Observatory is a FastAPI backend + Next.js 15 frontend that reads from existing file-based state. No new database. It reads `trajectory.jsonl`, `AGENTS.yaml`, `eval_history.jsonl`, and Langfuse to surface:

- **Agent status grid** -- which agents ran today, last run time, success/error
- **Trajectory timeline** -- a chronological feed of decisions and their rationale
- **Content pipeline kanban** -- content in-flight: researching → drafted → evaluated → published
- **Evaluation scores over time** -- per-agent quality trends by content category
- **Cost tracking** -- daily/weekly spend per agent, actual vs. budget
- **Knowledge browser** -- searchable view of `.self-improvement/MEMORY.md` and lessons
- **System health** -- MCP silo connectivity, Redis, Langfuse

Dual purpose: day-to-day operations + interview demo. A live dashboard showing a fully autonomous 32-agent content system is a stronger portfolio signal than any résumé line.

---

## What We Explicitly Don't Do

- **Local LLM inference for reasoning** -- we use cloud Claude (Opus + Sonnet). Local models save tokens but sacrifice the reasoning quality that makes agents genuinely useful. The Mac Mini runs infrastructure, not intelligence. Exception: FinBERT for financial sentiment classification.

- **Real-time trading** -- Holus is a marketing system. pythia and milo-to-the-moon are completely isolated and never touched by Holus.

- **General-purpose chatbot** -- Holus is a headless operational system triggered by schedules, events, and webhooks. The Observatory is read-only. There is no chat UI.

- **Multi-tenant / SaaS** -- built for one founder's portfolio. No user management, no billing, no multi-tenancy abstractions.

- **Custom model training** -- we optimize prompts (A/B testing, Reflexion), not weights. Fine-tuning is a supplement for classification tasks, not a core capability.

- **Multiple LLM providers** -- Claude-only. Adding GPT-4, Gemini, or others triples operational complexity for marginal intelligence gains.

- **Unified real-time orchestration** -- the marketing-strategist runs weekly, not in real-time. Making it real-time reintroduces the compound error and coordination overhead the federated architecture avoids.

---

## Related Documents

- [ADR-0001: Federated over unified](decisions/0001-federated-over-unified.md)
- [ADR-0002: Claude-first intelligence](decisions/0002-claude-first-intelligence.md)
- [ADR-0003: LangGraph for agents](decisions/0003-langgraph-for-agents.md)
- [Roadmap](roadmap.md)

---

## Last reviewed: 2026-03
