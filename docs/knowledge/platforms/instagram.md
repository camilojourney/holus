# Instagram Platform Knowledge
# Version: 1.0 (stub — 2026-03-08)

## Core Rule: Visual-First

**NEVER post without an image or video.** Instagram is a visual platform — the media IS the post. Text-only posts do not exist on Instagram. If there is no image or video, skip Instagram.

## Feed Posts

### Caption Structure
- **First 125 characters** = hook — this is what shows before "more". Make it count.
- **Body** = expand the idea. Concrete details > vague inspiration.
- **Hashtags** = at the end of caption OR in first comment. 5–8, targeted.

### Hashtags
- EN (@camiloexperience): professional AI/builder tags (#AIEngineering #BuildInPublic #MachineLearning)
- ES (@camilojourney): Spanish-first, English where no Spanish equivalent (#Ingeniería #InteligenciaArtificial)
- Never more than 8. Targeted > volume.

### Image Requirements
- JPEG preferred (PNG also works for feed posts)
- Square (1080x1080) or portrait (1080x1350) performs best
- Landscape (1080x566) works but crops on mobile

## Reels

- Duration: 15–60 seconds sweet spot
- Hook in first 3 seconds — or the viewer leaves
- Word-by-word captions required (process via Genpeli)
- Vertical format (1080x1920)

## Stories

- JPEG required (convert PNG before upload)
- 1080x1920 dimensions
- **Text NOT rendered via API** — burn text into image using Pilaster, or post image-only
- Safe zone: Y 250–1670, X 40–1040 (avoid platform UI chrome)
- Duration: auto (~5s for photos)
- Cannot be scheduled — post immediately only
- See `holus/knowledge/platforms/stories.md` for full stories spec

## Accounts

| Account | Language | Handle | Feel |
|---|---|---|---|
| experience | EN | @camiloexperience | Main EN visual feed |
| journey | ES | @camilojourney | Main ES visual feed, more personal |
| camilonation | EN | camilonation | Experimental A/B test only |
| cmadapt | EN | @camilo.clips (ES) | Experimental A/B test only |

## What Works

- Before/after comparisons (code, interfaces, results)
- Behind-the-scenes of building
- Short demo clips with captions

## What Fails

- Text-only posts (not possible)
- Low-quality images
- Captions that start with hashtags

## Status

Stub — update with real performance data after first 10 posts.
