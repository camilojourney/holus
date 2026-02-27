"""Trading agent with LangGraph: three-component pipeline with mandatory air gap.

Architecture:
  SignalGenerator (Sonnet, no broker access)
    -> RiskManager (always Opus)
      -> HumanReview (interrupt for >$500)
        -> ExecutionHandler (Alpaca, no AI reasoning)

The signal generator CANNOT access the broker API.
The execution handler does NOT use AI reasoning.
These are structural safety guarantees, not policy.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from holus.agents.base import BaseAgent
from holus.agents.trading.models import TradingState
from holus.core.events import EventType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SIGNAL_GENERATOR_PROMPT = """You are the Signal Generator for the Holus Trading Agent.
Your role: analyze market data and generate trading signals.

## Identity
- Agent: signal-generator (part of trading-agent)
- Model tier: operational (Sonnet)
- Authority: Generate signals ONLY. You have ZERO access to broker APIs.

## Guardrails
- Only generate signals with confidence > 0.7
- Always provide specific reasoning referencing the data
- Include entry price, direction, and confidence

## Output Format
Return a JSON array of signals:
[{"ticker": "AAPL", "direction": "long", "confidence": 0.85, "reasoning": "...", "entry_price": 185.50}]
"""

RISK_MANAGER_PROMPT = """You are the Risk Manager for the Holus Trading Agent.
ALWAYS evaluate independently -- never trust the signal generator blindly.

## Guardrails (NEVER VIOLATE)
- Maximum 2% of portfolio per trade
- Maximum 25% total portfolio exposure
- Stop loss REQUIRED on every trade
- If portfolio drawdown > 5% this week, REJECT ALL trades

## Output Format (JSON only)
{"approved": true/false, "position_size": N, "stop_loss": N, "take_profit": N,
 "risk_score": 0.0-1.0, "rejection_reason": "..." or null, "max_loss_usd": N}
