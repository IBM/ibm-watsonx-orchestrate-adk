"""Tests for TracerConfig."""

import pytest

from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    DEFAULT_SERVICE_NAME,
    ENV_OTLP_ENDPOINT,
)
from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig


class TestTracerConfigDefaults:
    def test_default_service_name(self):
        assert TracerConfig().service_name == DEFAULT_SERVICE_NAME

    def test_default_resource_attributes_empty(self):
        assert TracerConfig().resource_attributes == {}

    def test_resource_attributes_isolated_between_instances(self):
        cfg1 = TracerConfig()
        cfg2 = TracerConfig()
        cfg1.resource_attributes["x"] = "1"
        assert "x" not in cfg2.resource_attributes


class TestTracerConfigEndpoint:
    def test_endpoint_none_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv(ENV_OTLP_ENDPOINT, raising=False)
        assert TracerConfig().endpoint is None

    def test_endpoint_reads_from_env(self, monkeypatch):
        monkeypatch.setenv(ENV_OTLP_ENDPOINT, "http://collector:4318")
        assert TracerConfig().endpoint == "http://collector:4318"

    def test_endpoint_is_read_at_call_time_not_init(self, monkeypatch):
        monkeypatch.delenv(ENV_OTLP_ENDPOINT, raising=False)
        cfg = TracerConfig()
        assert cfg.endpoint is None
        monkeypatch.setenv(ENV_OTLP_ENDPOINT, "http://late-set:4318")
        assert cfg.endpoint == "http://late-set:4318"


class TestTracerConfigCustom:
    def test_custom_service_name(self):
        cfg = TracerConfig(service_name="my-agent")
        assert cfg.service_name == "my-agent"

    def test_custom_resource_attributes(self):
        attrs = {"env": "prod", "region": "us-south"}
        cfg = TracerConfig(resource_attributes=attrs)
        assert cfg.resource_attributes == attrs


class TestBuildResourceAttributes:
    def test_empty_by_default(self):
        assert TracerConfig().build_resource_attributes() == {}

    def test_returns_resource_attributes(self):
        attrs = {"key": "val"}
        result = TracerConfig(resource_attributes=attrs).build_resource_attributes()
        assert result == attrs

    def test_mutating_result_does_not_affect_config(self):
        cfg = TracerConfig(resource_attributes={"a": "b"})
        result = cfg.build_resource_attributes()
        result["extra"] = "x"
        assert "extra" not in cfg.resource_attributes

    def test_service_name_not_included(self):
        cfg = TracerConfig(service_name="svc")
        result = cfg.build_resource_attributes()
        assert "service.name" not in result
