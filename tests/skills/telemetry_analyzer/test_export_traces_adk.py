"""
Unit tests for skills/telemetry-analyzer/scripts/export_traces_adk.py

All tests are pure-logic: no network calls, no ADK imports required.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "skills" / "telemetry-analyzer" / "scripts"


def _import_module(name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    for stub in [
        "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller",
        "ibm_watsonx_orchestrate.client.base_api_client",
        "dotenv",
    ]:
        sys.modules.setdefault(stub, MagicMock())
    spec.loader.exec_module(mod)
    return mod


mod = _import_module("export_traces_adk")


# ---------------------------------------------------------------------------
# _find_repo_root
# ---------------------------------------------------------------------------
class TestFindRepoRoot:
    def test_finds_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "sub"
        nested.mkdir()
        assert mod._find_repo_root(nested) == tmp_path

    def test_fallback_when_no_git(self, tmp_path):
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        assert mod._find_repo_root(nested) == nested


# ---------------------------------------------------------------------------
# _bar
# ---------------------------------------------------------------------------
class TestBar:
    def test_full_progress(self, capsys):
        mod._bar(10, 10, 9, 1)
        out = capsys.readouterr().out
        assert "100.0%" in out
        assert "✓9" in out
        assert "✗1" in out

    def test_zero_total_no_crash(self, capsys):
        # total=0 should not raise ZeroDivisionError
        mod._bar(0, 0, 0, 0)


# ---------------------------------------------------------------------------
# export_trace — success and failure paths
# ---------------------------------------------------------------------------
class TestExportTrace:
    def _make_controller(self, response):
        ctrl = MagicMock()
        ctrl.export_trace_to_json.return_value = (response, None)
        return ctrl

    def _otel_response(self, n_spans=3):
        """Build a mock spans_response in OTel shape."""
        resp = MagicMock()
        scope_span = {"spans": [{}] * n_spans}
        resource_span = MagicMock()
        resource_span.get = lambda k, d=None: ([scope_span] if k == "scopeSpans" else d)
        resp.traceData = MagicMock()
        resp.traceData.resourceSpans = [resource_span]
        resp.spans = None
        return resp

    def test_success_writes_file(self, tmp_path):
        resp = self._otel_response(n_spans=2)
        ctrl = self._make_controller(resp)
        result = mod.export_trace(ctrl, "abc123", tmp_path, pretty=True)
        assert result is True
        ctrl.export_trace_to_json.assert_called_once_with(
            trace_id="abc123",
            output_file=str(tmp_path / "abc123.json"),
            pretty=True,
        )

    def test_empty_trace_id_returns_false(self, tmp_path):
        ctrl = MagicMock()
        assert mod.export_trace(ctrl, "   ", tmp_path, pretty=True) is False
        ctrl.export_trace_to_json.assert_not_called()

    def test_value_error_returns_false(self, tmp_path):
        ctrl = MagicMock()
        ctrl.export_trace_to_json.side_effect = ValueError("bad trace")
        assert mod.export_trace(ctrl, "tid1", tmp_path, pretty=True) is False

    def test_client_api_exception_returns_false(self, tmp_path):
        ClientAPIException = sys.modules[
            "ibm_watsonx_orchestrate.client.base_api_client"
        ].ClientAPIException
        ClientAPIException.side_effect = None

        ctrl = MagicMock()
        exc = MagicMock(spec=Exception)
        exc.response = MagicMock()
        exc.response.status_code = 404

        # Make it raise a real exception subclass so except catches it
        class FakeClientAPIException(Exception):
            def __init__(self):
                self.response = MagicMock()
                self.response.status_code = 404

        with patch.object(
            sys.modules["ibm_watsonx_orchestrate.client.base_api_client"],
            "ClientAPIException",
            FakeClientAPIException,
        ):
            # Re-import so the except clause uses our patched class
            mod2 = _import_module("export_traces_adk")
            ctrl2 = MagicMock()
            ctrl2.export_trace_to_json.side_effect = FakeClientAPIException()
            assert mod2.export_trace(ctrl2, "tid2", tmp_path, pretty=True) is False

    def test_legacy_spans_response(self, tmp_path):
        resp = MagicMock()
        resp.traceData = None
        resp.spans = [MagicMock(), MagicMock()]
        ctrl = self._make_controller(resp)
        assert mod.export_trace(ctrl, "tid3", tmp_path, pretty=False) is True
        assert "legacy" in mod.export_trace._last_detail

    def test_no_span_data_response(self, tmp_path):
        resp = MagicMock()
        resp.traceData = None
        resp.spans = None
        ctrl = self._make_controller(resp)
        assert mod.export_trace(ctrl, "tid4", tmp_path, pretty=False) is True
        assert "no span data" in mod.export_trace._last_detail
