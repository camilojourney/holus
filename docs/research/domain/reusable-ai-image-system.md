---
title: Reusable AI Image Creation System
domain: visual-content
owner: holus-research
last_updated: 2026-06-18
review_cadence: 45d
next_review: 2026-08-02
---

# Research: What should Holus do to create reusable, high-impact AI images?

## Mode

TECHNICAL_OPTIONS

## Question

What should Holus build so AI-generated images are impactful, reusable across
content, and less likely to look like generic AI output?

## Evidence

- [VERIFIED] Holus architecture defines Holus as the thought-to-content studio
  that creates text/image/carousel assets, reviews them, and learns from
  results. Pilaster remains the future optional AI-image adapter, while Holus
  owns source metadata, decisions, generated variants, visual assets, review
  state, and learning. Source: `ARCHITECTURE.md`.
- [VERIFIED] Existing Holus image research already enumerates 42 controllable
  image variables across format, color, typography, composition, visual
  elements, and branding. Source: `docs/research/domain/image.md`.
- [VERIFIED] Existing Holus quality research says visual content needs a
  multimodal visual judge because JSON/text checks miss contrast, layout,
  broken charts, and visual hierarchy. Source:
  `docs/research/domain/content-evaluation.md`.
- [VERIFIED] LinkedIn's own single-image ad specs support square, horizontal,
  and vertical images, and recommend 4:5 to avoid borders for vertical image
  delivery. Source:
  https://business.linkedin.com/advertise/ads/sponsored-content/single-image-ads-specs
- [VERIFIED] NN/g research argues users attend to information-carrying images
  relevant to the task and ignore decorative/fluffy imagery. Source:
  https://www.nngroup.com/articles/photos-as-web-content/
- [VERIFIED] OpenAI image generation docs expose image generation as a formal
  API surface; image generation should be treated as a provider behind a
  contract, not a one-off prompt. Source:
  https://developers.openai.com/api/docs/guides/image-generation
- [VERIFIED] OpenAI's image-model prompting guide frames production prompting
  around concrete production use cases and model/quality tradeoffs, not vague
  aesthetic adjectives. Source:
  https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
- [VERIFIED] Google's People + AI Guidebook frames human-AI systems as
  bidirectional feedback loops. Source: https://pair.withgoogle.com/guidebook/

## Findings From Holus' Local Experiment

The proximity-router batch produced 10 Codex images across workflow, chart,
person story, object metaphor, product scene, and typography card routes.

- [VERIFIED] The router improved category selection versus direct prompting.
- [VERIFIED] Charts, typography cards, and simple object metaphors were the
  strongest routes.
- [VERIFIED] Person-story and product-scene routes were weak because the prompt
  did not fully specify the action, artifact, and viewer test.
- [VERIFIED] Codex obeyed broad route categories but still invented fake UI
  labels, generic software scenes, and low-specificity human moments.
- [VERIFIED] The next control layer should not be more adjectives; it should be
  a production plan and a visual judge.

Source: `data/test-runs/proximity-router-10/review.md`.

## Options Compared

### Option A: Prompt-only image generation

Holus sends a refined post and a style prompt directly to an image model.

Pros:
- Lowest implementation cost.
- Fast to experiment with.

Cons:
- High variance.
- Images often look decorative or generic.
- Hard to reuse because the visual decisions are hidden inside the prompt.
- Weak logs: hard to know why one image worked.

Verdict: reject as production architecture.

### Option B: Router + production plan + provider dispatcher

Holus converts refined content into a structured visual route, then a detailed
production plan, then sends that to Codex/Pilaster/OpenAI via dispatcher.

Pros:
- Reusable across models.
- Logs explain what was attempted.
- Easy to evaluate route quality separately from provider quality.
- Supports deterministic and AI-generated outputs.
- Keeps Holus as strategist and Pilaster as future image backend.

Cons:
- More code and more contracts.
- Still needs visual judging and retries.
- Requires maintaining route templates.

Verdict: recommended path.

### Option C: Build a full design-template system only

Holus avoids AI-generated scenes and only creates deterministic cards,
charts, diagrams, and carousels.

Pros:
- High consistency.
- Easy to brand.
- Avoids many AI-image artifacts.

Cons:
- Can become visually repetitive.
- Weak for human/story scenes.
- Less expressive for product narrative or metaphor content.

Verdict: use for charts, typography, carousels, and workflow diagrams, but not
as the only system.

### Option D: Move everything to Pilaster now

Holus sends all image work to Pilaster.

Pros:
- Correct long-term silo boundary.
- Pilaster can own reusable styles, memory, and generation backends.

Cons:
- Premature if Holus has not finalized route/plan/eval contracts.
- Risk: Pilaster becomes a prompt dump instead of a real image system.

Verdict: not yet. First stabilize Holus' creative contract; then hand it to
Pilaster as a structured recipe.

## Recommendation

Build a reusable **Visual Operating System** inside Holus, then later delegate
rendering to Pilaster.

The durable pipeline should be:

```text
refined content
-> content intent extraction
-> proximity route
-> production plan
-> provider dispatch
-> visual judge
-> retry/mutate route or plan
-> review queue
-> publish analytics
-> route/model/template learning
```

## Required Contracts

### 1. Content Intent

The visual system should never read raw thought as the creative source of
truth. It should read:

- refined text
- thesis
- intended takeaway
- audience state
- proof type
- emotional tension
- platform
- content format

Raw thought remains provenance only.

### 2. Proximity Route

The router answers: what kind of image should this be?

Supported reusable modes:

