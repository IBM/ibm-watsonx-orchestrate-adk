"""Observability module -- framework-agnostic tracing for agent applications.

This module wraps the OpenTelemetry SDK and provides a user-friendly API
for creating spans, tracking LLM calls, tool invocations, and agent tasks.
No raw OpenTelemetry objects are exposed.  Works with any agentic platform
(LangGraph, CrewAI, AutoGen, custom frameworks, etc.).

Quick start with decorators::

    from ibm_watsonx_orchestrate_sdk.observability.decorators import (
        trace_call, trace_llm_call, trace_tool_call, trace_agent_call,
    )

    @trace_call(capture_input=True, capture_output=True, name="my_func")
    def my_func(x):
        return x * 2

Quick start with context managers::

    from ibm_watsonx_orchestrate_sdk.observability import Tracer

    tracer = Tracer()
    with tracer.start_span("my-op") as span:
        span.set_attribute("key", "value")
"""

__all__ = [
    "Tracer",
    "TracerConfig",
    "SpanWrapper",
    "LLMSpanWrapper",
    "ToolSpanWrapper",
    "AgentSpanWrapper",
    "get_default_tracer",
    "register_tracer",
    "trace_call",
    "trace_llm_call",
    "trace_tool_call",
    "trace_agent_call",
    "configure_tracing",
]

from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig
from ibm_watsonx_orchestrate_sdk.observability.decorators import (
    trace_agent_call,
    trace_call,
    trace_llm_call,
    trace_tool_call,
    configure_tracing,
)
from ibm_watsonx_orchestrate_sdk.observability.spans import (
    AgentSpanWrapper,
    LLMSpanWrapper,
    SpanWrapper,
    ToolSpanWrapper,
)
from ibm_watsonx_orchestrate_sdk.observability.tracer import (
    Tracer,
    get_default_tracer,
    register_tracer,
)
