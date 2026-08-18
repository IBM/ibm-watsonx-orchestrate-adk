#!/usr/bin/env python3
"""
Export trace spans using the new AgentOps v3 REST API:
  GET <INSTANCE_URL>/v1/agentops-v3/traces/<TRACE_ID>

Saves each trace as <trace_id>.json in Langfuse format in the data/ directory.

Usage:
    # Export a single trace by ID
    python scripts/export_traces_agentops_v3.py --trace-id <32-char-hex-id>

    # Export multiple trace IDs from a file (one ID per line)
    python scripts/export_traces_agentops_v3.py --ids-file data/trace_ids.txt

    # Change output directory (default: data/)
    python scripts/export_traces_agentops_v3.py --trace-id <id> --output-dir data

    # Compact JSON (not pretty-printed)
    python scripts/export_traces_agentops_v3.py --trace-id <id> --no-pretty
"""

import argparse
import json
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from repo root
# ---------------------------------------------------------------------------
def _find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return start

_repo_root = _find_repo_root(Path(__file__).resolve().parent)
_env_file = _repo_root / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file)

import requests

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
TRACES_PATH = "/v1/agentops-v3/traces"


# ---------------------------------------------------------------------------
# ADK helpers — pull instance base URL and bearer token
# ---------------------------------------------------------------------------
def _get_base_url_and_token() -> tuple[str, str]:
    """Return (base_url, bearer_token) for the active orchestrate environment.

    ``client.base_url`` varies by environment:
    - Some envs return a bare instance URL with no path suffix,
      e.g. ``https://api.us-south.watson-orchestrate.cloud.ibm.com/instances/<id>``.
    - Other envs already include ``/v1`` in ``base_url``,
      e.g. ``https://<host>/v1``.

    ``TRACES_PATH`` is defined as ``/v1/agentops-v3/traces`` so that it works
    correctly when ``base_url`` has no suffix.  If your environment's
    ``base_url`` already ends in ``/v1``, update ``TRACES_PATH`` to
    ``/agentops-v3/traces`` to avoid the doubled ``/v1/v1/`` segment.
    """
    from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller import TracesController
    client = TracesController().get_client()
    base = client.base_url.rstrip("/")
    if client.api_key:
        return base, client.api_key
    if client.authenticator:
        return base, client.authenticator.token_manager.get_token()
    raise RuntimeError("No bearer token available. Run: orchestrate env activate <env>")


# ---------------------------------------------------------------------------
# Fetch a single trace
# ---------------------------------------------------------------------------
def _fetch_trace(base: str, token: str, trace_id: str) -> dict:
    """GET /v1/agentops-v3/traces/<trace_id> — returns raw JSON."""
    url = f"{base}{TRACES_PATH}/{trace_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _bar(done: int, total: int, succeeded: int, failed: int, width: int = 40) -> None:
    filled = int(width * done / total) if total else 0
    bar = "█" * filled + "░" * (width - filled)
    pct = done / total * 100 if total else 0
    sys.stdout.write(f"\r  [{bar}] {pct:5.1f}%  {done}/{total}  ✓{succeeded}  ✗{failed}")
    sys.stdout.flush()


def export_trace(base: str, token: str, trace_id: str,
                 output_dir: Path, pretty: bool) -> bool:
    """Fetch and save one trace. Returns True on success."""
    trace_id = trace_id.strip()
    if not trace_id:
        return False

    output_file = output_dir / f"{trace_id}.json"
    t0 = time.monotonic()
    try:
        data = _fetch_trace(base, token, trace_id)
        elapsed = time.monotonic() - t0

        indent = 2 if pretty else None
        output_file.write_text(json.dumps(data, indent=indent))

        # Try to report a span count for feedback
        span_count = _count_spans(data)
        span_info = f"{span_count} spans" if span_count is not None else "saved"
        print(f"  OK  {trace_id}  ({span_info}, {elapsed:.1f}s)")
        return True

    except requests.HTTPError as e:
        elapsed = time.monotonic() - t0
        print(f"  FAILED  {trace_id}  (HTTP {e.response.status_code}, {elapsed:.1f}s)")
        return False
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"  FAILED  {trace_id}  ({e}, {elapsed:.1f}s)")
        return False


def _count_spans(data: dict) -> int | None:
    """Best-effort span count from whatever shape the API returns."""
    # OTel format: traceData.resourceSpans[].scopeSpans[].spans[]
    try:
        td = data.get("traceData") or data
        rs = td.get("resourceSpans", [])
        if rs:
            return sum(
                len(ss.get("spans", []))
                for r in rs
                for ss in r.get("scopeSpans", [])
            )
    except Exception:
        pass
    # Flat spans list
    if "spans" in data:
        return len(data["spans"])
    # Langfuse format: observations[]
    if "observations" in data:
        return len(data["observations"])
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Export traces via GET /v1/agentops-v3/traces/<id> (new observability stack)"
    )

    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("--trace-id", metavar="TRACE_ID",
                          help="A single trace ID to export")
    id_group.add_argument("--ids-file", metavar="FILE",
                          help="File with trace IDs, one per line")

    parser.add_argument("--output-dir", metavar="DIR", default=str(DEFAULT_OUTPUT_DIR),
                        help="Directory to write JSON files into (default: data/)")
    parser.add_argument("--no-pretty", action="store_true",
                        help="Write compact (non-indented) JSON")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.trace_id:
        trace_ids = [args.trace_id]
    else:
        ids_file = Path(args.ids_file)
        if not ids_file.exists():
            print(f"ERROR: IDs file not found: {ids_file}", file=sys.stderr)
            sys.exit(1)
        trace_ids = [l.strip() for l in ids_file.read_text().splitlines() if l.strip()]

    if not trace_ids:
        print("No trace IDs found. Nothing to export.")
        sys.exit(0)

    base, token = _get_base_url_and_token()

    print(f"Output dir: {output_dir}")
    print(f"Traces:     {len(trace_ids)}")
    print()

    succeeded, failed = 0, 0
    t0 = time.monotonic()

    for trace_id in trace_ids:
        if export_trace(base, token, trace_id, output_dir, pretty=not args.no_pretty):
            succeeded += 1
        else:
            failed += 1

    elapsed = time.monotonic() - t0
    print(f"\nDone. {succeeded} exported, {failed} failed.  Total time: {elapsed:.1f}s")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
