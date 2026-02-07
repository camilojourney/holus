# OpenClaw Integration

**Spec ID:** 007
**Status:** Draft
**Role:** DevOps
**Priority:** Medium

## Problem / Goal

Leverage OpenClaw's powerful tools (exec, browser, web_search, nodes, etc.) within Holus agents for advanced automation without reinventing capabilities. Provide API bridge and shared memory for seamless integration.

## Solution Overview

Create a shared OpenClaw client as a tool available to all agents. Use OpenClaw's exec for shell commands, browser for scraping, and message for notifications. Implement shared memory via OpenClaw workspace files or ChromaDB sync.

## Acceptance Criteria

- [ ] OpenClaw tools accessible via tools/openclaw.py
- [ ] Agents can call OpenClaw browser for job scraping/trading charts
- [ ] Shared memory: Holus ChromaDB <-> OpenClaw workspace sync
- [ ] API bridge: Holus dashboard exposes OpenClaw endpoints
- [ ] Exec tool for local shell (e.g., ollama manage)

## Scope

### In Scope
- OpenClaw Python client integration
- Tool wrappers for exec, browser, web_search
- Memory sync script

### Out of Scope
- Full OpenClaw agent spawning from Holus
- Node/camera integration (future)

## Technical Details

### Components
- `tools/openclaw.py` — Client and tool wrappers
- `core/openclaw_bridge.py` — Memory/API sync

## Implementation Notes

Use OpenClaw's function call format. Auth via workspace config. Run Holus as OpenClaw sub-agent where possible.

## Dependencies
- requests or OpenClaw SDK
- Holus orchestrator

## Testing
- [ ] Mock tests for tool calls
- [ ] Integration: scrape job via browser tool
