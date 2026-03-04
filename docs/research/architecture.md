---
last_updated: 2026-03-04
review_cadence: 90d
next_review: 2026-06-02
owner: juan
dependent_specs: []
---

# Architecture Research — Holus

Last updated: 2026-03-04
Review cadence: 90 days
Next review: 2026-06-02

---

## 1. Multi-Agent Orchestration Patterns

### 1.1 Supervisor Pattern

**How it works:**
A single supervisor agent receives input and delegates to specialized sub-agents. All routing flows through the supervisor. Sub-agents report back; supervisor decides next step.

**Evidence:**
- LangChain's `langgraph-supervisor-py` library implements hierarchical multi-agent systems where specialized agents are coordinated by a central supervisor [VERIFIED — github.com/langchain-ai/langgraph-supervisor-py, accessed 2026-03-04, Grade A]
- LangChain officially benchmarked this pattern in June 2025 [VERIFIED — blog.langchain.com/benchmarking-multi-agent-architectures/, June 11, 2025, Grade A]

**When to use:**
- When a coordinator needs to maintain global state
- When agent handoffs are conditional and require judgment
- When you want centralized logging and control

**When NOT to use:**
- When latency is critical (supervisor adds round-trip overhead)
- When agents are independent and don't need coordination

**Trade-offs:**
| Pro | Con |
|-----|-----|
| Centralized control | Extra round-trip per handoff |
| Easy to audit | Supervisor becomes bottleneck |
| Clear failure mode | Higher LLM cost per task |

### 1.2 Swarm Pattern

**How it works:**
Agents hand off directly to each other without a central coordinator. The `langgraph-swarm-py` library implements an active-agent router that tracks which agent is currently active.

**Evidence:**
- `langgraph-swarm-py` enables direct agent-to-agent handoffs via handoff tools [VERIFIED — github.com/langchain-ai/langgraph-swarm-py, accessed 2026-03-04, Grade A]
- Swarm pattern achieved ~40% reduction in end-to-end response time vs supervisor pattern in a named implementation (methodology: LangSmith waterfall comparison) [UNVERIFIED — single engineer blog, July 7, 2025, Grade C — directional only]

**When to use:**
- When agents have clear specialization and handoff logic
- When latency is critical
- When tasks flow linearly through agents

**When NOT to use:**
- When tasks require global state coordination
- When you need centralized control for compliance

### 1.3 Recommended Pattern for Holus

**Supervisor pattern for orchestration, with direct-handoff for content pipeline.**

Reasoning:
- Holus's weekly/daily cycle is not latency-sensitive (40% faster = still acceptable at swarm baseline)
- Holus needs centralized state: MEMORY.md updates, analytics ingestion, approval queue management
- The supervisor (Coordinator) maintains the ReAct loop: OBSERVE → REASON → ACT → EVALUATE
- Content sub-pipeline (ideation → draft → translate → adapt → approve) can use direct handoffs internally

---

## 2. Human-in-the-Loop (HITL) Patterns

### 2.1 LangGraph interrupt() API

The primary mechanism for human approval in Holus. [VERIFIED — official docs, Grade A]

**Requirements to implement:**
1. A checkpointer to persist graph state (durable in production — e.g., PostgreSQL-backed) [VERIFIED — docs.langchain.com/oss/python/langgraph/interrupts]
2. A `thread_id` in config so the runtime knows which state to resume [VERIFIED — same source]
3. An `interrupt()` call at the pause point with JSON-serializable payload [VERIFIED — same source]

**Code pattern:**
```python
from langgraph.types import interrupt

def approval_node(state: State):
    # Pause and send content to human for review
    approved = interrupt({
        "content": state["draft_content"],
        "platform": state["target_platform"],
        "instruction": "Approve or reject this content. Return {'approved': true/false, 'feedback': '...'}"
    })
    return {"approved": approved["approved"], "feedback": approved.get("feedback", "")}
```

### 2.2 Static vs Dynamic Interrupts

| Type | When | Implementation |
|------|------|----------------|
| Static (compile-time) | Every content generation needs approval | `interrupt_after=["generate_content"]` at `.compile()` |
| Dynamic (runtime) | Conditional approval (e.g., only posts > certain sensitivity) | `interrupt()` inside node with conditional logic |

[VERIFIED — dev.to/sreeni5018, December 21, 2025, Grade B]

**Holus recommendation:** Static interrupts on the content approval node. Every piece of content Juan will publish needs his eyes before posting. This is a compliance requirement, not optional.

