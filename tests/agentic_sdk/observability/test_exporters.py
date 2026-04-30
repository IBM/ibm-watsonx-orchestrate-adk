"""Tests for the exporter factory."""

import logging

import pytest

from ibm_watsonx_orchestrate_sdk.observability.attributes import ENV_OTLP_ENDPOINT
from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig
from ibm_watsonx_orchestrate_sdk.observability.exporters import create_exporter


class TestCreateExporter:
    def test_returns_console_exporter_when_no_endpoint(self, monkeypatch):
        monkeypatch.delenv(ENV_OTLP_ENDPOINT, raising=False)
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        exporter = create_exporter(TracerConfig())
        assert isinstance(exporter, ConsoleSpanExporter)

    def test_returns_otlp_exporter_when_endpoint_set(self, monkeypatch):
        monkeypatch.setenv(ENV_OTLP_ENDPOINT, "http://localhost:4318")
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = create_exporter(TracerConfig())
        assert isinstance(exporter, OTLPSpanExporter)

    def test_console_fallback_emits_warning(self, monkeypatch, caplog):
        monkeypatch.delenv(ENV_OTLP_ENDPOINT, raising=False)
        with caplog.at_level(
            logging.WARNING,
            logger="ibm_watsonx_orchestrate_sdk.observability.exporters",
        ):
            create_exporter(TracerConfig())
        assert ENV_OTLP_ENDPOINT in caplog.text

    def test_otlp_exporter_uses_endpoint(self, monkeypatch):
        url = "http://my-collector:4318/v1/traces"
        monkeypatch.setenv(ENV_OTLP_ENDPOINT, url)
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = create_exporter(TracerConfig())
        assert isinstance(exporter, OTLPSpanExporter)
