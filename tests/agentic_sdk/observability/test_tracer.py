"""Integration tests for Tracer, BaggageSpanProcessor, and singleton helpers."""

import threading

import pytest
from opentelemetry import baggage, context as otel_context
from unittest.mock import MagicMock

import ibm_watsonx_orchestrate_sdk.observability.tracer as tracer_module
from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    ATTR_AGENT_FRAMEWORK,
    ATTR_AGENT_NAME,
    ATTR_LLM_MODEL,
    ATTR_LLM_PROVIDER,
    ATTR_TOOL_NAME,
    BAGGAGE_AGENT_ID,
    BAGGAGE_TENANT_ID,
    SPAN_KIND_AGENT,
    SPAN_KIND_GENERAL,
    SPAN_KIND_LLM,
    SPAN_KIND_TOOL,
)
from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig
from ibm_watsonx_orchestrate_sdk.observability.tracer import (
    BaggageSpanProcessor,
    Tracer,
    get_default_tracer,
    register_tracer,
)

from .conftest import get_attrs


# ---------------------------------------------------------------------------
# Tracer initialisation
# ---------------------------------------------------------------------------


class TestTracerInit:
    def test_default_config_service_name(self, memory_tracer):
        tracer, _ = memory_tracer
        assert tracer._config.service_name == "wxo-agentic-sdk"

    def test_custom_config_service_name(self, memory_tracer, monkeypatch):
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        exp = InMemorySpanExporter()

        def fake_build(self):
            resource = Resource.create({"service.name": self._config.service_name})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(SimpleSpanProcessor(exp))
            return provider

        monkeypatch.setattr(Tracer, "_build_provider", fake_build)
        t = Tracer(TracerConfig(service_name="custom-svc"))
        assert t._config.service_name == "custom-svc"

    def test_shutdown_does_not_raise(self, memory_tracer):
        tracer, _ = memory_tracer
        tracer.shutdown()  # should not raise

    def test_force_flush_returns_true(self, memory_tracer):
        tracer, _ = memory_tracer
        assert tracer.force_flush(timeout_millis=1000) is True


# ---------------------------------------------------------------------------
# start_span
# ---------------------------------------------------------------------------