### 2.3 Approval Queue Design

The Telegram bot is Holus's approval interface. When content is ready:
1. LangGraph pauses at `approval_node`
2. Content + platform + schedule is sent to Juan via Telegram
3. Juan replies with ✅ (approve) or ❌ + feedback (reject/revise)
4. Holus resumes via `Command(resume={"approved": true, "feedback": "..."})` 
5. If approved → payload sealed and sent to social-media-auto API
6. If rejected → content loops back to generation with feedback

---

## 3. Content Generation Pipeline

### 3.1 Recommended Flow

```
OBSERVE
  ↓ social-media-auto: get_analytics(last_7_days)
  ↓ products.yaml: feature changelog
  ↓ MEMORY.md: learned patterns
REASON (Opus 4.5)
  ↓ What to create? For which platform? What angle?
GENERATE (Sonnet 4)
  ↓ Ideation → Copywriting → Translation → Platform Adaptation
APPROVE (interrupt)
  ↓ Telegram approval gate
PUBLISH
  ↓ Sealed payload → social-media-auto API
EVALUATE
  ↓ Log to trajectory.jsonl
  ↓ Update MEMORY.md
```

### 3.2 State Schema (TypedDict)

```python
class HolusState(TypedDict):
    # Input
    analytics: dict           # Last 7 days analytics
    product_context: dict     # From products.yaml
    memory: str               # MEMORY.md contents
    
    # Generation
    strategy: str             # Opus reasoning output
    draft_content: str        # Sonnet draft
    translated_content: str   # EN or ES version
    adapted_content: dict     # Per-platform adaptations
    
    # Approval
    approved: bool
    feedback: str
    
    # Output
    published: bool
    trajectory_entry: dict
```

### 3.3 Episodic Execution

Holus runs episodically (weekly cron or manual Telegram trigger) — not a long-running daemon. This is the right choice for:
- Cost control (pay per run, not per hour)
- Debuggability (each run is isolated, inspectable)
- Simplicity (no daemon management, no reconnection logic)

---

## 4. State Persistence

### 4.1 Checkpointer Options

| Option | Best For | Durability | Holus Fit |
|--------|----------|-----------|-----------|
| InMemorySaver | Dev/testing | None | Testing only |
| SqliteSaver | Single-node | Medium | Acceptable for solo use |
| PostgresSaver | Production | High | **Recommended** (already running PostgreSQL) |

**Recommendation:** Use `PostgresSaver` checkpointer — Holus already has PostgreSQL in Docker Compose. Thread state survives restarts and approval queue can span multiple sessions.

---

## Open Questions

- [ ] What is the latency impact of PostgresSaver vs SqliteSaver for Holus's use case?
- [ ] Should content approval queue be async (Holus runs, sends to Telegram, state persists until Juan responds) or synchronous (Holus waits)?
- [ ] How to handle approval timeout — if Juan doesn't respond in 24h, auto-cancel or auto-approve?

---

## Sources

1. LangChain, "Interrupts - Docs by LangChain", https://docs.langchain.com/oss/python/langgraph/interrupts (accessed 2026-03-04)
2. LangChain, "Agent Orchestration Framework for Reliable AI Agents", https://www.langchain.com/langgraph (accessed 2026-03-04)
3. GitHub, "langchain-ai/langgraph-supervisor-py", https://github.com/langchain-ai/langgraph-supervisor-py (accessed 2026-03-04)
4. GitHub, "langchain-ai/langgraph-swarm-py", https://github.com/langchain-ai/langgraph-swarm-py (accessed 2026-03-04)
5. LangChain Blog, "Benchmarking Multi-Agent Architectures", https://blog.langchain.com/benchmarking-multi-agent-architectures/ (June 11, 2025)
6. Sameer Nasir Shaikh, "Langgraph SWARM vs Langgraph SUPERVISOR", https://medium.com/@sameernasirshaikh/langgraph-swarm-vs-langgraph-supervisor-ce8194837d0a (July 7, 2025)
7. Sreeni, "Beyond input(): Building Production-Ready Human-in-the-Loop AI Agents with LangGraph", https://dev.to/sreeni5018/beyond-input-building-production-ready-human-in-the-loop-ai-with-langgraph-2en9 (December 21, 2025)
8. Towards Data Science, "LangGraph 201: Adding Human Oversight to Your Deep Research Agent", https://towardsdatascience.com/langgraph-201-adding-human-oversight-to-your-deep-research-agent/ (September 9, 2025)
