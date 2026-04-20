"""Framework-agnostic tracing decorators.

Apply these decorators to any function to automatically create
OpenTelemetry spans.  A default :class:`Tracer` (configured via
environment variables) is used so no explicit tracer instantiation is
required.

Usage::

    from ibm_watsonx_orchestrate_sdk.observability.decorators import (
        trace_call, trace_llm_call, trace_tool_call, trace_agent_call,
        configure_tracing,
    )

    @trace_call(capture_input=True, capture_output=True, name="my_function")
    def my_function(arg1, arg2):
        return result

    @trace_llm_call(capture_input=True, capture_output=True)
    def call_model(prompt, model="gpt-4"):
        return response

    @trace_tool_call(capture_input=True, capture_output=True)
    def search(query):
        return results

    @trace_agent_call(capture_input=True, capture_output=True)
    def run_agent(task, context):
        return result
"""

from __future__ import annotations

import functools
import inspect
import json
from typing import Any, Callable, Dict, Optional

from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    ATTR_INPUT,
    ATTR_OUTPUT,
)


def _safe_json(obj: Any) -> str:
    """Best-effort JSON serialisation; falls back to ``str()``."""
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)


def _capture_args(fn: Callable, args: tuple, kwargs: dict) -> str:
    """Serialise the function arguments into a JSON string."""
    sig = inspect.signature(fn)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    return _safe_json(dict(bound.arguments))


# -----------------------------------------------------------------------
# trace_call  --  general-purpose function tracing
# -----------------------------------------------------------------------

