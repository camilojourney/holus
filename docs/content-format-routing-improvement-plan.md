---
title: Content Format Routing Improvement Plan
last_updated: 2026-06-18
status: active
---

# Content Format Routing Improvement Plan

## Objective

Stop confusing visual asset creation with content strategy. Holus must classify the content job first, choose the format second, and only then decide whether any visual should be produced.

## Success Metrics

- At least 90% of `opinion` and `lesson` jobs route to `text_post` with `needs_visual=false`.
- 100% of `data_claim` jobs forbid `ai_generated_image`.
- 100% of `workflow_explanation` jobs route to deterministic diagram or carousel, never AI image.
- AI image generation is used only for `metaphor`, concrete `founder_story` artifact scenes, or approved product/story scenes.
- Every queue record includes `content_job_plan`.

## Failure Modes

- Decorative images attached to posts that are stronger as text.
- AI-generated charts, fake dashboards, or unreadable text.
- Workflow explanations routed to vague metaphor images.
- Founder stories converted into generic corporate scenes.
- Provider/model comparisons used as a substitute for content planning.

## Pipeline

```text
raw thought
-> content-job-classifier
-> format-router
-> specialist writer/designer
-> visual-necessity-gate
-> deterministic-artifact-planner OR ai-image-director
-> renderer/provider
-> semantic-visual-judge
-> human review
-> publish
-> performance learning
```

## Content Job Rules

| Job type | Default format | Visual rule |
| --- | --- | --- |
| `opinion` | `text_post` | No visual unless a concrete metaphor is explicit. |
| `lesson` | `text_post` | No visual unless it has reusable structure or proof. |
| `framework` | `carousel_document` | Deterministic carousel or framework grid. |
| `workflow_explanation` | `carousel_document` or deterministic diagram | Never AI image. |
| `data_claim` | `text_with_deterministic_visual` | Chart/table only; never AI image. |
| `product_update` | `text_with_deterministic_visual` | Deterministic UI/state surface; no fake UI text. |
| `founder_story` | `text_post` | Visual only with a concrete artifact. |
| `metaphor` | `ai_generated_image` | Allowed only for one concrete metaphor. |
| `case_study` | `carousel_document` | Use proof sequence, comparison, or before/after. |

## Implementation Status

- Added deterministic content job taxonomy in `src/holus/visual/content_job.py`.
- Added explicit `no_visual` strategy path in `src/holus/visual/generation_strategy.py`.
- Thought Studio queue records now include `content_job_plan`.
- Thought Studio skips rendering when strategy is `no_visual`.
- Added registry entries and prompt contracts for:
  - `content-job-classifier`
  - `format-router`
  - `visual-necessity-gate`
  - `deterministic-artifact-planner`
  - `ai-image-director`
  - `semantic-visual-judge`

## Next Steps

1. Replace keyword heuristics in `content_job.py` with agent-backed classification when model calls are available.
2. Add queue-level analytics for format decisions: job type, needs visual, route, provider, judge verdict, later performance.
3. Add semantic visual judge execution after rendered artifacts, not only prompt contracts.
4. Add deterministic examples for each allowed artifact type and block AI examples for forbidden jobs.
5. Re-run provider cycles only after the routing gate proves the content job actually needs imagery.

## Verification Plan

- Unit tests prove taxonomy behavior for opinion, data, workflow, metaphor, and founder-story artifact cases.
- Generation strategy tests prove text-only jobs use `no_visual`.
- Future acceptance tests should create a full thought pipeline run and assert text-only records do not have rendered image paths.
