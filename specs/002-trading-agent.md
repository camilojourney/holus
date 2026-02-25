# Spec 002: Trading Agent

## Feature: Autonomous trading agent with three-component pipeline, mandatory safety guardrails, and tiered memory

### Overview

The trading agent is the highest-stakes agent in Holus. It analyzes market data, generates trading signals, validates them against risk guardrails, and executes trades via the Alpaca API. The architecture enforces strict component separation regardless of model capability: a SignalGenerator (reads data, no broker access), a RiskManager (validates signals, always Opus), and an ExecutionHandler (pure execution, no AI reasoning). This structural separation makes it physically impossible for a signal generation error to execute a trade without risk validation. See [ADR-0002](../docs/decisions/0002-claude-first-intelligence.md) for the Claude-first intelligence rationale and [HOLUS-ARCHITECTURE-DECISIONS.md](../../HOLUS-ARCHITECTURE-DECISIONS.md) Section 2A for the full trading architecture.

### User Stories

- As a founder, I want the trading agent to paper-trade for 30+ days before touching real capital so that I can verify its performance against codified graduation criteria.
- As a founder, I want a human-in-the-loop approval for any trade above $500 so that high-value decisions always have a safety check.
- As a founder, I want circuit breakers that automatically halt trading when drawdown exceeds thresholds so that losses are bounded even if I am not monitoring.
- As a founder, I want a tiered memory system that extracts patterns from individual trades so that the agent improves its signal quality over time.

---

### Core Specifications

**SPEC-001: Signal Generator**

| Field | Value |
|-------|-------|
| Description | Analyzes market data (Alpaca SIP feed), news sentiment (FinBERT), and technical indicators to produce trading signals. Has zero broker API access. |
| Trigger | Scheduled via n8n (daily at market open for swing trades, or configurable interval) |
| Input | Market data (OHLCV bars, volume profile), news headlines (via Alpaca news API), technical indicators (RSI, MACD, Bollinger Bands), L2 episodic memory patterns, L3 semantic principles |
| Output | `TradingSignal` object with symbol, direction, confidence, reasoning, suggested position size |
| Validation | Signal must include reasoning chain. Confidence must be 0.0-1.0. Symbol must be in `allowed_symbols` whitelist (if configured). |
| Auth Required | `ALPACA_API_KEY` (data access only, NOT trading API) |

```python
# src/holus/agents/trading/signal_generator.py

from pydantic import BaseModel, field_validator
from datetime import datetime

class TradingSignal(BaseModel):
    signal_id: str
    timestamp: datetime
    symbol: str
    direction: str  # "long" | "short" | "close"
    confidence: float  # 0.0 to 1.0
    reasoning: str  # AI-generated explanation of why this signal
    suggested_quantity: int
    suggested_entry_price: float | None  # None = market order
    stop_loss_price: float
    take_profit_price: float
    signal_sources: list[str]  # ["technical_rsi", "sentiment_positive", "l2_pattern_match"]
    market_conditions: dict  # Volatility regime, trend, sector performance
    finbert_sentiment: dict | None  # FinBERT output if news-driven

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        if v not in ("long", "short", "close"):
            raise ValueError("Direction must be 'long', 'short', or 'close'")
        return v
```

FinBERT integration (runs locally on Mac Mini, not a reasoning task):

```python
# src/holus/integrations/finbert/sentiment.py

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class FinBERTAnalyzer:
    MODEL_NAME = "ProsusAI/finbert"

    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME)
        self.model.eval()

    def analyze(self, text: str) -> dict:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]
        labels = ["positive", "negative", "neutral"]
        scores = {label: round(prob.item(), 4) for label, prob in zip(labels, probs)}
        return {
            "sentiment": max(scores, key=scores.get),
            "confidence": max(scores.values()),
            "scores": scores,
        }

    def analyze_batch(self, headlines: list[str]) -> dict:
        results = [self.analyze(h) for h in headlines]
        avg_scores = {
            "positive": sum(r["scores"]["positive"] for r in results) / len(results),
            "negative": sum(r["scores"]["negative"] for r in results) / len(results),
            "neutral": sum(r["scores"]["neutral"] for r in results) / len(results),
        }
        return {
            "overall_sentiment": max(avg_scores, key=avg_scores.get),
            "average_scores": avg_scores,
            "headline_count": len(headlines),
            "individual_results": results,
        }
```