def trace_call(
    name: Optional[str] = None,
    *,
    capture_input: bool = False,
    capture_output: bool = False,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator that wraps a function in a general-purpose span.

    Args:
        name: Span name.  Defaults to the function's qualified name.
        capture_input: When ``True`` the function arguments are recorded
            as the ``input.value`` span attribute.
        capture_output: When ``True`` the return value is recorded as
            the ``output.value`` span attribute.
        attributes: Optional extra span attributes.
    """

    def decorator(fn: Callable) -> Callable:
        span_name = name or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from ibm_watsonx_orchestrate_sdk.observability.tracer import get_default_tracer

            tracer = get_default_tracer()
            with tracer.start_span(span_name, attributes=attributes) as span:
                if capture_input:
                    span.set_attribute(ATTR_INPUT, _capture_args(fn, args, kwargs))
                result = fn(*args, **kwargs)
                if capture_output:
                    span.set_attribute(ATTR_OUTPUT, _safe_json(result))
                return result

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            from ibm_watsonx_orchestrate_sdk.observability.tracer import get_default_tracer

            tracer = get_default_tracer()
            with tracer.start_span(span_name, attributes=attributes) as span:
                if capture_input:
                    span.set_attribute(ATTR_INPUT, _capture_args(fn, args, kwargs))
                result = await fn(*args, **kwargs)
                if capture_output:
                    span.set_attribute(ATTR_OUTPUT, _safe_json(result))
                return result

        return async_wrapper if inspect.iscoroutinefunction(fn) else wrapper

    return decorator


# -----------------------------------------------------------------------
# trace_llm_call  --  LLM invocation tracing
# -----------------------------------------------------------------------

def trace_llm_call(
    name: Optional[str] = None,
    *,
    capture_input: bool = False,
    capture_output: bool = False,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator that wraps a function in an LLM span.

    Args:
        name: Span name.  Defaults to the function's qualified name.
        capture_input: Record function arguments as ``input.value``.
        capture_output: Record the return value as ``output.value``.
        model: LLM model identifier (e.g. ``"gpt-4"``).
        provider: LLM provider (e.g. ``"openai"``).
        attributes: Optional extra span attributes.
    """

    def decorator(fn: Callable) -> Callable:
        span_name = name or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from ibm_watsonx_orchestrate_sdk.observability.tracer import get_default_tracer

            tracer = get_default_tracer()
            with tracer.start_llm_span(
                span_name, model=model, provider=provider, attributes=attributes
            ) as span:
                if capture_input:
                    span.set_attribute(ATTR_INPUT, _capture_args(fn, args, kwargs))
                result = fn(*args, **kwargs)
                if capture_output:
                    span.set_attribute(ATTR_OUTPUT, _safe_json(result))
                return result

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            from ibm_watsonx_orchestrate_sdk.observability.tracer import get_default_tracer

            tracer = get_default_tracer()
            with tracer.start_llm_span(
                span_name, model=model, provider=provider, attributes=attributes
            ) as span:
                if capture_input:
                    span.set_attribute(ATTR_INPUT, _capture_args(fn, args, kwargs))
                result = await fn(*args, **kwargs)
                if capture_output:
                    span.set_attribute(ATTR_OUTPUT, _safe_json(result))
                return result

        return async_wrapper if inspect.iscoroutinefunction(fn) else wrapper

    return decorator


# -----------------------------------------------------------------------
# trace_tool_call  --  tool invocation tracing
# -----------------------------------------------------------------------

def trace_tool_call(
    name: Optional[str] = None,
    *,
    capture_input: bool = False,
    capture_output: bool = False,
    tool_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator that wraps a function in a tool span.

    Args:
        name: Span name.  Defaults to the function's qualified name.
        capture_input: Record function arguments as ``input.value``.
        capture_output: Record the return value as ``output.value``.
        tool_name: Logical tool name.  Defaults to ``fn.__name__``.
        attributes: Optional extra span attributes.
    """

    def decorator(fn: Callable) -> Callable:
        span_name = name or fn.__qualname__
        resolved_tool_name = tool_name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from ibm_watsonx_orchestrate_sdk.observability.tracer import get_default_tracer

            tracer = get_default_tracer()
            with tracer.start_tool_span(
                span_name,
                tool_name=resolved_tool_name,
                attributes=attributes,
            ) as span:
                if capture_input:
                    span.set_attribute(ATTR_INPUT, _capture_args(fn, args, kwargs))
                result = fn(*args, **kwargs)
                if capture_output:
                    span.set_attribute(ATTR_OUTPUT, _safe_json(result))
                return result

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            from ibm_watsonx_orchestrate_sdk.observability.tracer import get_default_tracer

            tracer = get_default_tracer()
            with tracer.start_tool_span(
                span_name,
                tool_name=resolved_tool_name,
                attributes=attributes,
            ) as span:
                if capture_input:
                    span.set_attribute(ATTR_INPUT, _capture_args(fn, args, kwargs))
                result = await fn(*args, **kwargs)
                if capture_output:
                    span.set_attribute(ATTR_OUTPUT, _safe_json(result))
                return result

        return async_wrapper if inspect.iscoroutinefunction(fn) else wrapper

    return decorator


# -----------------------------------------------------------------------
# trace_agent_call  --  agent task tracing
# -----------------------------------------------------------------------

def trace_agent_call(
    name: Optional[str] = None,
    *,
    capture_input: bool = False,
    capture_output: bool = False,
    agent_name: Optional[str] = None,
    framework: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator that wraps a function in an agent span.

    Args:
        name: Span name.  Defaults to the function's qualified name.
        capture_input: Record function arguments as ``input.value``.
        capture_output: Record the return value as ``output.value``.
        agent_name: Logical agent name.  Defaults to ``fn.__name__``.
        framework: Agent framework identifier (e.g. ``"langgraph"``,
            ``"crewai"``, ``"autogen"``).
        attributes: Optional extra span attributes.
    """

    def decorator(fn: Callable) -> Callable:
        span_name = name or fn.__qualname__
        resolved_agent_name = agent_name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from ibm_watsonx_orchestrate_sdk.observability.tracer import get_default_tracer

            tracer = get_default_tracer()
            with tracer.start_agent_span(
                span_name,
                agent_name=resolved_agent_name,
                framework=framework,
                attributes=attributes,
            ) as span:
                if capture_input:
                    span.set_attribute(ATTR_INPUT, _capture_args(fn, args, kwargs))
                result = fn(*args, **kwargs)
                if capture_output:
                    span.set_attribute(ATTR_OUTPUT, _safe_json(result))
                return result

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            from ibm_watsonx_orchestrate_sdk.observability.tracer import get_default_tracer

            tracer = get_default_tracer()
            with tracer.start_agent_span(
                span_name,
                agent_name=resolved_agent_name,
                framework=framework,
                attributes=attributes,
            ) as span:
                if capture_input:
                    span.set_attribute(ATTR_INPUT, _capture_args(fn, args, kwargs))
                result = await fn(*args, **kwargs)
                if capture_output:
                    span.set_attribute(ATTR_OUTPUT, _safe_json(result))
                return result

        return async_wrapper if inspect.iscoroutinefunction(fn) else wrapper

    return decorator


# -----------------------------------------------------------------------
# configure_tracing  --  top-level create_agent hook
# -----------------------------------------------------------------------

def configure_tracing(fn: Callable) -> Callable:
    """Decorator for LangGraph ``create_agent`` factory functions.
    """

    @functools.wraps(fn)
    def wrapper(config: Any, *args: Any, **kwargs: Any) -> Any:
        from ibm_watsonx_orchestrate_sdk.observability.tracer import _build_invocation_context
        from opentelemetry import context as otel_context

        ec = (config or {}).get("configurable", {}).get("execution_context") or {}
        token = None
        if ec:
            ctx = _build_invocation_context(ec)
            if ctx is not None:
                token = otel_context.attach(ctx)

        try:
            return fn(config, *args, **kwargs)
        finally:
            if token is not None:
                otel_context.detach(token)

    return wrapper