"""


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def signal_generator(state: TradingState) -> dict[str, Any]:
    """Read market data, produce trading signals.  Uses Sonnet.  No broker access."""
    from langchain_anthropic import ChatAnthropic

    sonnet = ChatAnthropic(model="claude-sonnet-4-5-20250514", temperature=0, max_tokens=2048)

    market_data = state["market_data"]
    portfolio = state["portfolio_state"]

    response = sonnet.invoke(
        [
            {"role": "system", "content": SIGNAL_GENERATOR_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Market Data: {json.dumps(market_data)}\n"
                    f"Portfolio State: {json.dumps(portfolio)}\n\n"
                    "Generate trading signals. Output as JSON array."
                ),
            },
        ]
    )

    try:
        signals = json.loads(response.content)
        if not isinstance(signals, list):
            signals = [signals]
    except (json.JSONDecodeError, TypeError):
        signals = []

    return {
        "signals": signals,
        "messages": [{"node": "signal_generator", "output": signals}],
    }


def risk_manager(state: TradingState) -> dict[str, Any]:
    """Validate signals against guardrails.  ALWAYS runs on Opus."""
    from langchain_anthropic import ChatAnthropic

    opus = ChatAnthropic(model="claude-opus-4-20250514", temperature=0, max_tokens=4096)

    signals = state["signals"]
    portfolio = state["portfolio_state"]

    if not signals:
        return {
            "risk_assessment": {"approved": False, "rejection_reason": "No signals generated"},
            "messages": [{"node": "risk_manager", "output": "No signals to evaluate"}],
        }

    best_signal = max(signals, key=lambda s: s.get("confidence", 0))

    response = opus.invoke(
        [
            {"role": "system", "content": RISK_MANAGER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Signal: {json.dumps(best_signal)}\n"
                    f"Portfolio: {json.dumps(portfolio)}\n\n"
                    "Evaluate this signal. Return JSON with: approved, position_size, "
                    "stop_loss, take_profit, risk_score, rejection_reason, max_loss_usd"
                ),
            },
        ]
    )

    try:
        assessment = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        assessment = {"approved": False, "rejection_reason": "Risk manager produced invalid JSON"}

    return {
        "risk_assessment": assessment,
        "messages": [{"node": "risk_manager", "output": assessment}],
    }


def human_review(state: TradingState) -> dict[str, Any]:
    """Human-in-the-loop interrupt for high-value trades.

    Uses LangGraph's ``interrupt()`` to pause execution and wait for
    human input via the API or Slack webhook.
    """
    assessment = state["risk_assessment"] or {}
    signals = state.get("signals", [])
    best_signal = max(signals, key=lambda s: s.get("confidence", 0)) if signals else {}

    price = state.get("market_data", {}).get("price", 0)
    position_value = assessment.get("position_size", 0) * price

    human_decision = interrupt(
        {
            "question": "Approve this trade?",
            "signal": best_signal,
            "risk_assessment": assessment,
            "position_value": position_value,
        }
    )

    approved = human_decision.get("approved", False) if isinstance(human_decision, dict) else False

    return {
        "human_approval": approved,
        "messages": [{"node": "human_review", "output": f"Human approved: {approved}"}],
    }


def execution_handler(state: TradingState) -> dict[str, Any]:
    """The ONLY node with broker API access.  No AI reasoning.

    Executes the validated trade via Alpaca.  This is a deterministic
    node -- it translates the risk-approved signal into an API call.
    """
    assessment = state.get("risk_assessment") or {}
    signals = state.get("signals", [])
    best_signal = max(signals, key=lambda s: s.get("confidence", 0)) if signals else {}

    if not best_signal or not assessment.get("approved"):
        return {
            "execution_result": {"status": "skipped", "reason": "Not approved"},
            "messages": [{"node": "execution_handler", "output": "Trade skipped"}],
        }

    try:
        from holus.core.config import HolusConfig
        from holus.integrations.alpaca import AlpacaClient, AlpacaConfig, TradingGuardrails

        config = HolusConfig.load()
        alpaca = AlpacaClient(
            config=AlpacaConfig(
                api_key=config.alpaca_api_key,
                secret_key=config.alpaca_secret_key,
            ),
            guardrails=TradingGuardrails(),
        )

        result = alpaca.submit_order(
            symbol=best_signal.get("ticker", ""),
            qty=assessment.get("position_size", 0),
            side="buy" if best_signal.get("direction") == "long" else "sell",
        )

        return {
            "execution_result": result,
            "messages": [{"node": "execution_handler", "output": result}],
        }
    except Exception as exc:
        logger.exception("Trade execution failed")
        return {
            "error": str(exc),
            "execution_result": {"status": "failed", "error": str(exc)},
            "messages": [{"node": "execution_handler", "error": str(exc)}],
        }


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------


def should_proceed_to_execution(state: TradingState) -> str:
    """Conditional edge: route based on risk assessment."""
    assessment = state.get("risk_assessment")
    if not assessment or not assessment.get("approved"):
        return "rejected"

    price = state.get("market_data", {}).get("price", 0)
    position_value = assessment.get("position_size", 0) * price
    if position_value > 500:
        return "needs_human_approval"

    return "auto_approved"


def check_human_approval(state: TradingState) -> str:
    """After human review, route to execution or rejection."""
    if state.get("human_approval"):
        return "approved"
    return "rejected"


# ---------------------------------------------------------------------------
# TradingAgent
# ---------------------------------------------------------------------------


class TradingAgent(BaseAgent):
    """LangGraph-based trading agent with three-component air-gapped pipeline."""

    agent_name = "trading-agent"

    @property
    def system_prompt(self) -> str:
        return SIGNAL_GENERATOR_PROMPT

    def build_graph(self) -> StateGraph:
        """Construct the trading pipeline graph."""
        graph = StateGraph(TradingState)

        # Nodes
        graph.add_node("signal_generator", signal_generator)
        graph.add_node("risk_manager", risk_manager)
        graph.add_node("human_review", human_review)
        graph.add_node("execution_handler", execution_handler)

        # Edges
        graph.add_edge(START, "signal_generator")
        graph.add_edge("signal_generator", "risk_manager")

        graph.add_conditional_edges(
            "risk_manager",
            should_proceed_to_execution,
            {
                "auto_approved": "execution_handler",
                "needs_human_approval": "human_review",
                "rejected": END,
            },
        )

        graph.add_conditional_edges(
            "human_review",
            check_human_approval,
            {
                "approved": "execution_handler",
                "rejected": END,
            },
        )

        graph.add_edge("execution_handler", END)

        return graph

    def default_state(self) -> dict[str, Any]:
        return {
            "market_data": {},
            "portfolio_state": {},
            "signals": [],
            "risk_assessment": None,
            "human_approval": None,
            "execution_result": None,
            "messages": [],
            "error": None,
        }

    async def run_trading_cycle(
        self,
        market_data: dict[str, Any],
        portfolio_state: dict[str, Any],
        *,
        thread_id: str | None = None,
        checkpointer=None,
    ) -> dict[str, Any]:
        """Execute one full trading cycle.

        Args:
            market_data: Current market data (OHLCV, indicators, sentiment).
            portfolio_state: Current portfolio snapshot.
            thread_id: LangGraph thread ID for checkpointing.
            checkpointer: LangGraph checkpointer for persistence.

        Returns:
            Final state dict with signals, assessment, and execution result.
        """
        self.check_kill_switch()

        state = self.default_state()
        state["market_data"] = market_data
        state["portfolio_state"] = portfolio_state

        result = await self.run(state, thread_id=thread_id, checkpointer=checkpointer)

        # Publish events
        if result.get("execution_result", {}).get("status") not in (None, "skipped", "failed"):
            self.publish_event(
                "holus.trading.signals",
                EventType.TRADE_EXECUTED,
                payload=result.get("execution_result", {}),
            )

        return result