Acceptance Criteria:
- [ ] SignalGenerator produces `TradingSignal` objects with all required fields populated
- [ ] SignalGenerator has ZERO access to `TradingClient` or any broker execution API
- [ ] FinBERT runs locally and returns sentiment scores in <100ms per headline
- [ ] Model routing: SignalGenerator uses Sonnet 4.5 for standard evaluation, Opus 4 for novel market conditions
- [ ] Signals include reasoning chain explaining the analysis logic
- [ ] Signals reference L2 episodic memory patterns when relevant
- [ ] Signal confidence of 0.0 or below minimum threshold produces no signal (returns early)

---

**SPEC-002: Risk Manager**

| Field | Value |
|-------|-------|
| Description | Validates signals against guardrails, applies position sizing, and enforces risk limits. ALWAYS runs on Opus 4. The last line of defense before execution. |
| Trigger | Receives a `TradingSignal` from SignalGenerator |
| Input | `TradingSignal` + current portfolio state (positions, P&L, exposure) + guardrails config |
| Output | `ValidatedSignal` (approved with final sizing) or `RejectedSignal` (with rejection reason) |
| Validation | Every guardrail check must pass. Any single failure rejects the signal. Human-in-the-loop for trades above `max_single_trade_usd`. |
| Auth Required | `ALPACA_API_KEY` (portfolio state read only, NOT execution) |

```python
# src/holus/agents/trading/risk_manager.py

from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class RiskDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_HUMAN = "pending_human_approval"

class ValidatedSignal(BaseModel):
    signal_id: str
    decision: RiskDecision
    final_quantity: int
    final_direction: str
    symbol: str
    price: float
    stop_loss: float
    take_profit: float
    risk_score: float  # 0.0 (safe) to 1.0 (maximum risk)
    guardrail_checks: list[dict]  # Each check: {"name": str, "passed": bool, "detail": str}
    rejection_reason: str | None = None
    requires_human_approval: bool = False
    opus_reasoning: str  # Full Opus reasoning chain

class TradingGuardrails(BaseModel):
    max_position_pct: float = 0.02       # 2% per position
    max_portfolio_exposure: float = 0.30  # 30% total
    max_single_trade_usd: float = 500.0  # Human approval above this
    daily_loss_limit_pct: float = 0.05   # 5% daily drawdown circuit breaker
    max_trades_per_day: int = 10
    max_consecutive_losses: int = 5      # Pause after 5 consecutive losses
    allowed_symbols: list[str] | None = None
    min_signal_confidence: float = 0.6   # Reject signals below this

class RiskManager:
    """
    ALWAYS Opus 4. Risk validation is the highest-stakes reasoning task.
    """
    MODEL = "claude-opus-4-6"  # Never downgrade this.

    def validate(
        self,
        signal: "TradingSignal",
        portfolio_state: dict,
        guardrails: TradingGuardrails,
    ) -> ValidatedSignal:
        checks = []

        # Check 1: Signal confidence
        passed = signal.confidence >= guardrails.min_signal_confidence
        checks.append({
            "name": "min_confidence",
            "passed": passed,
            "detail": f"Confidence {signal.confidence} vs min {guardrails.min_signal_confidence}",
        })

        # Check 2: Position size limit
        trade_value = signal.suggested_quantity * (signal.suggested_entry_price or 0)
        portfolio_value = portfolio_state["portfolio_value"]
        position_pct = trade_value / portfolio_value if portfolio_value > 0 else 1.0
        passed = position_pct <= guardrails.max_position_pct
        checks.append({
            "name": "position_size",
            "passed": passed,
            "detail": f"Position {position_pct:.2%} vs max {guardrails.max_position_pct:.2%}",
        })

        # Check 3: Total portfolio exposure
        current_exposure = portfolio_state.get("total_exposure_pct", 0.0)
        new_exposure = current_exposure + position_pct
        passed = new_exposure <= guardrails.max_portfolio_exposure
        checks.append({
            "name": "portfolio_exposure",
            "passed": passed,
            "detail": f"New exposure {new_exposure:.2%} vs max {guardrails.max_portfolio_exposure:.2%}",
        })

        # Check 4: Daily loss circuit breaker
        daily_pnl_pct = portfolio_state.get("daily_pnl_pct", 0.0)
        passed = daily_pnl_pct > -guardrails.daily_loss_limit_pct
        checks.append({
            "name": "daily_loss_limit",
            "passed": passed,
            "detail": f"Daily P&L {daily_pnl_pct:.2%} vs limit -{guardrails.daily_loss_limit_pct:.2%}",
        })

        # Check 5: Daily trade count
        trades_today = portfolio_state.get("trades_today", 0)
        passed = trades_today < guardrails.max_trades_per_day
        checks.append({
            "name": "daily_trade_limit",
            "passed": passed,
            "detail": f"Trades today {trades_today} vs max {guardrails.max_trades_per_day}",
        })

        # Check 6: Consecutive losses
        consecutive_losses = portfolio_state.get("consecutive_losses", 0)
        passed = consecutive_losses < guardrails.max_consecutive_losses
        checks.append({
            "name": "consecutive_losses",
            "passed": passed,
            "detail": f"Consecutive losses {consecutive_losses} vs max {guardrails.max_consecutive_losses}",
        })

        # Check 7: Allowed symbols
        if guardrails.allowed_symbols:
            passed = signal.symbol in guardrails.allowed_symbols
            checks.append({
                "name": "symbol_whitelist",
                "passed": passed,
                "detail": f"Symbol {signal.symbol} {'in' if passed else 'NOT in'} whitelist",
            })

        # Determine overall decision
        all_passed = all(c["passed"] for c in checks)
        requires_human = trade_value > guardrails.max_single_trade_usd

        if not all_passed:
            failed = [c for c in checks if not c["passed"]]
            decision = RiskDecision.REJECTED
            rejection_reason = "; ".join(c["detail"] for c in failed)
        elif requires_human:
            decision = RiskDecision.PENDING_HUMAN
            rejection_reason = None
        else:
            decision = RiskDecision.APPROVED
            rejection_reason = None

        # ... Opus reasoning would be injected here via Claude API call ...

        return ValidatedSignal(
            signal_id=signal.signal_id,
            decision=decision,
            final_quantity=signal.suggested_quantity,
            final_direction=signal.direction,
            symbol=signal.symbol,
            price=signal.suggested_entry_price or 0.0,
            stop_loss=signal.stop_loss_price,
            take_profit=signal.take_profit_price,
            risk_score=0.0,  # Computed by Opus
            guardrail_checks=checks,
            rejection_reason=rejection_reason,
            requires_human_approval=requires_human,
            opus_reasoning="",  # Filled by Opus call
        )
```

