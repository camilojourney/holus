# Observatory Research Findings

Research date: 2026-03-12
Context: Holus Observatory dashboard — agent status, trajectory timeline, content pipeline kanban, eval scores, cost tracking. Backend: FastAPI + SSE + JSONL/YAML/MD files.

---

## Topic 1: Frontend Framework

### Framework Landscape (2026)

**Next.js 15/16**
- Bundle: 180–250 KB gzipped for medium apps
- In 2026 moved from v15 to v16, stabilizing Turbopack for production and graduating Partial Prerendering (PPR) toward GA
- React Server Components enable streaming responses — solid SSE support
- Massive ecosystem: 10x more chart/component options than SvelteKit
- Cognitive overhead: RSC boundaries, caching layers, and streaming cause real confusion
- Best fit: teams needing maximum rendering flexibility and React ecosystem breadth

**SvelteKit (Svelte 5 runes)**
- Bundle: 60–120 KB gzipped — 50%+ smaller than Next.js
- Svelte 5's runes system eliminates hook complexity; intuitive mutations instead of useState/useEffect
- Compiles to vanilla JS at build time — no React runtime overhead
- Native EventSource + SSE works cleanly; FastAPI + SvelteKit is a documented production pattern (testdriven.io tutorial exists)
- Fastest time-to-interactive for authenticated SaaS/dashboards
- Weaker component library ecosystem vs React, but catching up fast
- Enterprise contracts growing in 2026

**Remix (→ React Router v7 + Remix 3)**
- Bundle: 150–220 KB gzipped
- Merged into React Router v7 while reimagining Remix 3 as bundler-free
- Loader/action pattern excellent for form-heavy tools — less optimized for real-time streaming scenarios
- Less natural fit for agent monitoring dashboards vs Next.js or SvelteKit

**Astro**
- Designed for content sites, not interactive dashboards — not relevant here

### SSE Support (all frameworks)

All three frameworks support SSE via the native browser `EventSource` API. The pattern with FastAPI + SSE is:
- Backend: `sse-starlette` library, `EventSourceResponse` generator
- Frontend: `new EventSource(url)` with named event listeners
- Gotchas: CORS config required; connection cleanup on component teardown to prevent memory leaks; keep last N readings to prevent unbounded array growth

SvelteKit integrates most naturally with FastAPI SSE (both non-Node stacks), and the testdriven.io guide covers this exact pairing.

### Component Library Comparison

**shadcn/ui**
- Copy-paste approach (you own the code, no runtime dependency)
- ~50 KB gzipped typical dashboard
- Full Tailwind control, brand-exact customization
- Pairs naturally with Next.js App Router ecosystem
- No built-in chart components — requires pairing with a chart library

**Tremor**
- Purpose-built for analytics dashboards
- ~200 KB gzipped (heavier)
- 35–40+ pre-styled dashboard components: KPI cards, sparklines, area charts, metric tables
- Built on Recharts + Radix UI + Tailwind
- "Show the data, hide the chrome" philosophy — minimal decoration, maximum clarity
- Fastest path from zero to polished dashboard (hours, not days)
- Limitation: cannot drop down into lower-level Recharts APIs; customization ceiling

**The 2026 consensus pattern:** Use shadcn/ui as the base component library, pull in Tremor for charts/KPI cards, use Recharts directly when you need more control.

**Recharts**
- Built on React virtual DOM + SVG rendering
- Only re-renders changed chart segments — good for real-time with moderate data volumes
- Ideal for datasets under 10,000 points
- High customizability; Tremor is built on top of it

**ECharts (Apache)**
- Canvas rendering; better for high-frequency real-time updates with large datasets
- More complex API than Recharts

### Comparison Table

| Dimension | Next.js 16 | SvelteKit 5 | Remix 3 |
|-----------|-----------|-------------|---------|
| Bundle size | 180–250 KB | 60–120 KB | 150–220 KB |
| SSE support | Yes (RSC streaming) | Yes (native EventSource) | Yes |
| FastAPI pairing | Good | Excellent | Good |
| Chart libraries | Largest selection | Growing | React-based |
| Component ecosystem | Largest | Smaller but usable | React-based |
| Dev velocity (dashboard) | Medium | High | Low |
| Cognitive overhead | High (RSC/cache) | Low | Medium |
| Real-time perf | Good | Best | Good |
| 2026 momentum | Strong | Growing fast | Declining |

