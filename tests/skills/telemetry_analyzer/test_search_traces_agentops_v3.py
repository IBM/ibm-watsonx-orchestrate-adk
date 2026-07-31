"""
Unit tests for skills/telemetry-analyzer/scripts/search_traces_agentops_v3.py

All tests are pure-logic: no network calls, no ADK imports required.
"""
import argparse
import sys
from datetime import timedelta
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


mod = _import_module("search_traces_agentops_v3")


# ---------------------------------------------------------------------------
# parse_last
# ---------------------------------------------------------------------------
class TestParseLast:
    def test_minutes(self):
        assert mod.parse_last("20m") == timedelta(minutes=20)

    def test_hours(self):
        assert mod.parse_last("2h") == timedelta(hours=2)

    def test_days(self):
        assert mod.parse_last("7d") == timedelta(days=7)

    def test_plural_unit(self):
        assert mod.parse_last("3days") == timedelta(days=3)

    def test_invalid_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            mod.parse_last("nope")


# ---------------------------------------------------------------------------
# _find_repo_root
# ---------------------------------------------------------------------------
class TestFindRepoRoot:
    def test_finds_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "deep" / "path"
        nested.mkdir(parents=True)
        assert mod._find_repo_root(nested) == tmp_path

    def test_fallback_when_no_git(self, tmp_path):
        nested = tmp_path / "no" / "git"
        nested.mkdir(parents=True)
        assert mod._find_repo_root(nested) == nested


# ---------------------------------------------------------------------------
# _bar
# ---------------------------------------------------------------------------
class TestBar:
    def test_known_total(self, capsys):
        mod._bar(25, 50)
        assert "50.0%" in capsys.readouterr().out

    def test_unknown_total_spinner(self, capsys):
        mod._bar(4, None)
        assert "4 traces fetched" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# search_all_traces — pagination and checkpoint
# ---------------------------------------------------------------------------
class TestSearchAllTraces:
    def _page(self, items, has_more=False):
        """Build a raw API page dict."""
        return {"traces": items}

    def test_single_page_list_response(self, tmp_path):
        """API returns a bare list (no envelope)."""
        raw_pages = [[{"traceId": "x1"}, {"traceId": "x2"}]]
        call_count = 0

        def fake_get_page(base, token, from_ts, to_ts, page, limit):
            nonlocal call_count
            call_count += 1
            return raw_pages[page - 1]

        with patch.object(mod, "_get_traces_page", side_effect=fake_get_page):
            result = mod.search_all_traces("http://h", "tok", "t1", "t2", limit=None)

        assert [t["traceId"] for t in result] == ["x1", "x2"]

    def test_envelope_response(self, tmp_path):
        """API returns {traces: [...]}."""
        def fake_get_page(base, token, from_ts, to_ts, page, limit):
            if page == 1:
                return {"traces": [{"traceId": "e1"}]}
            return {"traces": []}

        with patch.object(mod, "_get_traces_page", side_effect=fake_get_page):
            result = mod.search_all_traces("http://h", "tok", "t1", "t2", limit=None)

        assert [t["traceId"] for t in result] == ["e1"]

    def test_limit_stops_pagination(self):
        def fake_get_page(base, token, from_ts, to_ts, page, limit):
            return {"traces": [{"traceId": f"t{i}"} for i in range(limit)]}

        with patch.object(mod, "_get_traces_page", side_effect=fake_get_page):
            result = mod.search_all_traces("http://h", "tok", "t1", "t2", limit=3)

        assert len(result) == 3

    def test_checkpoint_written(self, tmp_path):
        checkpoint = tmp_path / "ids.txt"

        def fake_get_page(base, token, from_ts, to_ts, page, limit):
            if page == 1:
                return {"traces": [{"traceId": "chk1"}, {"traceId": "chk2"}]}
            return {"traces": []}

        with patch.object(mod, "_get_traces_page", side_effect=fake_get_page):
            mod.search_all_traces("http://h", "tok", "t1", "t2", limit=None,
                                  checkpoint_path=checkpoint)

        content = checkpoint.read_text()
        assert "chk1" in content
        assert "chk2" in content

    def test_rate_limit_retry(self):
        """A _RateLimited exception triggers a wait-and-retry."""
        call_count = 0

        def fake_get_page(base, token, from_ts, to_ts, page, limit):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                resp = MagicMock()
                resp.json.return_value = {"retry_after": "1s"}
                raise mod._RateLimited(resp)
            return {"traces": [{"traceId": "after_retry"}]}

        with patch.object(mod, "_get_traces_page", side_effect=fake_get_page), \
             patch("time.sleep"):
            result = mod.search_all_traces("http://h", "tok", "t1", "t2", limit=None)

        assert result[0]["traceId"] == "after_retry"
        assert call_count == 2
