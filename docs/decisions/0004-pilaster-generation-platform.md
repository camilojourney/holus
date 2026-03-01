# ADR-0004: Pilaster as Backend-Agnostic Generation Platform

## Status

Accepted

## Context

Pilaster was originally designed as "the memory layer for ComfyUI" — a companion
tool that tracks ComfyUI workflow experiments, diffs versions, and warns before
repeating failures. This tightly coupled Pilaster to ComfyUI:

- If ComfyUI changes or dies, Pilaster breaks.
- Users who don't use ComfyUI can't use Pilaster.
- The product is defined by someone else's tool, not by its own value.

Meanwhile, the real value Pilaster provides is:
1. **Character consistency** — keeping LoRAs, reference sheets, and metadata so
   characters look the same across all generations.
2. **Experiment memory** — knowing what worked and what failed.
3. **Templates** — reusable generation presets that encode proven settings.

None of these require ComfyUI specifically. They work with any generation backend.

## Decision

Pilaster becomes an **AI image generation platform with memory**. Three layers:

1. **Character registry** — stores LoRAs, reference sheets, and metadata per
   character. Holus (or any client) requests "generate with character X" and
   Pilaster handles loading the right identity assets.

2. **Generation abstraction** — a single `generate(character, template, prompt)`
   interface. Behind it, swappable backend adapters:
   - ComfyUI (local, full control, node workflows)
   - Replicate (cloud, simple API, pay per generation)
   - Runway (cloud, best for video-from-image)
   - Fal.ai (cloud, fast SD inference)
   - Custom engines (future)

   Users never see nodes. They pick a character, a template, and hit generate.

3. **Experiment memory** — unchanged from current design. Tracks every generation
   with outcomes, quality scores, and settings. Learns what works.

## Consequences

### Positive

- Pilaster's value is independent of any single backend.
- Character consistency becomes a first-class feature, not a side effect.
- Broader audience: anyone doing AI image generation, not just ComfyUI users.
- Holus integration is cleaner: `generate(character="mascot", template="product-shot")`
  instead of `generate_image(brief, workflow_id)`.
- Backend can be swapped without losing characters or memory.
- Opens the door to offering Pilaster as a SaaS (users bring their own backend keys).

### Negative

- More engineering work: need backend adapters for each engine.
- ComfyUI adapter is the most complex (node graph translation).
- LoRA management varies by backend (ComfyUI loads .safetensors locally,
  Replicate needs model upload, Runway uses reference images instead).
- Template system needs to be abstract enough to map to different backends.

### Risks

- **Abstraction leak:** Each backend has unique capabilities. The abstraction might
  become lowest-common-denominator. Mitigate: allow backend-specific settings as
  optional pass-through, but keep the default interface simple.
- **LoRA portability:** A LoRA trained for SDXL may not work on all backends.
  Mitigate: store reference images alongside LoRAs as universal fallback.
  Backends that don't support LoRA can use reference images instead.

## Alternatives Considered

### Alternative A: Keep Pilaster as ComfyUI-only companion

- Simpler to build and maintain.
- Rejected because it limits the audience and creates existential dependency on ComfyUI.

### Alternative B: Build a new app for the generation platform, keep Pilaster for memory

- Clean separation of concerns.
- Rejected because it splits the value proposition. The memory IS the platform.
  Characters, templates, and experiment history are what make generation valuable.
  Splitting them into two apps creates unnecessary friction.

### Alternative C: Build everything into Holus

- Holus manages characters, templates, and generation directly.
- Rejected because it violates the silo architecture. Pilaster is the image
  generation silo. Holus is the strategist. Holus decides WHAT to create,
  Pilaster decides HOW to create it.

## References

- Runway Gen-4 character consistency via reference images
- Kling 3.0 Elements feature (multi-reference character consistency)
- LoRA training: 10-30 reference images → consistent character identity
- ComfyUI AnimateDiff for short video clips from consistent characters

---

**Date:** 2026-02-28
**Author:** Camilo Martinez
