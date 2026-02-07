# Research Scout Agent

**Spec ID:** 004
**Status:** Draft
**Role:** Backend Developer
**Priority:** Medium

## Problem / Goal

Staying updated with the latest research and projects in AI/ML is overwhelming. This agent continuously monitors sources and delivers curated, summarized digests to keep the user informed without constant checking.

## Solution Overview

Create an agent that scrapes GitHub trending, arXiv papers, newsletters, and RSS feeds in relevant domains, summarizes key findings, and sends weekly digests.

## Acceptance Criteria

- [ ] Monitors GitHub trending for AI/ML
- [ ] Tracks arXiv papers in user domains
- [ ] Summarizes newsletters and RSS feeds
- [ ] Generates weekly digest reports
- [ ] Runs daily for digests, continuous for monitoring

## Scope

### In Scope
- GitHub trending scraping
- arXiv monitoring
- RSS feed aggregation
- Weekly summarization

### Out of Scope
- Full paper downloads
- Non-AI/ML domains

## Technical Details

### Components
- `research_scout/agent.py` — Main agent logic
- `research_scout/tools.py` — Scraping and summarization tools
- `research_scout/prompts.py` — Summarization prompts

### Data Model
Research items in ChromaDB: source, title, summary, url, date

## Implementation Notes

Use web scraping for GitHub/arXiv. RSS parsing libraries. LLM for summarization.

## Dependencies

- Web scraping tools
- RSS libraries
- Telegram for digests

## Testing

- [ ] Unit tests for scraping functions
- [ ] Integration tests for summarization
- [ ] Manual verification of digests