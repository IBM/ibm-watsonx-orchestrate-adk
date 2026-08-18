"""
Unit tests for skills/telemetry-analyzer/scripts/export_traces_agentops_v3.py

All tests are pure-logic: no network calls, no ADK imports required.
"""
import json
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
        "dotenv",
        "requests",
    ]:
        sys.modules.setdefault(stub, MagicMock())
    spec.loader.exec_module(mod)
    return mod


mod = _import_module("export_traces_agentops_v3")


# ---------------------------------------------------------------------------
# _find_repo_root
# ---------------------------------------------------------------------------
class TestFindRepoRoot:
    def test_finds_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "deep"
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
    def test_renders_percentage(self, capsys):
        mod._bar(1, 4, succeeded=1, failed=0)
        out = capsys.readouterr().out
        assert "25.0%" in out

    def test_zero_total_no_crash(self, capsys):
        mod._bar(0, 0, succeeded=0, failed=0)


# ---------------------------------------------------------------------------
# _count_spans
# ---------------------------------------------------------------------------
class TestCountSpans:
    def test_otel_format(self):
        data = {
            "traceData": {
                "resourceSpans": [
                    {"scopeSpans": [{"spans": [{}, {}]}, {"spans": [{}]}]},
                ]
            }
        }
        assert mod._count_spans(data) == 3

    def test_otel_format_top_level_trace_data(self):
        """traceData at top-level (no extra nesting)."""
        data = {
            "resourceSpans": [
                {"scopeSpans": [{"spans": [{}, {}, {}]}]},
            ]
        }
        assert mod._count_spans(data) == 3

    def test_flat_spans_list(self):
        data = {"spans": [{}, {}, {}, {}]}
        assert mod._count_spans(data) == 4

    def test_langfuse_observations(self):
        data = {"observations": [{"id": "a"}, {"id": "b"}]}
        assert mod._count_spans(data) == 2

    def test_empty_data_returns_none(self):
        assert mod._count_spans({}) is None

    def test_malformed_resource_spans_falls_through(self):
        # resourceSpans present but empty → falls through to check "spans"
        data = {"traceData": {"resourceSpans": []}, "spans": [{}]}
        assert mod._count_spans(data) == 1


# ---------------------------------------------------------------------------
# export_trace — success and failure paths
# ---------------------------------------------------------------------------
class TestExportTrace:
    def _make_requests_get(self, payload: dict, status_code: int = 200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = payload
        if status_code >= 400:
            resp.raise_for_status.side_effect = __import__("requests").HTTPError(response=resp)
        else:
            resp.raise_for_status.return_value = None
        return resp

    def test_success_writes_json_file(self, tmp_path):
        payload = {"observations": [{"id": "s1"}, {"id": "s2"}]}
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = payload

        with patch.object(mod, "_fetch_trace", return_value=payload):
            result = mod.export_trace("https://h", "tok", "trace001", tmp_path, pretty=True)

        assert result is True
        written = json.loads((tmp_path / "trace001.json").read_text())
        assert written == payload

    def test_success_compact_json(self, tmp_path):
        payload = {"observations": []}
        with patch.object(mod, "_fetch_trace", return_value=payload):
            mod.export_trace("https://h", "tok", "trace002", tmp_path, pretty=False)

        raw = (tmp_path / "trace002.json").read_text()
        # compact JSON has no newlines
        assert "\n" not in raw

    def test_empty_trace_id_returns_false(self, tmp_path):
        result = mod.export_trace("https://h", "tok", "   ", tmp_path, pretty=True)
        assert result is False

    def test_http_error_returns_false(self, tmp_path):
        import requests as req_mod
        http_err = req_mod.HTTPError(response=MagicMock(status_code=404))

        with patch.object(mod, "_fetch_trace", side_effect=http_err):
            result = mod.export_trace("https://h", "tok", "bad_id", tmp_path, pretty=True)

        assert result is False

    def test_generic_exception_returns_false(self, tmp_path):
        with patch.object(mod, "_fetch_trace", side_effect=RuntimeError("boom")):
            result = mod.export_trace("https://h", "tok", "err_id", tmp_path, pretty=True)

        assert result is False
