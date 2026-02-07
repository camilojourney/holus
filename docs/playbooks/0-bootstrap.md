# Phase 0: Bootstrap Setup

> **When to use:** First time setup for a new project created from this template.
> **Goal:** Collect project context and generate initial framework files with real values.

---

## Prompt

```text
Read this file and run an interactive bootstrap for my project.
Ask me one question at a time, wait for my answer, and keep a running summary.
When done, generate the initial versions of:
- AGENTS.md
- CLAUDE.md
- .ai/contexts/product-context.md
- .ai/contexts/current-priorities.md
- .ai/decision-boundaries.md

Rules:
1. Ask concise, concrete questions.
2. Prefer defaults if I'm unsure.
3. Keep generated files practical and short.
4. Do not invent stack details; confirm unknowns.
5. Replace placeholders only when values are known.
```

---

## Interview Checklist

Ask for these categories:

1. Project identity
- Project name
- Tagline
- Vision (1-2 sentences)
- Target users

2. Tech stack
- Framework/runtime
- Language
- Database/storage
- Package manager
- Test command
- Lint command
- Build command

3. Product/domain
- Core entities
- Key user flows
- External APIs/services
- Compliance/security constraints

4. Decision boundaries
- Always rules
- Ask-first rules
- Never rules

5. Near-term priorities
- Top 3 goals this week
- Known blockers
- Next milestone

---

## Output Requirements

Before finishing, ensure:

- `AGENTS.md` has real commands and stack values.
- `CLAUDE.md` references real project directories/commands.
- `.ai/contexts/product-context.md` reflects real domain terms.
- `.ai/contexts/current-priorities.md` has concrete short-term priorities.
- `.ai/decision-boundaries.md` reflects the team's authority policy.

---

## Final Handoff

Return:

1. A short summary of answers captured.
2. The list of generated/updated files.
3. Any unresolved placeholders requiring human follow-up.
