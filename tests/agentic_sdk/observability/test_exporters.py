"""Tests for the exporter factory and DynamicAuthOTLPSpanExporter."""

import logging
import threading
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from ibm_watsonx_orchestrate_sdk.observability.attributes import ENV_OTLP_ENDPOINT
from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig
from ibm_watsonx_orchestrate_sdk.observability.exporters import (
    DynamicAuthOTLPSpanExporter,
    _apply_ssl_verify,
    create_exporter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(*, access_token=None, authenticator=None, base_url="http://host"):
    """Return a minimal mock AgenticSession."""
    session = MagicMock()
    session.access_token = access_token
    session.authenticator = authenticator
    session.base_url = base_url
    return session


def _make_config_with_authenticator(token="tok-abc", base_url="http://host"):
    """Return a TracerConfig backed by a mock authenticator session."""
    auth = MagicMock()
    auth.token_manager = MagicMock()
    auth.token_manager.get_token.return_value = token

    config = MagicMock(spec=TracerConfig)
    config.endpoint = f"{base_url}/inject/traces"
    config.session = _make_session(authenticator=auth, base_url=base_url)
    config.get_auth_headers.return_value = {"Authorization": f"Bearer {token}"}
    return config


# ---------------------------------------------------------------------------
# create_exporter factory
# ---------------------------------------------------------------------------


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

    def test_returns_dynamic_exporter_when_authenticator_present(self, monkeypatch):
        """create_exporter must return DynamicAuthOTLPSpanExporter when an
        authenticator is set on the session."""
        config = _make_config_with_authenticator()
        exporter = create_exporter(config)
        assert isinstance(exporter, DynamicAuthOTLPSpanExporter)

    def test_returns_static_otlp_exporter_when_access_token_only(self, monkeypatch):
        """create_exporter falls back to plain OTLPSpanExporter for static tokens."""
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        config = MagicMock(spec=TracerConfig)
        config.endpoint = "http://host/inject/traces"
        config.session = _make_session(access_token="static-tok", authenticator=None)
        config.get_auth_headers.return_value = {"Authorization": "Bearer static-tok"}

        exporter = create_exporter(config)
        assert isinstance(exporter, OTLPSpanExporter)


# ---------------------------------------------------------------------------
# DynamicAuthOTLPSpanExporter — error handling
# ---------------------------------------------------------------------------


class TestDynamicAuthOTLPSpanExporterErrorHandling:
    def _make_exporter(self, token="initial"):
        config = _make_config_with_authenticator(token=token)
        return DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)

    def test_init_succeeds_when_get_auth_headers_raises(self, caplog):
        """__init__ must not raise even if get_auth_headers() fails; a warning is logged."""
        config = _make_config_with_authenticator()
        config.get_auth_headers.side_effect = RuntimeError("token endpoint down")

        with caplog.at_level(
            logging.WARNING,
            logger="ibm_watsonx_orchestrate_sdk.observability.exporters",
        ):
            exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)

        assert exporter is not None
        assert "Failed to fetch initial authentication headers" in caplog.text

    def test_export_proceeds_when_header_update_raises(self):
        """If session.headers.update() raises the export must still be attempted."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        config = _make_config_with_authenticator(token="tok")
        exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)

        fake_session = MagicMock()
        fake_session.headers.update.side_effect = RuntimeError("headers locked")
        inner = MagicMock()
        inner._session = fake_session
        inner.export.return_value = SpanExportResult.SUCCESS
        exporter._exporter = inner

        result = exporter.export([MagicMock()])

        inner.export.assert_called_once()
        assert result == SpanExportResult.SUCCESS

    def test_export_warns_when_header_update_raises(self, caplog):
        """A warning must be emitted when session.headers.update() fails."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        config = _make_config_with_authenticator(token="tok")
        exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)

        fake_session = MagicMock()
        fake_session.headers.update.side_effect = RuntimeError("headers locked")
        inner = MagicMock()
        inner._session = fake_session
        inner.export.return_value = SpanExportResult.SUCCESS
        exporter._exporter = inner

        with caplog.at_level(
            logging.WARNING,
            logger="ibm_watsonx_orchestrate_sdk.observability.exporters",
        ):
            exporter.export([MagicMock()])

        assert "Failed to update session headers" in caplog.text

    def test_export_proceeds_when_get_auth_headers_raises(self):
        """If get_auth_headers raises during export (not __init__), the exception
        must be caught, a warning logged, and the underlying exporter still called."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        # Build the exporter with a healthy config first so __init__ succeeds,
        # then inject the failure for the export-time refresh call.
        config = _make_config_with_authenticator()
        exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)
        config.get_auth_headers.side_effect = RuntimeError("auth server unavailable")

        inner = MagicMock()
        inner.export.return_value = SpanExportResult.SUCCESS
        exporter._exporter = inner

        result = exporter.export([MagicMock()])

        # Export must still be called despite the refresh failure
        inner.export.assert_called_once()
        assert result == SpanExportResult.SUCCESS

    def test_export_emits_warning_when_token_refresh_fails(self, caplog):
        """A warning must be logged when token refresh fails."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        config = _make_config_with_authenticator()
        exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)
        config.get_auth_headers.side_effect = RuntimeError("network error")

        inner = MagicMock()
        inner.export.return_value = SpanExportResult.SUCCESS
        exporter._exporter = inner

        with caplog.at_level(
            logging.WARNING,
            logger="ibm_watsonx_orchestrate_sdk.observability.exporters",
        ):
            exporter.export([MagicMock()])

        assert "Failed to refresh authentication token" in caplog.text

    def test_export_updates_session_headers_on_success(self):
        """Fresh headers must be applied to the underlying session before export."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        config = _make_config_with_authenticator(token="new-token")
        exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)

        fake_session = MagicMock()
        inner = MagicMock()
        inner._session = fake_session
        inner.export.return_value = SpanExportResult.SUCCESS
        exporter._exporter = inner

        exporter.export([MagicMock()])

        fake_session.headers.update.assert_called_once_with(
            {"Authorization": "Bearer new-token"}
        )


# ---------------------------------------------------------------------------
# DynamicAuthOTLPSpanExporter — thread safety
# ---------------------------------------------------------------------------


class TestDynamicAuthOTLPSpanExporterThreadSafety:
    """Verify that concurrent exports do not race on session header updates."""

    def test_concurrent_exports_do_not_raise(self):
        """Spawning many threads that export simultaneously must complete
        without exceptions."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        config = _make_config_with_authenticator()
        exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)

        inner = MagicMock()
        inner._session = MagicMock()
        inner.export.return_value = SpanExportResult.SUCCESS
        exporter._exporter = inner

        errors: list = []

        def worker():
            try:
                exporter.export([MagicMock()])
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors during concurrent export: {errors}"

    def test_concurrent_exports_all_complete(self):
        """Every thread must get a result, proving no thread is starved."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        config = _make_config_with_authenticator()
        exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)

        inner = MagicMock()
        inner._session = MagicMock()
        inner.export.return_value = SpanExportResult.SUCCESS
        exporter._exporter = inner

        results: list = []

        def worker():
            results.append(exporter.export([MagicMock()]))

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 30
        assert all(r == SpanExportResult.SUCCESS for r in results)

    def test_header_update_is_serialised(self):
        """Ensure that header updates and the downstream export call are
        never interleaved across threads (lock covers both operations)."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        call_order: list = []
        lock = threading.Lock()

        config = _make_config_with_authenticator()
        exporter = DynamicAuthOTLPSpanExporter(endpoint=config.endpoint, config=config)

        def recording_update(headers):
            with lock:
                call_order.append(("update", threading.current_thread().ident))

        fake_session = MagicMock()
        fake_session.headers.update.side_effect = recording_update

        inner = MagicMock()
        inner._session = fake_session

        def recording_export(spans):
            with lock:
                call_order.append(("export", threading.current_thread().ident))
            return SpanExportResult.SUCCESS

        inner.export.side_effect = recording_export
        exporter._exporter = inner

        threads = [threading.Thread(target=lambda: exporter.export([MagicMock()])) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each "update" must be immediately followed by its paired "export"
        # from the SAME thread — the lock guarantees no other thread slips in.
        for i in range(0, len(call_order) - 1, 2):
            op1, tid1 = call_order[i]
            op2, tid2 = call_order[i + 1]
            assert op1 == "update", f"Expected 'update' at position {i}, got {op1}"
            assert op2 == "export", f"Expected 'export' at position {i+1}, got {op2}"
            assert tid1 == tid2, "update and export must be from the same thread"


# ---------------------------------------------------------------------------
# TracerConfig.get_auth_headers — error handling
# ---------------------------------------------------------------------------


class TestGetAuthHeadersErrorHandling:
    """Verify the improved error handling in TracerConfig.get_auth_headers."""

    def _config_with_authenticator(self, side_effect=None, return_value="tok"):
        """Return a real TracerConfig whose session authenticator is mocked."""
        auth = MagicMock()
        auth.token_manager = MagicMock()
        if side_effect:
            auth.token_manager.get_token.side_effect = side_effect
        else:
            auth.token_manager.get_token.return_value = return_value

        session = _make_session(authenticator=auth)
        config = TracerConfig.__new__(TracerConfig)
        # Bypass __post_init__ by setting attributes directly
        object.__setattr__(config, "_session", session)
        object.__setattr__(config, "client", MagicMock())
        return config

    def test_raises_runtime_error_when_token_retrieval_fails(self):
        """A failing authenticator must raise RuntimeError (not silently swallow it)."""
        config = self._config_with_authenticator(
            side_effect=ConnectionError("token endpoint unreachable")
        )
        with pytest.raises(RuntimeError, match="Failed to retrieve authentication token"):
            config.get_auth_headers()

    def test_runtime_error_chains_original_cause(self):
        """The RuntimeError must chain the original exception as __cause__."""
        original = ConnectionError("token endpoint unreachable")
        config = self._config_with_authenticator(side_effect=original)
        with pytest.raises(RuntimeError) as exc_info:
            config.get_auth_headers()
        assert exc_info.value.__cause__ is original

    def test_warns_on_empty_token(self, caplog):
        """An authenticator returning an empty string must log a warning, not raise."""
        config = self._config_with_authenticator(return_value="")
        with caplog.at_level(
            logging.WARNING,
            logger="ibm_watsonx_orchestrate_sdk.observability.config",
        ):
            headers = config.get_auth_headers()
        assert headers == {}
        assert "empty token" in caplog.text

    def test_returns_bearer_token_on_success(self):
        """A healthy authenticator must produce a valid Authorization header."""
        config = self._config_with_authenticator(return_value="good-token")
        headers = config.get_auth_headers()
        assert headers == {"Authorization": "Bearer good-token"}


# ---------------------------------------------------------------------------
# _apply_ssl_verify
# ---------------------------------------------------------------------------


class TestApplySSLVerify:
    """_apply_ssl_verify covers all three internal transport layouts."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_pool_exporter(self, initial_kw=None):
        """Mock shaped like OTLPSpanExporter v0.66b0+:
        exporter._client._transport._pool.connection_pool_kw
        """
        kw = dict(initial_kw) if initial_kw else {}
        pool = MagicMock(spec=["connection_pool_kw"])
        pool.connection_pool_kw = kw
        client_transport = MagicMock(spec=["_pool"])
        client_transport._pool = pool
        client = MagicMock(spec=["_transport"])
        client._transport = client_transport
        exporter = MagicMock(spec=["_client"])
        exporter._client = client
        return exporter, kw

    # ------------------------------------------------------------------
    # v0.66b0+ path: _client._transport._pool.connection_pool_kw
    # ------------------------------------------------------------------

    def test_v066_sets_cert_reqs_none_when_ssl_verify_false(self):
        """v0.66b0+: ssl_verify=False sets cert_reqs=CERT_NONE and removes ca_certs."""
        import ssl as _ssl
        exporter, kw = self._make_pool_exporter(initial_kw={"ca_certs": "/old/bundle.crt"})
        _apply_ssl_verify(exporter, False)
        assert kw["cert_reqs"] == _ssl.CERT_NONE
        assert "ca_certs" not in kw

    def test_v066_sets_ca_certs_when_ssl_verify_is_string(self):
        """v0.66b0+: ssl_verify='/path/ca.crt' sets ca_certs to that path."""
        exporter, kw = self._make_pool_exporter()
        _apply_ssl_verify(exporter, "/path/to/ca.crt")
        assert kw["ca_certs"] == "/path/to/ca.crt"
        assert "cert_reqs" not in kw

    def test_v066_no_mutation_when_ssl_verify_true(self):
        """ssl_verify=True must return immediately — pool kw must be untouched."""
        exporter, kw = self._make_pool_exporter(initial_kw={"ca_certs": "/original.crt"})
        _apply_ssl_verify(exporter, True)
        assert kw == {"ca_certs": "/original.crt"}

    # ------------------------------------------------------------------
    # mid path: exporter._transport.verify / ._transport._session.verify
    # ------------------------------------------------------------------

    def test_mid_sets_verify_false_on_transport_attr(self):
        """Mid layout: ssl_verify=False sets exporter._transport.verify."""
        exporter = MagicMock(spec=["_transport"])
        exporter._transport = MagicMock(spec=["verify"])
        _apply_ssl_verify(exporter, False)
        assert exporter._transport.verify is False

    def test_mid_sets_ca_bundle_on_transport_attr(self):
        """Mid layout: ssl_verify=str sets exporter._transport.verify to the path."""
        exporter = MagicMock(spec=["_transport"])
        exporter._transport = MagicMock(spec=["verify"])
        _apply_ssl_verify(exporter, "/my/ca.crt")
        assert exporter._transport.verify == "/my/ca.crt"

    def test_mid_sets_verify_on_transport_inner_session(self):
        """Mid layout: exporter._transport._session.verify"""
        exporter = MagicMock(spec=["_transport"])
        inner = MagicMock(spec=["verify"])
        exporter._transport = MagicMock(spec=["_session"])
        exporter._transport._session = inner
        _apply_ssl_verify(exporter, False)
        assert inner.verify is False

    # ------------------------------------------------------------------
    # older path: exporter._session.verify
    # ------------------------------------------------------------------

    def test_older_sets_verify_false_on_direct_session(self):
        """Older layout: ssl_verify=False sets exporter._session.verify."""
        exporter = MagicMock(spec=["_session"])
        exporter._session = MagicMock(spec=["verify"])
        _apply_ssl_verify(exporter, False)
        assert exporter._session.verify is False

    def test_older_sets_ca_bundle_on_direct_session(self):
        """Older layout: ssl_verify=str sets exporter._session.verify to the path."""
        exporter = MagicMock(spec=["_session"])
        exporter._session = MagicMock(spec=["verify"])
        _apply_ssl_verify(exporter, "/ca/bundle.crt")
        assert exporter._session.verify == "/ca/bundle.crt"

    # ------------------------------------------------------------------
    # unknown layout — warning must be emitted, no raise
    # ------------------------------------------------------------------

    def test_emits_warning_when_no_path_matched(self, caplog):
        """Must log a warning when no known transport attribute is found."""
        exporter = MagicMock(spec=[])
        with caplog.at_level(logging.WARNING, logger="ibm_watsonx_orchestrate_sdk.observability.exporters"):
            _apply_ssl_verify(exporter, False)
        assert any("ssl_verify" in r.message for r in caplog.records)

    def test_does_not_raise_when_no_transport_no_session(self):
        """Must not raise even if the exporter exposes no known attribute."""
        exporter = MagicMock(spec=[])
        _apply_ssl_verify(exporter, False)  # should not raise


# ---------------------------------------------------------------------------
# SSL verify propagation — create_exporter and DynamicAuthOTLPSpanExporter
# ---------------------------------------------------------------------------


class TestSSLVerifyPropagation:
    """_apply_ssl_verify must be called when ssl_verify is set, skipped when None."""

    def _static_config(self, ssl_verify):
        config = MagicMock(spec=TracerConfig)
        config.endpoint = "https://cpd-host/v1/orchestrate/inject/traces"
        config.ssl_verify = ssl_verify
        config.session = MagicMock()
        config.session.authenticator = None
        config.get_auth_headers.return_value = {"Authorization": "Bearer tok"}
        return config

    def _dynamic_config(self, ssl_verify):
        auth = MagicMock()
        auth.token_manager = MagicMock()
        auth.token_manager.get_token.return_value = "tok"
        config = MagicMock(spec=TracerConfig)
        config.endpoint = "https://cpd-host/v1/orchestrate/inject/traces"
        config.ssl_verify = ssl_verify
        config.session = MagicMock()
        config.session.authenticator = auth
        config.get_auth_headers.return_value = {"Authorization": "Bearer tok"}
        return config

    def test_static_exporter_calls_apply_when_ssl_verify_false(self):
        with patch("ibm_watsonx_orchestrate_sdk.observability.exporters._apply_ssl_verify") as m:
            create_exporter(self._static_config(False))
            m.assert_called_once()
            assert m.call_args[0][1] is False

    def test_static_exporter_skips_apply_when_ssl_verify_none(self):
        with patch("ibm_watsonx_orchestrate_sdk.observability.exporters._apply_ssl_verify") as m:
            create_exporter(self._static_config(None))
            m.assert_not_called()

    def test_dynamic_exporter_calls_apply_when_ssl_verify_false(self):
        with patch("ibm_watsonx_orchestrate_sdk.observability.exporters._apply_ssl_verify") as m:
            DynamicAuthOTLPSpanExporter(
                endpoint="https://cpd-host/inject/traces",
                config=self._dynamic_config(False),
            )
            m.assert_called_once()
            assert m.call_args[0][1] is False

    def test_dynamic_exporter_skips_apply_when_ssl_verify_none(self):
        with patch("ibm_watsonx_orchestrate_sdk.observability.exporters._apply_ssl_verify") as m:
            DynamicAuthOTLPSpanExporter(
                endpoint="https://cpd-host/inject/traces",
                config=self._dynamic_config(None),
            )
            m.assert_not_called()


