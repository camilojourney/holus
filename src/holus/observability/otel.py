"""OpenTelemetry instrumentation for Holus agents.

Provides trace context propagation and metric recording.
Traces are sent to the OTEL Collector (localhost:4317) which exports
metrics to Prometheus. Langfuse handles LLM-specific tracing separately.

Usage:
    from holus.observability.otel import get_tracer, record_llm_metrics

    tracer = get_tracer("marketing-agent")
    with tracer.start_as_current_span("observe") as span:
        span.set_attribute("gen_ai.agent.id", "marketing-strategist")
        ...

    record_llm_metrics(
        agent_id="marketing-strategist",
        model="claude-sonnet-4-6",
        tokens_input=1200,
        tokens_output=450,
        cost_usd=0.012,
        duration_sec=3.4,
    )
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_tracer_provider = None
_meter_provider = None


def _init_otel() -> None:
    """Initialize OTEL tracer and meter providers (lazy, once)."""
    global _tracer_provider, _meter_provider

    if _tracer_provider is not None:
        return

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    service_name = os.environ.get("OTEL_SERVICE_NAME", "holus")

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service_name})

        # Traces
        _tracer_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(_tracer_provider)

        # Metrics
        metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
        reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
        _meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(_meter_provider)

        logger.info("OTEL initialized: endpoint=%s, service=%s", endpoint, service_name)

    except ImportError:
        logger.info("OTEL packages not installed — tracing disabled")
    except Exception:
        logger.warning("OTEL init failed — tracing disabled", exc_info=True)


def get_tracer(name: str = "holus") -> Any:
    """Get an OTEL tracer. Returns a no-op tracer if OTEL is unavailable."""
    _init_otel()
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return _NoOpTracer()


def get_meter(name: str = "holus") -> Any:
    """Get an OTEL meter. Returns a no-op meter if OTEL is unavailable."""
    _init_otel()
    try:
        from opentelemetry import metrics
        return metrics.get_meter(name)
    except ImportError:
        return _NoOpMeter()


# Pre-created instruments for common metrics
_llm_cost_counter = None
_llm_token_counter = None
_llm_duration_histogram = None
_eval_score_gauge = None


def _ensure_instruments() -> None:
    """Lazily create metric instruments."""
    global _llm_cost_counter, _llm_token_counter, _llm_duration_histogram, _eval_score_gauge

    if _llm_cost_counter is not None:
        return

    meter = get_meter("holus.llm")
    _llm_cost_counter = meter.create_counter(
        "holus.llm.cost_usd",
        unit="USD",
        description="Cumulative LLM API cost",
    )
    _llm_token_counter = meter.create_counter(
        "holus.llm.tokens",
        unit="tokens",
        description="Cumulative token usage",
    )
    _llm_duration_histogram = meter.create_histogram(
        "holus.llm.duration",
        unit="s",
        description="LLM call duration",
    )
    _eval_score_gauge = meter.create_histogram(
        "holus.eval.score",
        unit="points",
        description="Eval gate scores",
    )


def record_llm_metrics(
    *,
    agent_id: str,
    model: str,
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_usd: float = 0.0,
    duration_sec: float = 0.0,
) -> None:
    """Record LLM call metrics to OTEL."""
    _ensure_instruments()
    if _llm_cost_counter is None:
        return

    attrs: dict[str, Any] = {"agent.id": agent_id, "model": model}
    _llm_cost_counter.add(cost_usd, attributes=attrs)
    _llm_token_counter.add(tokens_input, attributes={**attrs, "direction": "input"})  # type: ignore[union-attr]
    _llm_token_counter.add(tokens_output, attributes={**attrs, "direction": "output"})  # type: ignore[union-attr]
    _llm_duration_histogram.record(duration_sec, attributes=attrs)  # type: ignore[union-attr]


def record_eval_score(
    *,
    skill: str,
    repo: str,
    score: float,
) -> None:
    """Record an eval gate score to OTEL."""
    _ensure_instruments()
    if _eval_score_gauge is None:
        return
    _eval_score_gauge.record(score, attributes={"skill": skill, "repo": repo})


def propagate_context_env() -> dict[str, str]:
    """Serialize current trace context to env vars for subprocess propagation.

    Returns a dict with TRACEPARENT (and optionally TRACESTATE) that can be
    passed as env vars to Codex/Gemini CLI subprocesses.
    """
    try:
        from opentelemetry import context
        from opentelemetry.trace.propagation.tracecontext import (
            TraceContextTextMapPropagator,
        )

        carrier: dict[str, str] = {}
        TraceContextTextMapPropagator().inject(carrier, context.get_current())
        return carrier
    except ImportError:
        return {}


# -- No-op fallbacks for when OTEL is not installed --------------------------


class _NoOpSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class _NoOpTracer:
    def start_as_current_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()


class _NoOpCounter:
    def add(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpHistogram:
    def record(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpMeter:
    def create_counter(self, name: str, **kwargs: Any) -> _NoOpCounter:
        return _NoOpCounter()

    def create_histogram(self, name: str, **kwargs: Any) -> _NoOpHistogram:
        return _NoOpHistogram()