| Component Library | Bundle | Dashboard-ready | Customization | Chart support |
|-------------------|--------|-----------------|---------------|---------------|
| Tremor | ~200 KB | Excellent (built for this) | Limited | Built-in (on Recharts) |
| shadcn/ui | ~50 KB | Good (requires assembly) | Full | None (bring your own) |
| shadcn + Recharts | ~120 KB | Very good | High | Excellent |
| shadcn + Tremor (hybrid) | ~200 KB | Best | Medium-High | Excellent |

### Recommendation

**SvelteKit + shadcn/ui (SvelteKit port) + Tremor charts** is the fastest path to a polished Holus Observatory dashboard.

Rationale:
1. SvelteKit + FastAPI SSE is a proven, documented pairing — the backend is already FastAPI
2. Smallest bundle → best time-to-interactive for an always-on monitoring UI
3. Tremor's pre-built KPI cards, sparklines, and area charts cover all Observatory needs: agent status, eval scores, cost tracking, pipeline kanban
4. Runes-based reactivity is a natural fit for live-streaming data (agent state updates, eval scores flowing in)
5. If the team is already React-fluent, Next.js 16 + shadcn + Tremor is a solid fallback with larger ecosystem

**If React is non-negotiable:** Next.js 16 + shadcn/ui + Tremor. Skip Remix for this use case.

---

## Topic 2: Agent Observability

### How Companies Monitor Multi-Agent Systems in 2026

The core insight from 2026 industry practice: traditional uptime monitoring is insufficient for AI agents. The key shift is from "is it up?" to "how is it behaving?"

**The four observability layers:**
1. **Traces** — reconstruct the complete decision path for any agent interaction. Every LLM call, tool invocation, retrieval step, and intermediate decision gets captured with full context. Analogous to a call stack for AI.
2. **Metrics** — quantitative: response times, token usage, cost per request, error rates, success rates per task type
3. **Logs** — prompt/response/tool-call logging for replay and regression detection
4. **Evaluations** — LLM-as-judge or custom scorers running on live traffic (not just offline evaluation)

**Multi-agent specific patterns:**
- Nested spans showing interactions between agents (parent-child trace hierarchy)
- Per-agent cost attribution via metadata tags on every LLM call
- Agent-loop amplification tracking (a single user request can fan out into 10+ LLM calls)
- Tool call frequency and error rates per agent
- OpenTelemetry semantic conventions for GenAI are emerging as the standard for cross-framework tracing

**Microsoft Azure's top 5 practices (from Azure AI blog):**
1. Benchmark-driven model selection before deployment
2. Continuous evaluation across intent resolution accuracy, tool selection effectiveness, task adherence, response completeness, safety
3. CI/CD pipeline integration — every code change tested for quality and safety
4. Adversarial red teaming pre-production
5. Production monitoring with unified dashboards: traces + metrics + evaluations + alerts for drift

### Tool Comparison

| Dimension | Langfuse | LangSmith | Lunary | Phoenix (Arize) |
|-----------|----------|-----------|--------|-----------------|
| Open source | Yes (MIT) | No | Yes (Apache-2.0) | Yes (OSS core) |
| Self-hosting | Well-documented | Enterprise only | Yes, SOC2+ISO27001 | Yes (PostgreSQL) |
| Multi-agent tracing | Sessions + chains | LangGraph-native | Real-time + auto-categorize | OTel distributed tracing |
| Cost tracking | Per-generation with metadata tags | Built-in live dashboards | Token/cost/latency | Basic; evaluation-focused |
| Quality scoring | LLM-as-judge + user feedback | Dataset evals | Auto-categorize (Radar) + PII masking | Hallucination detection + relevance scoring |
| Agent-specific metrics | Trace filtering by agent tag | Tool popularity + error rates per agent | Conversation analytics | Multi-step agent trajectory analysis |
| Pricing (free tier) | 50K events/mo | 5K traces/mo | 10K events/mo | Unlimited (self-hosted) |
| Pricing (paid) | Cloud available | $39/user/mo | $20/user/mo | Phoenix Cloud available |
| Framework coupling | Framework-agnostic | LangChain/LangGraph only | Framework-agnostic | OpenTelemetry standard |
| Unique strength | Open-source flexibility; works with everything | Zero-config for LangChain | Security focus; compliance | No vendor lock-in; OTel native |

**Lunary detail:** Apache-2.0, self-hostable, SOC 2 Type II + ISO 27001 certified. Tracks cost, token usage, latency. Strong on conversation/agent monitoring with real-time analytics. "Radar" feature auto-categorizes outputs. Available on AWS Marketplace (Enterprise Edition).

**Phoenix/Arize detail:** Phoenix is the open-source self-hosted version (good for development + production on own infra). Arize AX is the enterprise SaaS version ($50K–100K/year). Phoenix supports 50+ LLMs, multi-step agent trajectory analysis, and drift detection. OpenTelemetry-native means traces can be consumed by multiple platforms — no lock-in.

