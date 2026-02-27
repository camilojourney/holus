# Knowledge Base — holus

This directory contains accumulated market intelligence that the self-improvement system uses to refine content strategy, platform targeting, and cross-product marketing decisions.

## Topic Index

| Topic | File | Expert Agent | Confidence | Last Updated |
|-------|------|-------------|------------|--------------|
| Content Marketing Strategy | `current/content-marketing-strategy.md` | content_agent | preliminary | 2026-02-26 |
| Social Media Platforms | `current/platforms.md` | marketing_agent | high | 2026-02-26 |
| Audience Profiles | `current/audience-profiles.md` | marketing_agent | medium | 2026-02-26 |
| Content Formats & Templates | `current/content-formats.md` | marketing_agent | medium | 2026-02-26 |

## Structure

- `current/` — Active knowledge files used by the self-improvement pipeline
- `archive/` — Superseded versions, rotated automatically when knowledge is updated
- `requests/` — Knowledge gap requests filed by any agent, processed by experts

## How It Works

Expert agents run on a research cadence, updating topic files with findings. Each update archives the previous version and records confidence levels. The coordinator and domain agents read these files to inform strategy decisions.

## Scope

This directory is for **market intelligence only**:
- Content marketing trends and platform algorithm changes
- AI-driven content creation best practices
- Cross-product marketing insights (what content performs for which product)
- Social media engagement patterns and timing research

**NOT for:** architecture docs (use `ARCHITECTURE.md`), code patterns, or implementation details.
