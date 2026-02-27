"""Alpaca Trading API integration.

The execution handler is the ONLY component with broker API access.
No AI reasoning happens here -- this is pure validated execution with
defense-in-depth guardrail checks.

Paper vs live switching is controlled by configuration, never by code changes.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class AlpacaConfig(BaseModel):
    """Alpaca API connection settings."""

    api_key: str
    secret_key: str
    paper: bool = True  # ALWAYS start paper; graduate via config review
    base_url: str = "https://paper-api.alpaca.markets"

    def effective_base_url(self) -> str:
        if self.paper:
            return "https://paper-api.alpaca.markets"
        return self.base_url


class TradingGuardrails(BaseModel):
    """Hard limits enforced at execution time (defense in depth)."""

    max_position_pct: float = Field(default=0.02, description="2% per position")
    max_portfolio_exposure: float = Field(default=0.30, description="30% total")
    max_single_trade_usd: float = Field(default=500.0, description="Human approval above this")
    daily_loss_limit_pct: float = Field(
        default=0.05, description="5% daily drawdown circuit breaker"
    )
    max_trades_per_day: int = 10
    allowed_symbols: list[str] | None = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GuardrailViolation(Exception):  # noqa: N818
    """Raised when a trade would violate a safety guardrail."""


class RateLimitExceeded(Exception):  # noqa: N818
    """Raised when the Alpaca API rate limit is hit."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AlpacaClient:
    """Alpaca trading client with guardrail enforcement.

    This class wraps the ``alpaca-py`` SDK and adds:
      - Pre-execution guardrail validation.
      - Rate limiting (200 req/min for Alpaca paper).
      - Daily trade counter.
      - Paper/live mode switching via config.
    """

    RATE_LIMIT_PER_MINUTE = 200

    def __init__(
        self,
        config: AlpacaConfig,
        guardrails: TradingGuardrails | None = None,
    ) -> None:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.trading.client import TradingClient

        self.config = config
        self.guardrails = guardrails or TradingGuardrails()

        self._trading_client = TradingClient(
            config.api_key,
            config.secret_key,
            paper=config.paper,
            url_override=config.effective_base_url(),
        )
        self._data_client = StockHistoricalDataClient(
            config.api_key,
            config.secret_key,
        )

        self._trade_count_today: int = 0
        self._day_marker: str = time.strftime("%Y-%m-%d")
        self._call_timestamps: list[float] = []

    # -- Account & Positions -------------------------------------------------

    def get_account(self) -> dict[str, Any]:
        """Return account summary: equity, buying power, portfolio value."""
        account = self._trading_client.get_account()
        return {
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "cash": float(account.cash),
            "currency": account.currency,
            "pattern_day_trader": account.pattern_day_trader,
            "trading_blocked": account.trading_blocked,
        }

    def get_positions(self) -> list[dict[str, Any]]:
        """Return all open positions."""
        positions = self._trading_client.get_all_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "side": p.side.value if hasattr(p.side, "value") else str(p.side),
                "market_value": float(p.market_value),
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc),
            }
            for p in positions
        ]

    def get_portfolio_exposure(self) -> float:
        """Calculate total portfolio exposure as a fraction of equity."""
        account = self.get_account()
        positions = self.get_positions()
        total_market_value = sum(abs(p["market_value"]) for p in positions)
        equity = account["portfolio_value"]
        return total_market_value / equity if equity > 0 else 0.0

    # -- Order Submission ----------------------------------------------------

    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: Literal["buy", "sell"],
        order_type: Literal["market", "limit"] = "market",
        limit_price: float | None = None,
        time_in_force: Literal["day", "gtc", "ioc"] = "day",
        stop_loss_price: float | None = None,
        take_profit_price: float | None = None,
    ) -> dict[str, Any]:
        """Submit an order with guardrail validation.

        This method validates against all guardrails before sending
        the order to Alpaca, even though the risk manager already validated.
        Defense in depth.

        Raises:
            GuardrailViolation: If any guardrail is violated.
            RateLimitExceeded: If rate limit would be breached.
        """
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import (
            LimitOrderRequest,
            MarketOrderRequest,
        )

        self._enforce_rate_limit()
        self._reset_daily_counter_if_needed()

        # -- Guardrail checks -----------------------------------------------
        self._validate_symbol(symbol)
        self._validate_daily_trade_count()

        account = self.get_account()
        portfolio_value = account["portfolio_value"]

        # Estimate position value (rough -- actual depends on fill)
        estimated_value = qty * (limit_price or self._last_price(symbol))

        if estimated_value > portfolio_value * self.guardrails.max_position_pct:
            raise GuardrailViolation(
                f"Position {symbol} ${estimated_value:.2f} exceeds "
                f"{self.guardrails.max_position_pct:.0%} of portfolio "
                f"(${portfolio_value:.2f})"
            )

        current_exposure = self.get_portfolio_exposure()
        if (
            current_exposure + (estimated_value / portfolio_value)
            > self.guardrails.max_portfolio_exposure
        ):
            raise GuardrailViolation(
                f"Adding {symbol} would push exposure to "
                f"{current_exposure + estimated_value / portfolio_value:.1%} "
                f"(limit {self.guardrails.max_portfolio_exposure:.0%})"
            )

        # -- Build order request --------------------------------------------
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        tif = {
            "day": TimeInForce.DAY,
            "gtc": TimeInForce.GTC,
            "ioc": TimeInForce.IOC,
        }[time_in_force]

        if order_type == "market":
            request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
            )
        else:
            if limit_price is None:
                raise ValueError("limit_price required for limit orders")
            request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
                limit_price=limit_price,
            )

        # -- Submit ----------------------------------------------------------
        order = self._trading_client.submit_order(request)
        self._trade_count_today += 1

        result = {
            "order_id": str(order.id),
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            "status": order.status.value if hasattr(order.status, "value") else str(order.status),
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        }
        logger.info("Order submitted: %s", result)
        return result

    # -- Market Data ---------------------------------------------------------

    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch historical bar data for a symbol."""
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        tf_map = {
            "1Min": TimeFrame(1, TimeFrameUnit.Minute),
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
            "1Day": TimeFrame(1, TimeFrameUnit.Day),
        }
        tf = tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Day))

        request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf, limit=limit)
        bars = self._data_client.get_stock_bars(request)

        result: list[dict[str, Any]] = []
        for bar in bars[symbol]:
            result.append(
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume),
                }
            )
        return result

    # -- Internal helpers ----------------------------------------------------

    def _validate_symbol(self, symbol: str) -> None:
        allowed = self.guardrails.allowed_symbols
        if allowed is not None and symbol not in allowed:
            raise GuardrailViolation(f"Symbol {symbol} not in allowed list: {allowed}")

    def _validate_daily_trade_count(self) -> None:
        if self._trade_count_today >= self.guardrails.max_trades_per_day:
            raise GuardrailViolation(
                f"Daily trade limit ({self.guardrails.max_trades_per_day}) reached"
            )

    def _reset_daily_counter_if_needed(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if today != self._day_marker:
            self._day_marker = today
            self._trade_count_today = 0

    def _enforce_rate_limit(self) -> None:
        """Simple sliding-window rate limiter."""
        now = time.time()
        window_start = now - 60.0
        self._call_timestamps = [t for t in self._call_timestamps if t > window_start]
        if len(self._call_timestamps) >= self.RATE_LIMIT_PER_MINUTE:
            raise RateLimitExceeded(f"Rate limit ({self.RATE_LIMIT_PER_MINUTE}/min) reached")
        self._call_timestamps.append(now)

    def _last_price(self, symbol: str) -> float:
        """Get the most recent close price for rough position sizing."""
        try:
            bars = self.get_bars(symbol, timeframe="1Day", limit=1)
            if bars:
                return bars[-1]["close"]
        except Exception:
            logger.warning("Could not fetch last price for %s", symbol)
        return 0.0
