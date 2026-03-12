# Threads Platform Knowledge
# Version: 1.0 (stub — 2026-03-08)

## Hard Constraints

- **Max 500 characters** — hard limit enforced by API. Truncated posts fail silently.
- **No hashtags** on @camiloexperience (EN) or @camilojourney (ES) — ever. Algorithm doesn't rely on them and they look out of place.
- **Images: JPEG only** — PNG will fail. Convert before upload.
- **Text-only posts work fine** — Threads is text-first. No image required.

## What Works

- Short punchy observations (1–3 sentences)
- Honest admissions ("I got this wrong")
- Dry humor with a specific technical detail
- Incomplete thoughts that invite a response naturally (not "what do you think?")
- Raw, unpolished takes — authenticity over polish

## What Fails

- Motivational content ("believe in yourself", "consistency is key")
- Questions as opening hooks ("Have you ever wondered...")
- "Here is a thread:" style setup
- Anything that reads like a LinkedIn post
- Long multi-paragraph explanations
- Hashtag stacks

## Accounts

| Account | Language | Handle | Feel |
|---|---|---|---|
| experience | EN | @camiloexperience | Conversational, smart friend, technical specifics welcome |
| journey | ES | @camilojourney | Warmer, more personal, community-focused, same no-hashtag rule |

## Accounts to Study

- @dailyprompter — best example of Threads-native writing (see `social-media-automatization/docs/knowledge/accounts/threads.md`)

## API Notes

- Image support: JPEG only, appears below text
- No scheduling via API — post immediately or use platform natively
- Character limit enforced at API level — validate before sending

## Status

Stub — update with real performance data after first 10 posts.