- `workflow`: process, handoff, operating system, pipeline
- `chart`: metric, comparison, ranking, evidence
- `person_story`: human decision, hesitation, pointing, review moment
- `object_metaphor`: one physical metaphor
- `product_scene`: UI/review queue/product behavior
- `typography_card`: the thesis itself is the asset

### 3. Production Plan

The production plan answers: what exactly must appear?

Fields:

- concept
- viewer test
- scene script
- composition script
- required elements
- text policy
- forbidden elements
- compliance checks

This should be deterministic first. Agents can improve it later, but they must
output the same schema.

### 4. Provider Recipe

Pilaster/OpenAI/Codex should receive structured data, not only a flat prompt:

- subject
- route mode
- production plan
- style profile
- composition
- lighting
- camera/framing
- negative constraints
- required compliance checks
- output size
- model/provider

### 5. Visual Judge

The judge should answer:

- Can a viewer understand the takeaway without the caption?
- Are the required elements visible?
- Does the image match the route?
- Is there pseudo-text or fake UI?
- Is it decorative rather than information-carrying?
- Does it look like generic AI output?
- Does it meet LinkedIn crop/format requirements?

Reject if:

- route does not match output
- required artifact/action is missing
- product scene has random fake UI
- person story is generic stock-photo energy
- metaphor is unclear
- workflow has unlabeled/random widgets
- chart is decorative or numerically incoherent

## Reusable Image Archetypes

### Workflow

Use when the idea is about process, roles, handoffs, systems, review, or
fallbacks.

Reusable pattern:

```text
input -> stage 1 -> stage 2 -> stage 3 -> review -> output
```

Must include:

- distinct stages
- one visible handoff path
- input/output boundary
- one bottleneck or correction point

### Chart

Use when the idea depends on evidence or comparison.

Reusable pattern:

```text
one chart + one highlighted conclusion
```

Must include:

- one chart type only
- one highlighted winner/anomaly
- minimal labels
- no decorative data clutter

### Person Story

Use when the idea depends on a human decision or moment.

Reusable pattern:

```text
person + artifact + visible action
```

Must include:

- one person
- one concrete artifact
- pointing/marking/pausing/choosing action
- visible decision tension

### Object Metaphor

Use when a physical metaphor can carry the idea.

Reusable pattern:

```text
one hero object + one visible tension
```

Must include:

- one metaphor only
- explainable in one sentence
- no random premium desk objects

### Product Scene

Use when the idea is about software behavior.

Reusable pattern:

```text
selected item + reason panel + decision state
```

Must include:

- one selected content/review item
- one reason or fit signal
- one decision state
- plausible UI blocks, not fake paragraphs

### Typography Card

Use when the thesis is stronger than any scene.

Reusable pattern:

```text
large thesis + one support line + restrained accent
```

Must include:

- exact thesis
- legible hierarchy
- minimal decoration

## Metrics

Pre-publish metrics:

- route accuracy
- plan compliance
- image clarity
- information-carrying score
- anti-slop score
- visual hierarchy
- brand consistency

Post-publish metrics:

- save rate
- comment quality
- share rate
- profile clicks
- dwell proxy for carousels/documents
- route-level performance
- provider/model-level performance

## Adversary Analysis

The biggest risk is building a complicated visual pipeline that still produces
bad images because the judge is weak. The second biggest risk is optimizing for
pretty images instead of useful images. NN/g's evidence is relevant here: users
ignore decorative images. The core gate must be information-carrying value, not
visual polish alone.

Another risk is overfitting to LinkedIn feed aesthetics. If every image becomes
an editorial chart/card, the brand becomes predictable. Holus needs a portfolio
of reusable archetypes and route-level performance tracking.

## Decision Points

DECISION_POINT: image_generation_architecture
OPTIONS: A) prompt-only B) router+plan+dispatcher+judge C) deterministic-only
RECOMMENDATION: B
CONFIDENCE: HIGH
EVIDENCE: Local Holus batch + NN/g decorative-image evidence + existing Holus
visual judge research.

DECISION_POINT: first production-quality routes
OPTIONS: A) all routes B) chart/typography/workflow first C) person/product first
RECOMMENDATION: B
CONFIDENCE: HIGH
EVIDENCE: Local batch showed chart and typography strongest; workflow is useful
but needs stricter compliance.

DECISION_POINT: Pilaster integration timing
OPTIONS: A) now B) after route/plan/judge contracts stabilize
RECOMMENDATION: B
CONFIDENCE: MEDIUM
EVIDENCE: Holus needs the creative contract before Pilaster can become a useful
backend rather than a prompt sink.

## Recommended Next Implementation

1. Add `VisualJudgeDecision` for image files, not just specs.
2. Judge the rendered image against the production plan.
3. Add retry policies per route:
   - person story: require action/artifact
   - product scene: require selected item/reason/decision
   - workflow: require sequence/input/output/bottleneck
   - object metaphor: require one metaphor only
   - chart: require one highlighted conclusion
4. Start a small route performance table:
   - route
   - provider
   - model
   - plan compliance score
   - human verdict
   - publish outcome
5. Only after this, map the structured recipe to Pilaster.

## Sources

- `ARCHITECTURE.md`
- `docs/research/domain/image.md`
- `docs/research/domain/content-evaluation.md`
- `data/test-runs/proximity-router-10/review.md`
- LinkedIn single image ad specs:
  https://business.linkedin.com/advertise/ads/sponsored-content/single-image-ads-specs
- NN/g, Photos as Web Content:
  https://www.nngroup.com/articles/photos-as-web-content/
- OpenAI image generation API:
  https://developers.openai.com/api/docs/guides/image-generation
- OpenAI image models prompting guide:
  https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
- Google People + AI Guidebook:
  https://pair.withgoogle.com/guidebook/
