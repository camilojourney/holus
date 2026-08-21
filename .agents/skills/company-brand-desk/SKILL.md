---
name: company-brand-desk
description: "Company OS brand desk. Review brand signal and voice evidence before supervisor routing."
compatibility: [python>=3.12]
prompt_version: 2
agentic_eval: default-7-pillars
---

# Company Brand Desk

This Holus-owned Company OS skill reads Company OS brand evidence and writes desk findings for
the supervisor. It does not publish, send outreach, spend money, or grant IC
approval.

## Inputs

- `.self-improvement/automations/COMPANY_OS.md`
- `.self-improvement/COMPANY_KILL`
- `.self-improvement/automations/brand-marketing/events.jsonl`
- `.self-improvement/automations/brand-content/events.jsonl`
- `.self-improvement/hub/ic_decisions.jsonl`

Treat missing evidence as `NEEDS_MORE_EVIDENCE`, not approval.

## Workflow

1. Stop with `HALT` when `COMPANY_KILL` is tripped or unreadable.
2. Review brand KPI placeholders: `share_of_voice`, `sentiment`,
   `follower_delta`, and `voice_consistency_score`.
3. Use official LinkedIn 3-legged OAuth evidence when follower data is
   available, and include the `taste`/`brand-strategist` deep handoff in the
   event payload for voice consistency scoring.
4. Route publish, outreach, spend, or public-positioning actions to
   `human_ic_required`; only `ic_decisions.jsonl` can approve them.
5. Append one desk event to
   `.self-improvement/automations/brand-marketing/events.jsonl`.
6. Follow `references/output-contract.md` for the event shape.

## Deterministic Commands

- `python3 build_brand_context.py --repo-path <holus-root> --out /tmp/company-brand-context.json`
- `python3 render_brand_outputs.py --repo-path <holus-root> --context-file /tmp/company-brand-context.json`

## Silo Invoke Paths

- Taste deep brand review: `/taste holus company-brand-desk --deep --agent brand-strategist`
- Notion milestone journal: `/notion log Company OS funnel milestone`

Both paths are represented as local handoff payloads during unattended runs;
they do not publish, approve, or mutate external systems.

## Agents

Use the agent stubs when the evidence is ambiguous or a brand recommendation
could affect public positioning:

- `brand-signal-auditor`
- `voice-consistency-reviewer`
