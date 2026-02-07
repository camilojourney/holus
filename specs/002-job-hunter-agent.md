# Job Hunter Agent

**Spec ID:** 001
**Status:** Draft
**Role:** Backend Developer
**Priority:** High

## Problem / Goal

Manual job searching is time-consuming and inefficient. This agent automates the discovery, filtering, and application process for relevant job opportunities, allowing the user to focus on interviews and offers.

## Solution Overview

Implement a specialized agent that scrapes job boards, matches against user preferences, auto-applies where possible, and generates personalized cover letters. It reports daily summaries and requires human review for complex applications.

## Acceptance Criteria

- [ ] Scrapes jobs from LinkedIn, Wellfound, Lever, Greenhouse
- [ ] Filters jobs based on salary ($150k-180k), role (AI/data), location (NYC)
- [ ] Auto-fills applications for supported platforms
- [ ] Generates tailored cover letters
- [ ] Sends daily reports via Telegram
- [ ] Runs every 6 hours autonomously

## Scope

### In Scope
- Job scraping from specified boards
- Resume-based matching
- Auto-application functionality
- Cover letter generation
- Daily reporting

### Out of Scope
- Other job boards
- Negotiation or interview scheduling
- Salary negotiation

## Technical Details

### Components
- `job_hunter/agent.py` — Main agent logic
- `job_hunter/tools.py` — Scraping and application tools
- `job_hunter/prompts.py` — System prompts for matching and generation

### Data Model
Jobs stored in ChromaDB with fields: title, company, location, salary, description, url, status

## Implementation Notes

Use Playwright for browser automation, LangChain for AI matching and generation. Ensure rate limiting to avoid bans.

## Dependencies

- Browser automation tools
- LLM for cover letter generation
- Telegram notifications

## Testing

- [ ] Unit tests for scraping functions
- [ ] Integration tests for job matching
- [ ] Manual testing of auto-applications