class TestStartSpan:
    def test_span_kind_general(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_span("op"):
            pass
        assert get_attrs(exporter.get_finished_spans()[0])["span.kind"] == SPAN_KIND_GENERAL

    def test_span_name(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_span("my-operation"):
            pass
        assert exporter.get_finished_spans()[0].name == "my-operation"

    def test_extra_attributes_merged(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_span("op", attributes={"custom": "value"}):
            pass
        assert get_attrs(exporter.get_finished_spans()[0])["custom"] == "value"

    def test_span_is_ended_after_context_manager(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_span("op"):
            pass
        assert len(exporter.get_finished_spans()) == 1

    def test_exception_still_ends_span(self, memory_tracer):
        tracer, exporter = memory_tracer
        with pytest.raises(ValueError):
            with tracer.start_span("op"):
                raise ValueError("bad")
        assert len(exporter.get_finished_spans()) == 1


# ---------------------------------------------------------------------------
# start_llm_span
# ---------------------------------------------------------------------------


class TestStartLLMSpan:
    def test_span_kind_llm(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_llm_span("llm-op"):
            pass
        assert get_attrs(exporter.get_finished_spans()[0])["span.kind"] == SPAN_KIND_LLM

    def test_model_and_provider_set(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_llm_span("llm-op", model="gpt-4", provider="openai"):
            pass
        attrs = get_attrs(exporter.get_finished_spans()[0])
        assert attrs[ATTR_LLM_MODEL] == "gpt-4"
        assert attrs[ATTR_LLM_PROVIDER] == "openai"

    def test_default_span_name(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_llm_span():
            pass
        assert exporter.get_finished_spans()[0].name == "llm_call"


# ---------------------------------------------------------------------------
# start_tool_span
# ---------------------------------------------------------------------------


class TestStartToolSpan:
    def test_span_kind_tool(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_tool_span("tool-op", tool_name="search"):
            pass
        assert get_attrs(exporter.get_finished_spans()[0])["span.kind"] == SPAN_KIND_TOOL

    def test_tool_name_set(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_tool_span("tool-op", tool_name="search"):
            pass
        assert get_attrs(exporter.get_finished_spans()[0])[ATTR_TOOL_NAME] == "search"

    def test_default_span_name(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_tool_span():
            pass
        assert exporter.get_finished_spans()[0].name == "tool_call"


# ---------------------------------------------------------------------------
# start_agent_span
# ---------------------------------------------------------------------------


class TestStartAgentSpan:
    def test_span_kind_agent(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_agent_span("agent-op"):
            pass
        assert get_attrs(exporter.get_finished_spans()[0])["span.kind"] == SPAN_KIND_AGENT

    def test_agent_name_and_framework(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_agent_span("agent-op", agent_name="planner", framework="langgraph"):
            pass
        attrs = get_attrs(exporter.get_finished_spans()[0])
        assert attrs[ATTR_AGENT_NAME] == "planner"
        assert attrs[ATTR_AGENT_FRAMEWORK] == "langgraph"

    def test_default_span_name(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_agent_span():
            pass
        assert exporter.get_finished_spans()[0].name == "agent_call"


# ---------------------------------------------------------------------------
# Parent–child span propagation
# ---------------------------------------------------------------------------


class TestSpanContextPropagation:
    def test_nested_spans_have_parent_child_relationship(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_span("parent"):
            with tracer.start_span("child"):
                pass

        spans = exporter.get_finished_spans()
        assert len(spans) == 2
        child = next(s for s in spans if s.name == "child")
        parent = next(s for s in spans if s.name == "parent")
        assert child.parent is not None
        assert child.parent.span_id == parent.context.span_id

    def test_sibling_spans_have_no_parent(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_span("a"):
            pass
        with tracer.start_span("b"):
            pass
        spans = exporter.get_finished_spans()
        assert len(spans) == 2
        for span in spans:
            assert span.parent is None or span.parent.is_valid is False


# ---------------------------------------------------------------------------
# BaggageSpanProcessor
# ---------------------------------------------------------------------------


class TestBaggageSpanProcessor:
    def test_copies_baggage_to_span_attributes(self, memory_tracer):
        tracer, exporter = memory_tracer
        ctx = baggage.set_baggage(BAGGAGE_TENANT_ID, "tenant-123")
        ctx = baggage.set_baggage(BAGGAGE_AGENT_ID, "agent-456", context=ctx)
        token = otel_context.attach(ctx)
        try:
            with tracer.start_span("bagg-span"):
                pass
        finally:
            otel_context.detach(token)

        attrs = get_attrs(exporter.get_finished_spans()[0])
        assert attrs.get(BAGGAGE_TENANT_ID) == "tenant-123"
        assert attrs.get(BAGGAGE_AGENT_ID) == "agent-456"

    def test_missing_baggage_not_added(self, memory_tracer):
        tracer, exporter = memory_tracer
        with tracer.start_span("no-bagg"):
            pass
        attrs = get_attrs(exporter.get_finished_spans()[0])
        assert BAGGAGE_TENANT_ID not in attrs
        assert BAGGAGE_AGENT_ID not in attrs

    def test_partial_baggage(self, memory_tracer):
        tracer, exporter = memory_tracer
        ctx = baggage.set_baggage(BAGGAGE_TENANT_ID, "t-001")
        token = otel_context.attach(ctx)
        try:
            with tracer.start_span("partial-bagg"):
                pass
        finally:
            otel_context.detach(token)

        attrs = get_attrs(exporter.get_finished_spans()[0])
        assert attrs.get(BAGGAGE_TENANT_ID) == "t-001"
        assert BAGGAGE_AGENT_ID not in attrs

    def test_on_end_is_noop(self):
        proc = BaggageSpanProcessor()
        proc.on_end(MagicMock())  # should not raise

    def test_shutdown_is_noop(self):
        proc = BaggageSpanProcessor()
        proc.shutdown()  # should not raise

    def test_force_flush_returns_true(self):
        proc = BaggageSpanProcessor()
        assert proc.force_flush() is True


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------


class TestSingletonHelpers:
    def test_get_default_tracer_returns_registered_instance(self, memory_tracer):
        tracer, _ = memory_tracer
        assert get_default_tracer() is tracer

    def test_get_default_tracer_same_instance_on_repeated_calls(self, memory_tracer):
        assert get_default_tracer() is get_default_tracer()

    def test_register_tracer_replaces_default(self, memory_tracer):
        old = tracer_module._default_tracer
        new_tracer = MagicMock()
        register_tracer(new_tracer)
        assert get_default_tracer() is new_tracer
        tracer_module._default_tracer = old  # restore

    def test_register_tracer_thread_safe(self, memory_tracer):
        errors = []

        def worker():
            try:
                register_tracer(MagicMock())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
