---
title: Content Evaluation & Quality Gates
domain: content-quality
owner: holus-research
last_updated: 2026-03-14
review_cadence: 30
next_review: 2026-04-13
---

# Content Evaluation & Quality Gates

> Full research on agent evaluation, LLM-as-Judge patterns, and observability is in
> [../architecture.md](../architecture.md) (section: Agent Evaluation & Observability).
> This file captures Holus-specific decisions and implementation details.

## Quality Gate Architecture (Holus)

Three-layer gate applied to every content piece before publishing:

### Gate A: Programmatic (deterministic, $0)

Applied in `idea_runner.py` before saving to content queue.

| Check | Rule | Blocks? |
|-------|------|---------|
| No exclamation marks | `"!" not in text` | Yes |
| No leading "I" | First char of first line is not "I" | Yes |
| No "we" | `" we " not in text.lower()` | Yes |
| Character limit | Platform-specific max chars | Yes |
| Hashtag count | 3-5 hashtags | Warn |

### Gate B: LLM Judge (probabilistic, ~$25-60/month)

Independent model (not the generator) scores each piece. Uses 2D rubric parameterized by content_type x platform.

- **Judge model:** Different from generator (e.g., if generator is Claude, judge is Gemini or GPT-4o-mini)
- **Rubric dimensions:** hook strength, voice fidelity, content fidelity, platform fit
- **Scoring:** G-Eval pattern — CoT before numeric score (1-10)
- **Threshold:** Score >= 7 to pass. Score 5-6 = revise. Score < 5 = reject.

See [../architecture.md](../architecture.md) for full research on judge patterns and bias mitigation.

### Gate C: Human Review (Observatory)

Juan reviews in Observatory dashboard. Approve/reject with one click. This is the final gate — catches what programmatic and LLM layers miss (~50% of remaining issues).

## Content Fidelity Constraint

Added to generator prompt in `idea_runner.py`:

- Generator must **elaborate**, not **invent** new claims
- Up to 2 supporting claims allowed IF: (a) direct logical consequence of something in the idea, (b) unambiguous technical fact
- No market observations, trend statements, or historical framing not in the original idea
- Post must defend ONE thesis — no second thesis, even related

## Decision: Single Parameterized Judge (not N judges)

One judge model with dynamic context injection (content_type + platform) rather than separate judges per format. The rubric weights shift based on parameters, not the judge itself.

See [architecture.md section on 2D rubric](../architecture.md) for the research backing this decision.
