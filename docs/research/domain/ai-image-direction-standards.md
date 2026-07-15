---
title: AI Image Direction Standards
last_updated: 2026-06-18
mode: TECHNICAL_OPTIONS
status: active
---

# AI Image Direction Standards

## Question

What should Holus require from an AI image specialist so generated images get close to the intended marketing concept instead of producing vague, decorative output?

## Evidence

- [VERIFIED] OpenAI's image prompting guidance says text-in-image work needs exact copy, placement, and font/style constraints, and dense text/layouts need stricter prompting and iteration.
  Source: https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
- [VERIFIED] Google's Gemini image prompting guide recommends describing the scene rather than listing keywords, and for photorealistic scenes it calls out shot type, subject, action/expression, environment, lighting, mood, camera/lens, details, and aspect ratio.
  Source: https://developers.googleblog.com/how-to-prompt-gemini-2-5-flash-image-generation-for-the-best-results/
- [VERIFIED] The same Google guide says image editing should preserve style, lighting, and composition when only one element is changed, and notes that nuanced requests and complex typography may require iteration.
  Source: https://developers.googleblog.com/how-to-prompt-gemini-2-5-flash-image-generation-for-the-best-results/
- [VERIFIED] Adobe Firefly guidance emphasizes specificity, simple/direct language, subject, descriptors, and keywords, and recommends rewording prompts when outputs miss the target.
  Source: https://helpx.adobe.com/firefly/web/generate-images-with-text-to-image/generate-images-using-text-prompts/writing-effective-text-prompts.html
- [VERIFIED] Midjourney docs distinguish text prompts, image/style references, and parameters such as aspect ratio as separate controls over output.
  Source: https://docs.midjourney.com/hc/en-us/articles/32023408776205-Prompt-Basics

## Standard Adopted

Holus AI image direction must include:

1. Content job fit.
2. Single viewer takeaway.
3. Concrete subject.
4. Action or state.
5. Environment.
6. Composition and camera.
7. Lighting and mood.
8. Style or medium.
9. Palette and brand fit.
10. Aspect ratio and platform.
11. Text policy.
12. Reference assets, when available.
13. Negative constraints.
14. Reviewer checklist.

## Hard Gates

AI image direction must return `allowed: false` when:

- The content job is `data_claim`, `workflow_explanation`, chart, table, or diagram.
- The image needs exact text, labels, or numbers to communicate.
- The idea needs a fake dashboard, fake UI, fake logo, or invented product state.
- The image is only decoration for an opinion.
- The metaphor cannot be explained in one sentence.

## Recommended Agent Contract

Use `agentic/agents/specialists/visual/ai-image-director.md` as the canonical specialist. It produces a structured brief, not a loose prompt. The final provider prompt is only one field inside the larger direction object.

## Why This Matters

The previous prompt shape was too thin:

```json
{
  "scene": "a workbench covered with scattered sticky notes",
  "subject": "prompt cards",
  "composition": "top-down editorial photo"
}
```

That leaves too many decisions to the model. The new contract forces the agent to decide what the viewer should understand, what object maps to what concept, where the camera is, what text is allowed, what must be absent, and how the judge will evaluate the result.

## Confidence

High confidence that this improves AI image prompt quality for metaphor/story/product-scene cases.

Medium confidence that it will make first-pass results publishable. The sources agree that iteration is still needed, especially for text and nuanced layouts.
