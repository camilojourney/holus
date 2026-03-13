# Target — Holus Observatory

## Primary Persona: The Solo Founder Operator (Juan)

**Who:** Juan, 30s, AI engineer and solo founder running a portfolio of products (Pilaster, Genpeli, Invoz). Manages a 32-agent autonomous marketing system that creates, evaluates, and publishes content across 13 platforms. Technical — reads logs, writes Python, understands LLM internals.

**Problem:** The agent system runs headless. When something breaks at 2 AM, Juan tails JSONL files and greps YAML to understand what happened. He cannot answer "which agent failed?", "what did the system spend this week?", or "is the content quality trending up or down?" without manual data wrangling. There is no single surface that shows system health.

**Context:** Juan checks the Observatory 2-3 times per day — morning (overnight health check), midday (content pipeline status), and evening (review what shipped). He uses a MacBook during work hours and occasionally checks on his phone. He does NOT edit agents or content from the dashboard — it is strictly read-only. He already has Langfuse for raw trace data; the Observatory is the opinionated summary layer.

**What success looks like:** Juan opens the Observatory, sees 4 KPI cards (cycles, success rate, quality score, cost), notices one agent in red on the grid, clicks through to its detail page, sees the last 5 runs failed with low quality scores, and knows exactly where to focus. Total time: 30 seconds. No JSONL parsing. No terminal.

**Frustrations:**
- "I built 32 agents but I can't tell which ones are actually working without grepping trajectory.jsonl."
- "I don't know if quality is improving over time — I have no trend view."
- "The content pipeline could be stuck in DRAFT for days and I wouldn't notice."
- "I want to show this system to interviewers, but tailing logs is not a demo."

---

## Secondary Persona: The Interviewer / Portfolio Viewer

**Who:** A hiring manager or technical interviewer viewing the Observatory as a live demo during a job interview or portfolio review. Not a user — a viewer. Spends 2-5 minutes clicking through pages.

**What they need to see:** A polished, real dashboard showing a genuinely autonomous system. Real data, not mocks. Agent statuses, quality trends, content pipeline, cost tracking. The impression should be: "this person built and operates a real multi-agent system."

---

## Anti-Persona

**Team ops manager needing RBAC and multi-user:** The Observatory has no auth, no roles, no permissions. It is single-operator. A team wanting shared dashboards with access control needs Grafana or Datadog.

**Non-technical founder wanting a content calendar:** The Observatory shows agent system internals. Someone who wants to plan and schedule posts should use the social-media-automatization dashboard instead. The Observatory shows the brain, not the publishing queue.

**Someone wanting to control agents from the UI:** The Observatory is read-only. No editing agents, no triggering runs, no modifying config. All mutations happen through code, CLI, or the Telegram bot. If someone wants a control panel, this is not it.

---

## Design Tiebreaker

When UX decisions conflict, optimize for **glanceability of system health**.

The most critical moment is Juan opening the dashboard and knowing in under 5 seconds: is the system healthy? The KPI cards, health status banner, and agent grid must communicate state through color alone — green means fine, yellow means check, red means fix now. Every other UX decision is secondary to this 5-second health read.

---

## Tone of Voice

- Operational, not friendly. The Observatory is a monitoring tool. Status updates, not encouragement.
- Data-forward. Numbers, scores, timestamps. Not "Great job!" — instead "7.3/10, +0.4 from last week."
- Precise on failure. "Agent `hook-architect` failed: quality score 3.2 (threshold 7.0)" not "Something went wrong."
- Dark mode preferred. Operators monitor dashboards in varied lighting. Dark backgrounds reduce eye strain and make colored status indicators pop.
- Minimal text. The UI communicates through layout, color, and numbers. Paragraphs of explanation belong in docs, not the dashboard.
