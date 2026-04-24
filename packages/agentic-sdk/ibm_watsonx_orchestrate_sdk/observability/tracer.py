"""Main Tracer class -- the primary entry point for the observability module.

Wraps an OpenTelemetry ``TracerProvider`` and exposes a user-friendly,
framework-agnostic API for creating spans without leaking raw OTEL objects.

A module-level default tracer is lazily created so that standalone
decorators (``trace_call``, ``trace_llm_call``, etc.) work without the
user having to instantiate a ``Tracer`` explicitly.
"""

from __future__ import annotations

import logging
import threading
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Dict, Optional

from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    ATTR_AGENT_NAME,
    ATTR_LLM_MODEL,
    ATTR_LLM_PROVIDER,
    ATTR_SERVICE_NAME,
    ATTR_TOOL_NAME,
    BAGGAGE_AGENT_ID,
    BAGGAGE_TENANT_ID,
    SPAN_KIND_AGENT,
    SPAN_KIND_GENERAL,
    SPAN_KIND_LLM,
    SPAN_KIND_TOOL,
)
from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig
from ibm_watsonx_orchestrate_sdk.observability.exporters import create_exporter
from ibm_watsonx_orchestrate_sdk.observability.spans import (
    AgentSpanWrapper,
    LLMSpanWrapper,
    SpanWrapper,
    ToolSpanWrapper,
)

if TYPE_CHECKING:
    from opentelemetry.context import Context
    from opentelemetry.sdk.trace import ReadableSpan, TracerProvider as _TracerProvider
    from opentelemetry.trace import Tracer as _OtelTracer

logger = logging.getLogger(__name__)

_BAGGAGE_KEYS = (BAGGAGE_TENANT_ID, BAGGAGE_AGENT_ID)

# ---------------------------------------------------------------------------
# Request-scoped execution context (trace_id, span_id, tenant_id, agent_id)
# ---------------------------------------------------------------------------
_execution_context_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "wxo_execution_context", default=None,
)


def store_execution_context(ec: Dict[str, Any]) -> None:
    """Store the execution context for the current async/thread scope.

    Called by ``@configure_tracing`` so that all subsequent span-creating
    decorators in the same request automatically inherit the parent trace.
    """
    _execution_context_var.set(ec)
    logger.debug("Stored execution context: trace_id=%s", ec.get("trace_id"))


class BaggageSpanProcessor:
    """SpanProcessor that copies Baggage entries to span attributes.

    On every ``on_start`` it reads ``tenant.id`` and ``agent.id`` from
    the current OpenTelemetry Baggage context and sets them as span
    attributes so they are exported with each span.

    Implements the full ``SpanProcessor`` protocol without inheriting
    from the SDK class so that the import stays lazy.
    """

    def on_start(self, span: "ReadableSpan", parent_context: "Optional[Context]" = None) -> None:
        from opentelemetry import baggage, context

        ctx = parent_context or context.get_current()
        for key in _BAGGAGE_KEYS:
            value = baggage.get_baggage(key, ctx)
            if value is not None:
                span.set_attribute(key, value)

    def on_end(self, span: "ReadableSpan") -> None:
        pass

    def _on_ending(self, span: "ReadableSpan") -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


# ---------------------------------------------------------------------------
# Default (singleton) tracer
# ---------------------------------------------------------------------------
_default_tracer: Optional[Tracer] = None
_default_lock = threading.Lock()


def get_default_tracer() -> "Tracer":
    """Return the module-level default ``Tracer``, creating it on first call.

    The default tracer uses zero-config ``TracerConfig`` (reads all
    settings from environment variables).
    """
    global _default_tracer
    if _default_tracer is None:
        with _default_lock:
            if _default_tracer is None:
                _default_tracer = Tracer()
    return _default_tracer


def register_tracer(tracer: "Tracer") -> None:
    """Set the module-level default tracer used by all decorators and ``get_default_tracer()``.

    Call this once at startup after constructing your ``Tracer`` so that
    ``@trace_call``, ``@trace_agent_call``, and the other decorators use
    your configured instance instead of creating a zero-config default.

    Example::

        tracer = Tracer(TracerConfig(service_name="my-agent"))
        register_tracer(tracer)
    """
    global _default_tracer
    with _default_lock:
        _default_tracer = tracer
    logger.info("Default tracer registered [service=%s]", tracer._config.service_name)


