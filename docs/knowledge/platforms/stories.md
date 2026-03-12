# Instagram Stories Platform Knowledge
# Version: 1.0 (stub — 2026-03-08)

## Core Constraints

- **Format: JPEG only** — convert PNG before upload (PNG fails silently in some API versions)
- **Dimensions: 1080×1920 px** (9:16 portrait — anything else crops incorrectly)
- **Text: NOT rendered via API** — the API posts the image as-is. You cannot pass caption text and have it appear on the story.

## Text in Stories

Two options if text is needed:
1. **Burn text into the image** using Pilaster before uploading (preferred)
2. **Post image-only** — let the visual speak without text

Never pass text as a caption field expecting it to render — it won't appear.

If the user wants text in a story → flag: "Story text must be burned into the image. Use Pilaster to generate the image with text baked in before posting."

## Safe Zone

Content that matters must stay within the safe zone to avoid being obscured by the platform UI:
- **Y axis:** 250 to 1670 (top and bottom are hidden by story chrome)
- **X axis:** 40 to 1040

Do not place important text, faces, or logos outside this zone.

## Duration

Photos are shown for approximately 5 seconds by the platform (not configurable via API).

## Scheduling

Stories **cannot be scheduled** via the API. Post immediately only.

## Analytics

No analytics available via API for stories. Engagement data is not queryable.

## Workflow

1. Validate image is JPEG + 1080×1920
2. If PNG: convert to JPEG before upload
3. If text needed: route to Pilaster to generate image with text burned in
4. Upload via `POST /api/v1/media/upload` → get URL
5. Post to story endpoint with `format: story`

## Accounts

| Account | Language | Handle |
|---|---|---|
| experience | EN | @camiloexperience |
| journey | ES | @camilojourney |

## Related Files

- Instagram feed: `holus/knowledge/platforms/instagram.md`
- Pilaster image generation: `holus/knowledge/current/pilaster-repo.md`

## Status

Stub — update with real API behavior after first 5 story posts.
