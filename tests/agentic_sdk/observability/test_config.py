"""Tests for TracerConfig."""

import pytest
from unittest.mock import MagicMock

from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    DEFAULT_SERVICE_NAME,
    ENV_OTLP_ENDPOINT,
)
from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig


def _cfg_with_session(base_url: str, path: str = "/inject/traces") -> TracerConfig:
    """Return a TracerConfig whose session has the given base_url."""
    session = MagicMock()
    session.base_url = base_url
    cfg = TracerConfig.__new__(TracerConfig)
    object.__setattr__(cfg, "_session", session)
    object.__setattr__(cfg, "trace_injection_path", path)
    return cfg


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


class TestEndpointUrlConstruction:
    """Verify that urljoin is used correctly for session-based endpoints."""

    def test_basic_path_appended_to_base(self):
        cfg = _cfg_with_session("https://instance.example.com", "/inject/traces")
        assert cfg.endpoint == "https://instance.example.com/inject/traces"

    def test_trailing_slash_on_base_does_not_double_slash(self):
        cfg = _cfg_with_session("https://instance.example.com/", "/inject/traces")
        assert cfg.endpoint == "https://instance.example.com/inject/traces"

    def test_base_with_existing_subpath(self):
        cfg = _cfg_with_session("https://instance.example.com/api/v1", "/inject/traces")
        assert cfg.endpoint == "https://instance.example.com/api/v1/inject/traces"

    def test_path_without_leading_slash(self):
        cfg = _cfg_with_session("https://instance.example.com", "inject/traces")
        assert cfg.endpoint == "https://instance.example.com/inject/traces"

    def test_absolute_path_used_directly(self):
        """When trace_injection_path is a full URL it must be returned as-is."""
        full_url = "https://other-host.example.com/custom/path"
        cfg = _cfg_with_session("https://instance.example.com", full_url)
        assert cfg.endpoint == full_url

    def test_no_session_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv(ENV_OTLP_ENDPOINT, "http://collector:4318")
        assert TracerConfig().endpoint == "http://collector:4318"