Acceptance Criteria:
- [ ] RiskManager ALWAYS uses Opus 4 (`claude-opus-4-6`). No config option to downgrade.
- [ ] All 7 guardrail checks run on every signal. Any single failure = rejection.
- [ ] Trades above `max_single_trade_usd` ($500 default) trigger human-in-the-loop via LangGraph `interrupt_before`
- [ ] `ValidatedSignal` includes full reasoning chain from Opus and all guardrail check results
- [ ] Daily loss circuit breaker fires when `daily_pnl_pct` exceeds `-daily_loss_limit_pct`, activating kill switch for trading agent
- [ ] Consecutive loss pause fires after 5 consecutive losses
- [ ] RiskManager has ZERO access to `TradingClient` execution methods

---

**SPEC-003: Execution Handler**

| Field | Value |
|-------|-------|
| Description | The ONLY component with Alpaca broker API access. Executes validated signals. No AI reasoning -- pure deterministic execution with defense-in-depth guardrail re-checks. |
| Trigger | Receives a `ValidatedSignal` with `decision == APPROVED` from RiskManager |
| Input | `ValidatedSignal` + Alpaca API credentials |
| Output | Order confirmation (order_id, status, fill details) or execution error |
| Validation | Defense-in-depth: re-checks position size and daily trade limits even though RiskManager already validated |
| Auth Required | `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` (ONLY component with these) |

