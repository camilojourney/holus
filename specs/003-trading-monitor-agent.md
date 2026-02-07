# Trading Monitor Agent

**Spec ID:** 002
**Status:** Draft
**Role:** Backend Developer
**Priority:** High

## Problem / Goal

Manual trading monitoring is stressful and prone to missing opportunities or risks. This agent provides 24/7 market surveillance for crypto perpetual futures, alerts on key events, and enables automated trading with human oversight.

## Solution Overview

Build an agent that integrates with trading APIs to monitor positions, calculate indicators, send real-time alerts, and generate P&L reports. Includes a confirmation gate for trade execution to ensure safety.

## Acceptance Criteria

- [ ] Monitors crypto perpetual futures positions
- [ ] Tracks key indicators and signals
- [ ] Sends alerts on significant market moves
- [ ] Generates daily P&L summaries
- [ ] Executes trades via API with user confirmation
- [ ] Runs every 15 minutes during market hours, hourly off-hours

## Scope

### In Scope
- Crypto futures monitoring
- Indicator tracking and alerting
- P&L reporting
- API-based trade execution with gate

### Out of Scope
- Other asset classes
- Fully autonomous trading without gates

## Technical Details

### Components
- `trading_monitor/agent.py` — Main agent logic
- `trading_monitor/tools.py` — API integration and calculation tools
- `trading_monitor/prompts.py` — System prompts for strategy

### Data Model
Trades and positions in ChromaDB: symbol, position, entry_price, current_price, pnl, alerts

## Implementation Notes

Integrate with crypto exchange APIs. Use technical analysis libraries for indicators. Ensure secure API key handling.

## Dependencies

- Trading API integrations
- Telegram for alerts
- Confirmation mechanism

## Testing

- [ ] Unit tests for indicator calculations
- [ ] Integration tests with API (mocked)
- [ ] Manual testing of alerts and reports