def _build_invocation_context(execution_context: Dict[str, Any]) -> Optional["Context"]:
    """Build an OTel Context from the WXO execution_context."""
    from opentelemetry import baggage, context, trace
    from opentelemetry.trace import SpanContext, TraceFlags, NonRecordingSpan

    ctx = context.get_current()

    # --- Propagate parent trace context (trace_id + span_id) ---
    raw_trace_id = execution_context.get("trace_id")
    raw_span_id = execution_context.get("span_id")
    if raw_trace_id and raw_span_id:
        try:
            parent_span_context = SpanContext(
                trace_id=int(raw_trace_id, 16),
                span_id=int(raw_span_id, 16),
                is_remote=True,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            )
            parent_span = NonRecordingSpan(parent_span_context)
            ctx = trace.set_span_in_context(parent_span, ctx)
        except (ValueError, TypeError):
            logger.warning("Invalid trace_id/span_id in execution_context, ignoring")

    # --- Set baggage for metadata propagation ---
    baggage_mapping = {
        BAGGAGE_TENANT_ID: execution_context.get("tenant_id"),
        BAGGAGE_AGENT_ID: execution_context.get("agent_id"),
    }

    any_set = False
    for key, value in baggage_mapping.items():
        if value:
            ctx = baggage.set_baggage(key, str(value), context=ctx)
            any_set = True

    # Return ctx if we set a parent span OR any baggage
    if raw_trace_id and raw_span_id:
        return ctx
    return ctx if any_set else None


class Tracer:
    """High-level, user-facing tracer that hides the OpenTelemetry SDK.

    Example -- zero-config usage (endpoint & attributes from env vars)::

        from ibm_watsonx_orchestrate_sdk.observability import Tracer

        tracer = Tracer()

        with tracer.start_span("my-operation") as span:
            span.set_attribute("key", "value")
    """

    def __init__(self, config: Optional[TracerConfig] = None) -> None:
        self._config = config or TracerConfig()
        self._provider: _TracerProvider = self._build_provider()
        self._tracer: _OtelTracer = self._provider.get_tracer(
            self._config.service_name
        )

    # ------------------------------------------------------------------
    # Provider bootstrap
    # ------------------------------------------------------------------

    def _build_provider(self) -> "_TracerProvider":
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource_attrs = {ATTR_SERVICE_NAME: self._config.service_name}
        resource_attrs.update(self._config.build_resource_attributes())

        resource = Resource.create(resource_attrs)
        provider = TracerProvider(resource=resource)

        provider.add_span_processor(BaggageSpanProcessor())

        exporter = create_exporter(self._config)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        return provider

    # ------------------------------------------------------------------
    # Span creation -- context-manager based
    # ------------------------------------------------------------------

    @staticmethod
    def _current_context():
        from opentelemetry import context, trace

        ctx = context.get_current()

        current_span = trace.get_current_span(ctx)
        if current_span.get_span_context().is_valid:
            return ctx
            
        ec = _execution_context_var.get()
        if ec is not None:
            built = _build_invocation_context(ec)
            if built is not None:
                return built

        return ctx

    def start_span(
        self,
        name: str,
        *,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> SpanWrapper:
        """Start a general-purpose span (use as a context manager).

        ::

            with tracer.start_span("step", attributes={"k": "v"}) as span:
                ...
        """
        merged: Dict[str, Any] = {"span.kind": SPAN_KIND_GENERAL}
        if attributes:
            merged.update(attributes)
        
        otel_span = self._tracer.start_span(name, context=self._current_context(), attributes=merged)
        return SpanWrapper(otel_span)

    def start_llm_span(
        self,
        name: str = "llm_call",
        *,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> LLMSpanWrapper:
        """Start a span pre-configured for LLM call tracking.

        Token usage can be recorded via
        :pymeth:`LLMSpanWrapper.record_completion`.
        """
        merged: Dict[str, Any] = {"span.kind": SPAN_KIND_LLM}
        if model:
            merged[ATTR_LLM_MODEL] = model
        if provider:
            merged[ATTR_LLM_PROVIDER] = provider
        if attributes:
            merged.update(attributes)
        
        otel_span = self._tracer.start_span(name, context=self._current_context(), attributes=merged)
        return LLMSpanWrapper(otel_span, model=model, provider=provider)

    def start_tool_span(
        self,
        name: str = "tool_call",
        *,
        tool_name: Optional[str] = None,
        tool_input: Any = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> ToolSpanWrapper:
        """Start a span pre-configured for tool invocation tracking."""
        merged: Dict[str, Any] = {"span.kind": SPAN_KIND_TOOL}
        if tool_name:
            merged[ATTR_TOOL_NAME] = tool_name
        if attributes:
            merged.update(attributes)

        otel_span = self._tracer.start_span(name, context=self._current_context(), attributes=merged)
        return ToolSpanWrapper(otel_span, tool_name=tool_name, tool_input=tool_input)

    def start_agent_span(
        self,
        name: str = "agent_call",
        *,
        agent_name: Optional[str] = None,
        framework: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> AgentSpanWrapper:
        """Start a span pre-configured for agent task tracking."""
        merged: Dict[str, Any] = {"span.kind": SPAN_KIND_AGENT}
        if agent_name:
            merged[ATTR_AGENT_NAME] = agent_name
        if attributes:
            merged.update(attributes)

        otel_span = self._tracer.start_span(name, context=self._current_context(), attributes=merged)
        return AgentSpanWrapper(otel_span, agent_name=agent_name, framework=framework)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Flush pending spans and shut down the tracer provider."""
        self._provider.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush pending spans (useful before process exit)."""
        return self._provider.force_flush(timeout_millis)
