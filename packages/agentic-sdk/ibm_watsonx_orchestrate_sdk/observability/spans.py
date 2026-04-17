"""Span wrappers that hide raw OpenTelemetry Span objects.

Four wrapper levels are provided:

* ``SpanWrapper``       -- general-purpose span context manager.
* ``LLMSpanWrapper``    -- adds helpers for recording token usage.
* ``ToolSpanWrapper``   -- adds helpers for recording tool results.
* ``AgentSpanWrapper``  -- adds helpers for recording agent task results.

All wrappers are framework-agnostic and work with any agentic platform.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, TYPE_CHECKING

from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    ATTR_AGENT_FRAMEWORK,
    ATTR_AGENT_NAME,
    ATTR_AGENT_OUTPUT,
    ATTR_LLM_COMPLETION_TOKENS,
    ATTR_LLM_MODEL,
    ATTR_LLM_PROMPT_TOKENS,
    ATTR_LLM_PROVIDER,
    ATTR_LLM_RESPONSE_MODEL,
    ATTR_LLM_STOP_REASON,
    ATTR_LLM_TOTAL_TOKENS,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTPUT,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span, StatusCode


def _safe_json(obj: Any) -> str:
    """Best-effort JSON serialisation; falls back to ``str()``."""
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)


class SpanWrapper:
    """User-facing wrapper around an OpenTelemetry ``Span``.

    Used as a context manager so the span is automatically ended on exit.
    Exceptions are recorded and the status is set to ``ERROR`` when they
    propagate out of the ``with`` block.
    """

    def __init__(self, span: "Span") -> None:
        self._span = span

    # --- context manager protocol ---

    def __enter__(self) -> "SpanWrapper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        if exc_val is not None:
            self._span.set_status(_error_status(str(exc_val)))
            self._span.record_exception(exc_val)
        self._span.end()
        return None

    # --- public helpers ---

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a single attribute on the underlying span."""
        self._span.set_attribute(key, value)

    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set multiple attributes at once."""
        for k, v in attributes.items():
            self._span.set_attribute(k, v)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Record a timestamped event on the span."""
        self._span.add_event(name, attributes=attributes)

    def set_status_ok(self) -> None:
        """Mark the span as successful."""
        self._span.set_status(_ok_status())

    def set_status_error(self, description: str = "") -> None:
        """Mark the span as failed."""
        self._span.set_status(_error_status(description))


class LLMSpanWrapper(SpanWrapper):
    """Span wrapper with convenience methods for LLM call tracking."""

    def __init__(
        self,
        span: "Span",
        *,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> None:
        super().__init__(span)
        if model:
            self._span.set_attribute(ATTR_LLM_MODEL, model)
        if provider:
            self._span.set_attribute(ATTR_LLM_PROVIDER, provider)

    def record_completion(
        self,
        *,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        response_model: Optional[str] = None,
        stop_reason: Optional[str] = None,
    ) -> None:
        """Record token usage and optional response metadata.

        If *total_tokens* is not provided it is computed from
        *prompt_tokens* + *completion_tokens* when both are given.
        """
        if prompt_tokens is not None:
            self._span.set_attribute(ATTR_LLM_PROMPT_TOKENS, prompt_tokens)
        if completion_tokens is not None:
            self._span.set_attribute(ATTR_LLM_COMPLETION_TOKENS, completion_tokens)

        if total_tokens is not None:
            self._span.set_attribute(ATTR_LLM_TOTAL_TOKENS, total_tokens)
        elif prompt_tokens is not None and completion_tokens is not None:
            self._span.set_attribute(ATTR_LLM_TOTAL_TOKENS, prompt_tokens + completion_tokens)

        if response_model:
            self._span.set_attribute(ATTR_LLM_RESPONSE_MODEL, response_model)
        if stop_reason:
            self._span.set_attribute(ATTR_LLM_STOP_REASON, stop_reason)


class ToolSpanWrapper(SpanWrapper):
    """Span wrapper with convenience methods for tool call tracking."""

    def __init__(
        self,
        span: "Span",
        *,
        tool_name: Optional[str] = None,
        tool_input: Any = None,
    ) -> None:
        super().__init__(span)
        if tool_name:
            self._span.set_attribute(ATTR_TOOL_NAME, tool_name)
        if tool_input is not None:
            self._span.set_attribute(ATTR_TOOL_INPUT, _safe_json(tool_input))

    def record_result(self, output: Any) -> None:
        """Record the tool invocation result."""
        self._span.set_attribute(ATTR_TOOL_OUTPUT, _safe_json(output))


class AgentSpanWrapper(SpanWrapper):
    """Span wrapper with convenience methods for agent task tracking."""

    def __init__(
        self,
        span: "Span",
        *,
        agent_name: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> None:
        super().__init__(span)
        if agent_name:
            self._span.set_attribute(ATTR_AGENT_NAME, agent_name)
        if framework:
            self._span.set_attribute(ATTR_AGENT_FRAMEWORK, framework)

    def record_result(self, output: Any) -> None:
        """Record the agent task result."""
        self._span.set_attribute(ATTR_AGENT_OUTPUT, _safe_json(output))


# ---------------------------------------------------------------------------
# Internal helpers (avoid importing StatusCode at module level)
# ---------------------------------------------------------------------------

def _ok_status() -> "StatusCode":
    from opentelemetry.trace import StatusCode, Status
    return Status(StatusCode.OK)


def _error_status(description: str = "") -> "StatusCode":
    from opentelemetry.trace import StatusCode, Status
    return Status(StatusCode.ERROR, description)