```python
# src/holus/agents/trading/execution_handler.py

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from pydantic import BaseModel

class ExecutionResult(BaseModel):
    order_id: str
    symbol: str
    status: str  # "filled" | "partially_filled" | "pending" | "rejected"
    filled_quantity: int
    filled_price: float | None
    timestamp: str

class AlpacaConfig(BaseModel):
    api_key: str
    secret_key: str
    paper: bool = True  # ALWAYS paper until graduation. Changed via config, never code.
    base_url: str = "https://paper-api.alpaca.markets"

class ExecutionHandler:
    """
    ONLY component with broker API access.
    No AI reasoning here. Pure validated execution.
    Defense in depth: re-checks guardrails even though RiskManager already validated.
    """
    def __init__(self, config: AlpacaConfig, guardrails: "TradingGuardrails"):
        self.client = TradingClient(
            config.api_key,
            config.secret_key,
            paper=config.paper,
            url_override=config.base_url,
        )
        self.guardrails = guardrails
        self._trade_count_today = 0

    def execute(self, signal: "ValidatedSignal") -> ExecutionResult:
        if signal.decision != "approved":
            raise ValueError(f"Cannot execute non-approved signal: {signal.decision}")

        # Defense in depth: re-check even after RiskManager approved
        account = self.client.get_account()
        portfolio_value = float(account.portfolio_value)
        trade_value = signal.final_quantity * signal.price

        if trade_value > portfolio_value * self.guardrails.max_position_pct:
            raise GuardrailViolation(
                f"Position size ${trade_value:.2f} exceeds "
                f"{self.guardrails.max_position_pct:.0%} of portfolio ${portfolio_value:.2f}"
            )

        if self._trade_count_today >= self.guardrails.max_trades_per_day:
            raise GuardrailViolation(
                f"Daily trade limit ({self.guardrails.max_trades_per_day}) reached"
            )

        order_request = MarketOrderRequest(
            symbol=signal.symbol,
            qty=signal.final_quantity,
            side=OrderSide.BUY if signal.final_direction == "long" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )

        order = self.client.submit_order(order_request)
        self._trade_count_today += 1

        return ExecutionResult(
            order_id=str(order.id),
            symbol=signal.symbol,
            status=order.status.value,
            filled_quantity=int(order.filled_qty or 0),
            filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
            timestamp=order.submitted_at.isoformat() if order.submitted_at else "",
        )

class GuardrailViolation(Exception):
    pass
```

Acceptance Criteria:
- [ ] ExecutionHandler is the ONLY class that imports `alpaca.trading.client.TradingClient`
- [ ] ExecutionHandler has ZERO AI/LLM imports or calls. Pure deterministic logic.
- [ ] Defense-in-depth position size check catches any signal that somehow bypassed RiskManager
- [ ] `paper: true` is the default. Changing to `false` requires config change AND human approval.
- [ ] Every execution is logged to Langfuse with order details and latency
- [ ] Failed executions (Alpaca errors) are caught, logged, and published as `holus.system.alerts` events
- [ ] `_trade_count_today` resets at market open (not midnight)

---

**SPEC-004: TradeMemory Protocol**

| Field | Value |
|-------|-------|
| Description | Three-tier memory system for trading agent learning. L1 (working: every trade), L2 (episodic: extracted patterns, weekly), L3 (semantic: general principles, monthly). |
| Trigger | L1: after every trade. L2: weekly scheduled job. L3: monthly scheduled job. |
| Input | L1: trade execution data + market context. L2: all L1 trades from last 30 days. L3: all L2 patterns. |
| Output | Structured memories stored in Mem0 with agent-scoped isolation |
| Validation | L1 entries are append-only (never modified). L2 patterns require sample_size >= 5. L3 principles require evidence_count >= 3. |
| Auth Required | Mem0 access (local, no external auth) |

```python
# src/holus/agents/trading/memory.py

from datetime import datetime
from pydantic import BaseModel

class L1WorkingMemory(BaseModel):
    """Every trade with full context. Append-only. Never modified."""
    trade_id: str
    timestamp: datetime
    symbol: str
    direction: str  # "long" | "short"
    entry_price: float
    exit_price: float | None
    quantity: int
    signal_source: str
    signal_confidence: float
    market_conditions: dict  # {"volatility": "high", "trend": "bullish", ...}
    risk_score: float
    guardrail_checks: list[dict]
    outcome: str | None  # "win" | "loss" | "open"
    pnl: float | None
    pnl_pct: float | None
    hold_duration_hours: float | None
    notes: str  # AI-generated context at time of trade

class L2EpisodicMemory(BaseModel):
    """Extracted patterns from L1. Updated weekly by Opus."""
    pattern_id: str
    description: str
    # e.g. "Asian session breakouts on gold failed 4/5 times with RSI > 70"
    confidence: float  # 0.0 to 1.0
    sample_size: int   # Must be >= 5
    date_range: str    # "2026-02-01 to 2026-02-28"
    symbols: list[str]
    conditions: dict   # {"time_of_day": "asian_session", "rsi_range": ">70"}
    win_rate: float
    avg_pnl: float
    avg_pnl_pct: float
    last_validated: datetime
    contradictions: list[str]  # Counter-evidence observed

class L3SemanticMemory(BaseModel):
    """General principles refined over time. Updated monthly by Opus."""
    principle_id: str
    principle: str
    # e.g. "Mean reversion works better than momentum in low-volatility regimes"
    evidence_count: int  # Must be >= 3
    supporting_patterns: list[str]  # L2 pattern_ids
    contradicting_patterns: list[str]
    confidence: float
    last_validated: datetime
    first_observed: datetime
```

