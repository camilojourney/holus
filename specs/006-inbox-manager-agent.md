# Inbox Manager Agent

**Spec ID:** 005
**Status:** Draft
**Role:** Backend Developer
**Priority:** High

## Problem / Goal

Email inbox management is a daily chore that distracts from important work. This agent automates triage, categorization, and response drafting for efficient email handling.

## Solution Overview

Build an agent that connects to Gmail API, categorizes emails using AI, drafts responses for routine messages, researches senders, and notifies via Telegram for escalations.

## Acceptance Criteria

- [ ] Categorizes emails: opportunity/spam/action/FYI
- [ ] Drafts responses for routine emails
- [ ] Escalates important emails via Telegram
- [ ] Researches senders automatically
- [ ] Runs every 30 minutes

## Scope

### In Scope
- Gmail API integration
- AI-based categorization
- Response drafting
- Sender research
- Notification routing

### Out of Scope
- Other email providers
- Sending emails autonomously

## Technical Details

### Components
- `inbox_manager/agent.py` — Main agent logic
- `inbox_manager/tools.py` — Gmail API and research tools
- `inbox_manager/prompts.py` — Categorization and drafting prompts

### Data Model
Emails in ChromaDB: subject, sender, category, draft_response, research_notes

## Implementation Notes

Use Gmail API for access. LLM for categorization and drafting. Web search for sender research.

## Dependencies

- Gmail API
- Telegram notifications
- Web search tools

## Testing

- [ ] Unit tests for categorization logic
- [ ] Integration tests with Gmail API mocks
- [ ] Manual testing of drafts and escalations