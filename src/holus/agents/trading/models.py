"""Trading agent data models.

These Pydantic models define the structured data that flows through
the trading pipeline: signals, risk assessments, executions, and portfolio state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, TypedDict

import operator
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models (validation boundaries)
# ---------------------------------------------------------------------------

class TradeSignal(BaseModel):
    """A trading signal produced by the signal generator node."""

    ticker: str
    direction: Literal["long", "short"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    entry_price: float | None = None
    signal_source: str = "sonnet-signal-generator"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RiskAssessment(BaseModel):
    """Risk manager output -- validates a signal against guardrails."""

    approved: bool
    position_size: float = Field(default=0.0, ge=0.0)
    stop_loss: float | None = None
    take_profit: float | None = None
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rejection_reason: str | None = None
    max_loss_usd: float | None = None


class TradeExecution(BaseModel):
    """Result of executing a trade through Alpaca."""

    order_id: str
    symbol: str
    qty: float
    side: Literal["buy", "sell"]
    status: str
    fill_price: float | None = None
    submitted_at: datetime | None = None
    error: str | None = None


class PortfolioState(BaseModel):
    """Snapshot of the current portfolio."""

    portfolio_value: float
    buying_power: float
    equity: float
    cash: float
    positions: list[dict] = Field(default_factory=list)
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    total_exposure_pct: float = 0.0


# ---------------------------------------------------------------------------
# LangGraph state (TypedDict for graph flow)
# ---------------------------------------------------------------------------

class TradingState(TypedDict):
    """State flowing through the trading LangGraph pipeline.

    Nodes read from and write to specific keys.  The ``messages`` list
    uses ``operator.add`` as a reducer for accumulation across nodes.
    """

    # Inputs
    market_data: dict
    portfolio_state: dict

    # Pipeline state
    signals: list[dict]
    risk_assessment: dict | None
    human_approval: bool | None
    execution_result: dict | None

    # Observability (accumulating)
    messages: Annotated[list, operator.add]

    # Error tracking
    error: str | None