Example L2 pattern (stored in Mem0):

```json
{
  "pattern_id": "L2-20260315-001",
  "description": "AAPL tends to gap up on Mondays following Friday closes above 20-day SMA when VIX < 18",
  "confidence": 0.72,
  "sample_size": 11,
  "date_range": "2026-01-15 to 2026-03-15",
  "symbols": ["AAPL"],
  "conditions": {
    "day_of_week": "monday",
    "prior_close_vs_sma20": "above",
    "vix_range": "<18"
  },
  "win_rate": 0.727,
  "avg_pnl": 142.50,
  "avg_pnl_pct": 0.83,
  "last_validated": "2026-03-15T21:00:00Z",
  "contradictions": ["Failed during Feb 2026 rate decision week (L1-20260225-003)"]
}
```

Acceptance Criteria:
- [ ] Every executed trade produces an L1 entry with all fields populated
- [ ] L1 entries are append-only. No update or delete operations exist on L1.
- [ ] L2 extraction runs weekly. Only creates patterns with `sample_size >= 5`.
- [ ] L2 patterns include `contradictions` field listing counter-evidence
- [ ] L3 refinement runs monthly. Only creates principles with `evidence_count >= 3`.
- [ ] All memory operations use Mem0 with `agent_id="trading-agent"` scope isolation
- [ ] L2 and L3 extraction use Opus 4 for pattern synthesis
- [ ] Memory is queryable: "What patterns apply to AAPL in high-volatility regimes?"

---

**SPEC-005: Paper-to-Live Graduation Criteria**

| Field | Value |
|-------|-------|
| Description | Codified criteria that must be met before the trading agent transitions from paper trading to live capital. Graduation requires explicit human review. |
| Trigger | Manual trigger after minimum paper trading period |
| Input | Full paper trading history (all L1 trades), portfolio metrics |
| Output | Graduation report (pass/fail per criterion) + human review prompt |
| Validation | All criteria must pass AND human must explicitly approve |
| Auth Required | Human approval |

```yaml
# config/trading_agent.yaml -- graduation section
graduation_criteria:
  minimum_paper_days: 30
  minimum_trades: 50
  required_metrics:
    sharpe_ratio_min: 1.0
    max_drawdown_max: 0.10      # Max 10% drawdown
    win_rate_min: 0.45
    profit_factor_min: 1.2      # Gross profits / gross losses
    avg_hold_duration_min_hours: 1.0  # Not scalping
    avg_hold_duration_max_hours: 168  # Not holding forever (1 week)
  human_review: required        # Cannot be set to "auto"

live_trading:
  enabled: false                # Changed ONLY after graduation + human approval
  position_limits:
    max_position_pct: 0.01      # Tighter than paper (1% vs 2%)
    max_portfolio_exposure: 0.15 # Tighter than paper (15% vs 30%)
    max_single_trade_usd: 200   # Tighter than paper ($200 vs $500)
  circuit_breakers:
    daily_loss_pct: 0.03        # 3% (tighter than paper's 5%)
    weekly_loss_pct: 0.05       # 5% weekly loss halts all trading
    consecutive_losses: 5
```

Graduation report structure:

```json
{
  "report_id": "graduation-20260415",
  "generated_at": "2026-04-15T21:00:00Z",
  "paper_trading_days": 35,
  "total_trades": 67,
  "criteria_results": {
    "minimum_paper_days": {"required": 30, "actual": 35, "passed": true},
    "minimum_trades": {"required": 50, "actual": 67, "passed": true},
    "sharpe_ratio": {"required": 1.0, "actual": 1.34, "passed": true},
    "max_drawdown": {"required": 0.10, "actual": 0.067, "passed": true},
    "win_rate": {"required": 0.45, "actual": 0.52, "passed": true},
    "profit_factor": {"required": 1.2, "actual": 1.45, "passed": true}
  },
  "all_criteria_passed": true,
  "human_approval": "pending",
  "recommendation": "All metrics meet graduation criteria. Ready for human review."
}
```

