# Playbook: Visual Pipeline

The visual pipeline turns structured agent output into branded social assets by converting typed specs into Jinja templates and rendering them through the Playwright engine. The goal is to keep content generation deterministic at the boundaries: agents emit data, converters map that data into templates, and the renderer produces PNG or PDF outputs.

| Content type | Spec / converter | Output |
|---|---|---|
| `CAROUSEL` | `CarouselSpec` | PDF |
| `INSIGHT` | `RenderSpec` via `single_image/insight` | PNG |
| `DATA_VIZ` | `RenderSpec` via `single_image/data_viz` | PNG |
| `POLL` | `RenderSpec` via `single_image/poll` | PNG |
| `VIDEO_REEL` | `VideoSkeletonSpec` | placeholder PNG |

## Add a Template

1. Create the new `templates/.../*.html.j2` file and extend `base.html.j2`.
2. Add CSS in the template head block, or update shared CSS only if the pattern should be reused.
3. Add a converter in `src/holus/visual/spec_converter.py` that validates inputs and returns a `RenderSpec`.
4. Export the new model or converter from `src/holus/visual/__init__.py`.

## Visual Baselines

Capture fresh baselines with:

```bash
python scripts/capture_visual_baselines.py
```