### Per-Agent Cost Tracking Approaches

Two dominant patterns:

**1. Metadata tagging (all platforms)**
Attach `agent_id`, `agent_type`, `pipeline_run_id` as metadata to every LLM call. Platforms aggregate by these tags. Langfuse's Metrics API filters by tags. LangSmith groups by run metadata.

**2. Proxy-based (Helicone, Portkey)**
Route all LLM calls through a proxy by changing the base URL. No SDK changes. The proxy logs requests, responses, tokens, and costs automatically. Portkey tracks token usage across providers, teams, and workloads via routing labels.

**What to capture per agent:**
- Input + output tokens per request
- Retries and retry amplification
- Parallel tool calls (each is a separate cost event)
- Agent-loop iterations (a loop running 5x = 5x the cost)
- Model used (different models = different $/token)

**Alerting pattern:** Set thresholds per agent per time window (e.g., "marketing-strategist spends >$5 in 1 hour") with automated rate-limit or alert.

### Key Metrics for a Marketing Agent System

From Holus's context (marketing content pipeline: SEO researcher → blog writer → reviewer → publisher):

**Pipeline-level:**
- Content velocity: articles/briefs generated per day
- Quality/brand QA pass rate: % passing reviewer pool threshold
- Time-to-publish: elapsed time from trigger to publish
- Cost per published asset

**Agent-level:**
- Task completion rate per agent (did it finish without error?)
- Tool call success rate (did external API calls succeed?)
- Retry rate (indicator of model/prompt instability)
- Token efficiency: output quality / tokens consumed
- Latency per agent (P50/P95)

**Quality scoring:**
- Eval score per content piece (LLM-as-judge, 1–10 scale)
- Score distribution over time (detect drift)
- Score by specialist type (which reviewer categories flag most rejections)
- Adaptive threshold compliance: what % of pieces exceed current threshold

**Cost:**
- Per-agent daily/weekly spend
- Model cost breakdown (Sonnet vs Gemini vs Codex)
- Cost per approved asset (total pipeline cost / approved pieces)

### Recommendation

**For Holus Observatory — use Langfuse (self-hosted) as the tracing backbone.**

Rationale:
1. MIT licensed, self-hosted → no data leaves the stack, zero ongoing cost
2. Works with everything — Holus uses Claude (Anthropic SDK), Gemini, and Codex. Langfuse is framework-agnostic with SDKs for all three.
3. Best open-source cost tracking: metadata tags let you attribute every LLM call to a specific agent (`seo-researcher`, `blog-writer`, `proof-agent`)
4. LangGraph is already in the Holus stack → Langfuse's LangGraph integration gives near-zero setup for traces
5. 50K events/mo free tier covers early production easily

**For quality visualization in the Observatory UI:** Build custom eval score charts using Tremor area charts + sparklines pulling from Langfuse's Metrics API. Do not rely on Langfuse's own dashboard for the Observatory — it's a backend data source, not the UI.

**If OpenTelemetry compliance becomes important** (cross-system tracing, Kubernetes, future multi-cloud): switch to or add Phoenix alongside Langfuse. OTel traces from Phoenix can feed the same Observatory UI.

---

## Key Takeaways

- **SvelteKit + FastAPI is the tightest integration** for a real-time SSE dashboard. Bundle is 50%+ smaller than Next.js, developer velocity for dashboards is higher, and Svelte 5 runes are naturally reactive for streaming agent state. If React is mandatory, Next.js 16 is the fallback — skip Remix.

- **Tremor is the fastest path to a polished dashboard.** It's purpose-built for exactly this use case (KPI cards, sparklines, eval score charts, cost tables). Use it on top of shadcn/ui as the base. Recharts directly when you need lower-level control.

- **Langfuse self-hosted is the right tracing backend for Holus.** MIT, framework-agnostic (works with Claude/Gemini/Codex), strong cost tracking via metadata tags, LangGraph integration. The Observatory dashboard calls Langfuse's Metrics API — it doesn't embed Langfuse's UI.

- **Multi-agent cost tracking requires explicit tagging from day one.** Tag every LLM call with `agent_id` and `pipeline_run_id`. Retroactively attributing costs without tags is impossible. The metadata tagging pattern works across all platforms.

- **The metrics that matter most for a marketing agent system:** eval score pass rate, cost per approved asset, agent retry rate (instability signal), time-to-publish, and per-agent token spend. These five give complete health visibility for the Holus content pipeline.
