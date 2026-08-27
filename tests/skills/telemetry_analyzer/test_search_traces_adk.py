"""
Unit tests for skills/telemetry-analyzer/scripts/search_traces_adk.py

All tests are pure-logic: no network calls, no ADK imports required.
"""
import argparse
import sys
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Import helpers — the script lives outside the normal src/ tree, so we add
# its parent directory to sys.path before importing.
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "skills" / "telemetry-analyzer" / "scripts"


def _import_module(name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    # Stub out heavy ADK imports so the module-level code doesn't fail
    adk_stubs = [
        "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller",
        "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper",
        "ibm_watsonx_orchestrate.client.base_api_client",
        "ibm_watsonx_orchestrate.client.observability.traces",
        "ibm_watsonx_orchestrate.client.observability.traces.traces_client",
        "ibm_watsonx_orchestrate.client.utils",
        "dotenv",
    ]
    for stub in adk_stubs:
        sys.modules.setdefault(stub, MagicMock())
    spec.loader.exec_module(mod)
    return mod


mod = _import_module("search_traces_adk")


# ---------------------------------------------------------------------------
# parse_last
# ---------------------------------------------------------------------------
class TestParseLast:
    def test_minutes(self):
        assert mod.parse_last("30m") == timedelta(minutes=30)

    def test_minutes_long(self):
        assert mod.parse_last("5minutes") == timedelta(minutes=5)

    def test_hours(self):
        assert mod.parse_last("6h") == timedelta(hours=6)

    def test_hours_long(self):
        assert mod.parse_last("2hours") == timedelta(hours=2)

    def test_days(self):
        assert mod.parse_last("3d") == timedelta(days=3)

    def test_days_long(self):
        assert mod.parse_last("1day") == timedelta(days=1)

    def test_whitespace_stripped(self):
        assert mod.parse_last("  10m  ") == timedelta(minutes=10)

    def test_invalid_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            mod.parse_last("badvalue")

    def test_invalid_unit_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            mod.parse_last("5w")


# ---------------------------------------------------------------------------
# _find_repo_root
# ---------------------------------------------------------------------------
class TestFindRepoRoot:
    def test_finds_git_dir(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        assert mod._find_repo_root(nested) == tmp_path

    def test_falls_back_to_start_when_no_git(self, tmp_path):
        nested = tmp_path / "x" / "y"
        nested.mkdir(parents=True)
        # No .git anywhere — should return the start directory
        assert mod._find_repo_root(nested) == nested


# ---------------------------------------------------------------------------
# _bar (progress bar) — just assert it doesn't raise and writes to stdout
# ---------------------------------------------------------------------------
class TestBar:
    def test_bar_with_known_total(self, capsys):
        mod._bar(5, 10, label="pg1")
        out = capsys.readouterr().out
        assert "50.0%" in out
        assert "5/10" in out

    def test_bar_without_total_shows_spinner(self, capsys):
        mod._bar(3, None, label="")
        out = capsys.readouterr().out
        assert "3 traces fetched" in out


# ---------------------------------------------------------------------------
# search_all_traces — pagination logic
# ---------------------------------------------------------------------------
class TestSearchAllTraces:
    def _make_client(self, pages):
        """Return a mock client_ref whose _post cycles through *pages*."""
        client = MagicMock()
        client.base_endpoint = "https://example.com/traces"
        client._post.side_effect = pages
        return [client]

    def test_single_page_no_cursor(self, tmp_path):
        pages = [{"traceSummaries": [{"traceId": "aaa"}, {"traceId": "bbb"}], "nextCursor": None}]
        client_ref = self._make_client(pages)
        filters = MagicMock()
        sort = MagicMock()

        result = mod.search_all_traces(client_ref, filters, sort, limit=None)

        assert [t["traceId"] for t in result] == ["aaa", "bbb"]

    def test_multi_page_stops_on_empty_cursor(self, tmp_path):
        pages = [
            {"traceSummaries": [{"traceId": "p1"}], "nextCursor": "cursor1"},
            {"traceSummaries": [{"traceId": "p2"}], "nextCursor": None},
        ]
        client_ref = self._make_client(pages)

        result = mod.search_all_traces(client_ref, MagicMock(), MagicMock(), limit=None)

        assert [t["traceId"] for t in result] == ["p1", "p2"]

    def test_limit_stops_early(self, tmp_path):
        pages = [
            {"traceSummaries": [{"traceId": f"t{i}"} for i in range(5)], "nextCursor": "c"},
            {"traceSummaries": [{"traceId": f"t{i}"} for i in range(5, 10)], "nextCursor": None},
        ]
        client_ref = self._make_client(pages)

        result = mod.search_all_traces(client_ref, MagicMock(), MagicMock(), limit=5)

        assert len(result) == 5

    def test_checkpoint_written(self, tmp_path):
        pages = [{"traceSummaries": [{"traceId": "abc"}], "nextCursor": None}]
        client_ref = self._make_client(pages)
        checkpoint = tmp_path / "ids.txt"

        mod.search_all_traces(client_ref, MagicMock(), MagicMock(), limit=None,
                              checkpoint_path=checkpoint)

        assert "abc" in checkpoint.read_text()
