"""
Trading Monitor Agent — Watches markets and sends alerts.
Monitors crypto positions, tracks signals, generates P&L summaries.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from core.base_agent import BaseAgent
from core.llm import TaskComplexity


class TradingMonitorAgent(BaseAgent):
    name = "trading_monitor"
    description = "Monitors trading positions, tracks signals, sends alerts"
    schedule = "every 15 minutes"

    def get_tools(self) -> list:

        @tool
        def get_market_data(symbol: str) -> str:
            """Fetch current price, 24h change, and volume for a trading pair."""
            # TODO: Implement with ccxt or Binance API
            return f"[Placeholder] Would fetch market data for {symbol}"

        @tool
        def check_open_positions() -> str:
            """Check all open perpetual futures positions."""
            # TODO: Implement with exchange API
            return "[Placeholder] Would check open positions on configured exchanges"

        @tool
        def analyze_signals(symbol: str) -> str:
            """Run technical analysis and check for trading signals."""
            return f"[Placeholder] Would analyze RSI, MACD, volume for {symbol}"

        @tool
        def place_order(symbol: str, side: str, amount: float, order_type: str = "limit") -> str:
            """Place a trade order. ALWAYS requires approval."""
            return f"[Placeholder] Would place {side} {order_type} order for {amount} {symbol}"

        @tool
        def get_pnl_summary() -> str:
            """Get profit/loss summary for the day/week."""
            return "[Placeholder] Would calculate P&L from exchange data"

        return [get_market_data, check_open_positions, analyze_signals, place_order, get_pnl_summary]

    def get_system_prompt(self) -> str:
        watchlist = self.config.get("watchlist", ["BTC/USDT", "ETH/USDT"])
        alerts = self.config.get("alerts", {})
        return f"""You are the Trading Monitor agent for Holus.

Your mission: Monitor crypto markets, track positions, and alert the user on significant events.

WATCHLIST: {', '.join(watchlist)}

ALERT THRESHOLDS:
- Price change: {alerts.get('price_change_pct', 3)}%+ in any direction
- Volume spike: {alerts.get('volume_spike_multiplier', 2)}x normal volume

WORKFLOW (each run):
1. Check all open positions — any liquidation risks?
2. Fetch market data for watchlist
3. Run signal analysis on top movers
4. If significant event detected → send alert
5. Every 4th run → generate P&L summary

RULES:
- NEVER place trades without explicit user approval
- Always include risk assessment in alerts
- Track all alerts in memory to avoid spam (don't re-alert same event)
- Include relevant context from memory when alerting
"""

    async def run(self) -> dict[str, Any]:
        logger.info("📈 Trading Monitor scanning markets...")

        result = await self.execute(
            "Check market conditions for my watchlist. "
            "Report any significant price movements, volume spikes, or position risks. "
            "If nothing notable, just log and move on.",
            complexity=TaskComplexity.SIMPLE,
        )

        # Only notify if something significant
        if any(word in result.lower() for word in ["alert", "significant", "risk", "spike", "liquidation"]):
            await self.notify(f"📈 *Market Alert*\n\n{result[:500]}")

        self.remember(
            f"Market scan: {result[:200]}",
            metadata={"type": "market_scan"},
        )

        return {"status": "completed", "result": result}
