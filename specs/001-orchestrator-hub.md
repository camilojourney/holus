# Orchestrator Hub

**Spec ID:** 001
**Status:** Ready
**Role:** Backend Developer
**Priority:** High

## Problem / Goal

Holus requires a central orchestrator to route incoming tasks to the appropriate specialized agent, manage scheduling, handle shared resources like memory and notifications, and provide a dashboard for monitoring. Without this hub, agents operate in isolation without coordination.

## Solution Overview

Implement the Holus Hub using Python with APScheduler for task scheduling, FastAPI for the dashboard/API, and LangGraph for agent routing. The hub acts as the single entrypoint for tasks, either from schedules, API calls, or external triggers (e.g., Telegram commands).

## Acceptance Criteria

- [ ] Routes tasks to correct agent based on type/content
- [ ] Schedules agent executions per config (e.g., every 6h for job hunter)
- [ ] Manages shared ChromaDB memory across agents
- [ ] Sends notifications via Telegram/SMS
- [ ] Exposes FastAPI dashboard at :8080 for logs/status
- [ ] Handles health checks and restarts failed agents
- [ ] Supports human-in-the-loop approvals

## Scope

### In Scope
- core/orchestrator.py implementation
- Scheduling with APScheduler
- Task routing logic
- Integration with base_agent.py
- Basic dashboard with agent status/logs

### Out of Scope
- Advanced ML-based routing
- Multi-machine scaling
- Voice interface

## Technical Details

### Components
- `core/orchestrator.py` — Main hub loop and router
- `dashboard/app.py` — FastAPI server
- `core/notifier.py` — Notification abstraction

### Data Model
No new DB tables; uses existing ChromaDB collections: `shared_memory`, `agent_logs`

## Implementation Notes

Use LangGraph for stateful workflows. Route simple categorization to local Ollama, complex to cloud. Ensure thread-safety for concurrent agents.

## Dependencies
- APScheduler
- FastAPI + HTMX for dashboard
- ChromaDB

## Testing
- [ ] Unit tests for routing logic
- [ ] Integration tests for scheduling
- [ ] E2E test: hub starts, schedules mock agent
