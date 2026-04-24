"""Shared fixtures for observability tests."""

import pytest

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import ibm_watsonx_orchestrate_sdk.observability.tracer as tracer_module
from ibm_watsonx_orchestrate_sdk.observability.attributes import ATTR_SERVICE_NAME
from ibm_watsonx_orchestrate_sdk.observability.tracer import (
    BaggageSpanProcessor,
    Tracer,
    register_tracer,
)


def _make_memory_tracer(monkeypatch):
    """Build a Tracer backed by InMemorySpanExporter using SimpleSpanProcessor."""
    exporter = InMemorySpanExporter()

    def fake_build_provider(self):
        resource = Resource.create({ATTR_SERVICE_NAME: self._config.service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BaggageSpanProcessor())
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        return provider

    monkeypatch.setattr(Tracer, "_build_provider", fake_build_provider)
    return Tracer(), exporter


@pytest.fixture
def memory_tracer(monkeypatch):
    """Yield (tracer, exporter) and restore the default tracer singleton afterwards."""
    old = tracer_module._default_tracer
    tracer, exporter = _make_memory_tracer(monkeypatch)
    register_tracer(tracer)
    yield tracer, exporter
    tracer_module._default_tracer = old
    tracer_module._execution_context_var.set(None)


@pytest.fixture
def traced(monkeypatch):
    """Yield InMemorySpanExporter with the default tracer set to a memory-backed Tracer."""
    old = tracer_module._default_tracer
    tracer, exporter = _make_memory_tracer(monkeypatch)
    register_tracer(tracer)
    yield exporter
    tracer_module._default_tracer = old
    tracer_module._execution_context_var.set(None)


def get_attrs(span) -> dict:
    return dict(span.attributes or {})
