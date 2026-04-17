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
from typing import Any, Dict, Optional

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

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider as _TracerProvider
from opentelemetry.trace import Tracer as _OtelTracer

logger = logging.getLogger(__name__)

_BAGGAGE_KEYS = (BAGGAGE_TENANT_ID, BAGGAGE_AGENT_ID)


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
        from opentelemetry import context
        return context.get_current()

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