Acceptance Criteria:
- [ ] Graduation check produces a structured report with pass/fail per criterion
- [ ] All criteria must pass before human review is triggered
- [ ] `human_review: required` cannot be overridden to "auto" via environment variables
- [ ] Live trading config has strictly tighter limits than paper trading config
- [ ] Changing `live_trading.enabled` from `false` to `true` requires editing `config/trading_agent.yaml` (not an env var)
- [ ] Graduation report is stored in `.self-improvement/reports/trading/` for audit trail

---

### Data Structures

Full trade lifecycle event (published to `holus.trading.signals`):

```json
{
  "source_agent": "trading-agent",
  "event_type": "trade_executed",
  "timestamp": "2026-03-15T14:30:00Z",
  "payload": {
    "trade_id": "T-20260315-001",
    "symbol": "AAPL",
    "direction": "long",
    "quantity": 10,
    "entry_price": 185.50,
    "stop_loss": 182.00,
    "take_profit": 192.00,
    "risk_score": 0.45,
    "signal_confidence": 0.78,
    "signal_sources": ["technical_rsi", "sentiment_positive"],
    "guardrail_checks_passed": 7,
    "order_id": "alpaca-order-abc123",
    "execution_mode": "paper"
  },
  "correlation_id": "signal-20260315-001"
}
```

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/agents/trading/__init__.py` | New | Trading agent module init |
| `src/holus/agents/trading/agent.py` | New | TradingAgent(BaseAgent) with LangGraph state machine |
| `src/holus/agents/trading/signal_generator.py` | New | Signal generation logic |
| `src/holus/agents/trading/risk_manager.py` | New | Risk validation with guardrails |
| `src/holus/agents/trading/execution_handler.py` | New | Alpaca API execution (ONLY file with broker access) |
| `src/holus/agents/trading/memory.py` | New | TradeMemory L1/L2/L3 protocol |
| `src/holus/agents/trading/workflows.py` | New | Temporal.io workflow definitions |
| `src/holus/agents/trading/graduation.py` | New | Paper-to-live graduation checker |
| `src/holus/integrations/alpaca/__init__.py` | New | Alpaca module init |
| `src/holus/integrations/alpaca/client.py` | New | Alpaca Trading API wrapper |
| `src/holus/integrations/alpaca/data.py` | New | Market data client (bars, quotes) |
| `src/holus/integrations/alpaca/models.py` | New | Alpaca-specific Pydantic models |
| `src/holus/integrations/finbert/__init__.py` | New | FinBERT module init |
| `src/holus/integrations/finbert/sentiment.py` | New | FinBERT local sentiment analysis |
| `config/trading_agent.yaml` | Modified | Add guardrails and graduation criteria |
| `tests/unit/agents/test_trading.py` | New | Signal, risk, execution unit tests |
| `tests/unit/agents/test_trade_memory.py` | New | Memory protocol unit tests |
| `tests/integration/test_alpaca_paper.py` | New | Paper trading integration test |

---

### Edge Cases & Error Handling

**EDGE-001: SignalGenerator hallucinates a trade signal for a non-existent symbol**
- Scenario: Claude generates a signal for a symbol that does not exist on Alpaca
- Expected behavior: RiskManager's symbol whitelist check catches it. If no whitelist, ExecutionHandler's Alpaca API call returns an error.
- Error message: `WARN: Signal rejected: symbol {symbol} not found on Alpaca. Source: {signal_id}`
- Recovery: Signal is logged and discarded. No trade executed.

**EDGE-002: Alpaca API outage during open position**
- Scenario: API becomes unreachable while the agent has open positions
- Expected behavior: Temporal.io workflow pauses at the execution checkpoint. Agent publishes `holus.system.alerts` event. Retries every 60 seconds for up to 1 hour. Alerts founder via Slack after 3 failed retries.
- Error message: `CRITICAL: Alpaca API unreachable. Open positions exist. Retrying. Alert sent to founder.`
- Recovery: Temporal replays from last checkpoint when API returns. Founder can manually manage positions via Alpaca dashboard.

**EDGE-003: Daily loss circuit breaker fires mid-trading-session**
- Scenario: Cumulative daily losses exceed `daily_loss_limit_pct` (5% default)
- Expected behavior: Kill switch activates for trading agent. All pending signals are discarded. Open positions are NOT force-closed (to avoid selling at the worst moment). Founder is alerted.
- Error message: `CRITICAL: Daily loss limit triggered ({daily_pnl_pct}% exceeds {limit}%). Trading halted. Open positions maintained.`
- Recovery: Founder reviews positions manually. Kill switch must be manually deactivated for the next trading day.

**EDGE-004: Human approval timeout on high-value trade**
- Scenario: A trade >$500 requires human approval but no response within 30 minutes
- Expected behavior: Signal expires. Trade is not executed. Event logged with `timeout` reason.
- Error message: `INFO: Signal {signal_id} expired: human approval timeout (30 min). Trade not executed.`
- Recovery: If the trade opportunity is still valid, the SignalGenerator will produce a new signal on the next scheduled run.

**EDGE-005: FinBERT gives confidently wrong sentiment on novel financial terminology**
- Scenario: FinBERT misinterprets a headline (e.g., "Apple stock crushes expectations" classified as negative due to "crushes")
- Expected behavior: FinBERT is one input among many; it is never the sole trade trigger. The Claude-based SignalGenerator synthesizes FinBERT output with technical indicators and memory patterns.
- Error message: None (FinBERT result is logged but no special handling)
- Recovery: L2 memory will eventually capture that FinBERT sentiment disagreed with actual outcomes for certain headline patterns.

**EDGE-006: Graduation criteria pass but human rejects**
- Scenario: All metrics meet thresholds but founder identifies a qualitative concern (e.g., all wins are tiny, all losses are large)
- Expected behavior: Graduation is rejected. Paper trading continues. Founder's rejection reason is stored in the graduation report.
- Error message: `INFO: Graduation rejected by human review. Reason: {reason}. Continuing paper trading.`
- Recovery: Address the qualitative concern (likely by adjusting guardrails or signal generation prompts), then re-run graduation check after more paper trading days.

**EDGE-007: Redis unavailable -- kill switch cannot be checked**
- Scenario: Redis crashes and the trading agent cannot check the kill switch
- Expected behavior: If kill switch check fails (connection error), the agent treats it as ACTIVE (fail-safe). Agent halts all activity until Redis is back.
- Error message: `CRITICAL: Cannot reach Redis for kill switch check. Treating as ACTIVE (fail-safe). Agent halted.`
- Recovery: Restart Redis (`docker compose restart redis`). Agent automatically resumes.

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Signal generation (end-to-end) | < 30s | Langfuse trace: data fetch + FinBERT + Claude reasoning |
| Risk validation | < 10s | Langfuse trace: portfolio state + Opus reasoning |
| Order execution | < 2s | Alpaca API response time |
| Kill switch check | < 1ms | Redis `EXISTS` latency |
| FinBERT sentiment (single headline) | < 100ms | Local inference latency |
| FinBERT sentiment (batch of 20) | < 2s | Local batch inference |
| L2 pattern extraction (weekly) | < 5 min | Opus reasoning over 30 days of L1 data |
| L3 principle refinement (monthly) | < 10 min | Opus synthesis of all L2 patterns |

---

### Security Considerations

- `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are the highest-risk secrets. Only `ExecutionHandler` has access.
- Paper trading uses a separate Alpaca endpoint (`paper-api.alpaca.markets`). Live trading requires config change.
- All trade data passes through Anthropic API for reasoning. Covered by Anthropic's enterprise API privacy guarantees.
- Financial audit trail: all trades logged to append-only JSONL in `.self-improvement/audit/financial_YYYY-MM.jsonl`
- Kill switch is intentionally fail-safe: Redis failure = agent halts.

---

### Out of Scope

- Options trading (equities only in v1)
- Crypto trading (Alpaca supports it, but out of scope for v1)
- Real-time / HFT (daily/swing timeframes only)
- Backtesting framework (separate spec)
- Tax reporting and P&L attribution (separate spec)
- Multiple broker support (Alpaca only in v1)

---

### Related Specs

- [001-core-infrastructure.md](./001-core-infrastructure.md) -- provides Redis (event bus, kill switch), Temporal (durable execution), Claude client, config management
- [003-content-pipeline.md](./003-content-pipeline.md) -- content agent may consume `market_regime_shift` events for market-related content

---

**Last Updated:** 2026-02-24
**Status:** Not Started
**Owner:** Camilo Martinez
