#!/usr/bin/env python3
"""
Search traces using the new AgentOps v3 REST API:
  GET <INSTANCE_URL>/v1/agentops-v3/traces
    ?fromTimestamp=<ISO8601>
    &toTimestamp=<ISO8601>
    &page=<int>
    &limit=<int>

Auth is a Bearer token obtained from the active orchestrate ADK client
(already an IAM JWT — no extra IAM call needed).

Usage:
    python scripts/search_traces_agentops_v3.py --last 30m
    python scripts/search_traces_agentops_v3.py \
        --start 2026-07-20T17:26:08Z --end 2026-07-20T17:49:52Z --all
    python scripts/search_traces_agentops_v3.py --all --save-ids data/trace_ids.txt
"""

import argparse
import re
import sys
import time
from datetime import datetime, timezone, timedelta
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
# The new agentops-v3 search call
# ---------------------------------------------------------------------------
TRACES_PATH = "/v1/agentops-v3/traces"
DEFAULT_PAGE_LIMIT = 100
DEFAULT_IDS_DIR = Path(__file__).resolve().parent.parent / "data"


def _get_traces_page(base: str, token: str, from_ts: str, to_ts: str,
                     page: int, limit: int) -> dict:
    """GET /v1/agentops-v3/traces with pagination query params.  Returns raw JSON."""
    url = f"{base}{TRACES_PATH}"
    params = {
        "fromTimestamp": from_ts,
        "toTimestamp":   to_ts,
        "page":          page,
        "limit":         limit,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }
    resp = requests.get(url, params=params, headers=headers, timeout=120)
    if resp.status_code == 429:
        raise _RateLimited(resp)
    resp.raise_for_status()
    return resp.json()


class _RateLimited(Exception):
    def __init__(self, resp):
        self.resp = resp


# ---------------------------------------------------------------------------
# Pagination driver
# ---------------------------------------------------------------------------
def search_all_traces(base: str, token: str,
                      from_ts: str, to_ts: str,
                      limit: int | None,
                      checkpoint_path: Path | None = None) -> list[dict]:
    """Page through agentops-v3/traces until exhausted or limit reached."""
    results: list[dict] = []
    page = 1

    if checkpoint_path:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text("")

    while True:
        page_limit = DEFAULT_PAGE_LIMIT if limit is None else min(DEFAULT_PAGE_LIMIT, limit - len(results))

        # Retry loop for 429
        while True:
            try:
                raw = _get_traces_page(base, token, from_ts, to_ts, page, page_limit)
                break
            except _RateLimited as e:
                body = {}
                try:
                    body = e.resp.json()
                except Exception:
                    pass
                wait_str = body.get("retry_after", "60s")
                wait = int(re.search(r"\d+", str(wait_str)).group())
                print(f"\n  Rate limited — waiting {wait}s before retrying page {page}...")
                time.sleep(wait + 1)

        # The API may return a list directly or wrap it
        if isinstance(raw, list):
            batch = raw
        else:
            # try common envelope keys
            batch = (
                raw.get("traces") or
                raw.get("data") or
                raw.get("items") or
                raw.get("results") or
                (raw if isinstance(raw, list) else [])
            )

        results.extend(batch)

        if checkpoint_path and batch:
            with checkpoint_path.open("a") as f:
                for t in batch:
                    tid = t.get("traceId") or t.get("trace_id") or t.get("id") or ""
                    if tid:
                        f.write(tid + "\n")

        _bar(len(results), limit)

        reached_limit = limit is not None and len(results) >= limit
        if not batch or len(batch) < page_limit or reached_limit:
            break

        page += 1

    sys.stdout.write("\n")
    sys.stdout.flush()
    return results


def _bar(done: int, total: int | None, width: int = 40) -> None:
    if total:
        filled = int(width * done / total)
        bar = "█" * filled + "░" * (width - filled)
        pct = done / total * 100
        line = f"\r  [{bar}] {pct:5.1f}%  {done}/{total}"
    else:
        spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[done % 10]
        line = f"\r  {spinner}  {done} traces fetched"
    sys.stdout.write(line)
    sys.stdout.flush()


def parse_last(value: str) -> timedelta:
    match = re.fullmatch(r"(\d+)\s*(m|h|d|minutes?|hours?|days?)", value.strip(), re.IGNORECASE)
    if not match:
        raise argparse.ArgumentTypeError(f"Invalid --last value '{value}'. Use e.g. 30m, 6h, 3d.")
    n, unit = int(match.group(1)), match.group(2).lower()
    if unit.startswith("m"):
        return timedelta(minutes=n)
    if unit.startswith("h"):
        return timedelta(hours=n)
    return timedelta(days=n)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Search traces via GET /v1/agentops-v3/traces (new observability stack)"
    )

    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument("--last",  metavar="WINDOW",
                            help="Relative window, e.g. 30m, 2h, 3d. Default: 20m")
    time_group.add_argument("--start", metavar="ISO8601",
                            help="Explicit start time (ISO 8601 UTC)")
    parser.add_argument("--end", metavar="ISO8601",
                        help="Explicit end time (ISO 8601 UTC). Requires --start.")

    limit_group = parser.add_mutually_exclusive_group()
    limit_group.add_argument("--limit", type=int, default=50,
                             help="Max traces to return (default: 50)")
    limit_group.add_argument("--all", dest="fetch_all", action="store_true",
                             help="Fetch every trace in the window")

    parser.add_argument("--count", action="store_true",
                        help="Print total count only")
    parser.add_argument("--save-ids", metavar="FILE",
                        help="Save trace IDs to this file (default: data/<agent>_<ts>_ids.txt)")

    # kept for backwards compat — ignored, always uses the new endpoint
    parser.add_argument("--no-v3",    action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--force-v3", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    end_time = datetime.now(timezone.utc)
    if args.start:
        start_time = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
        if args.end:
            end_time = datetime.fromisoformat(args.end.replace("Z", "+00:00"))
    elif args.last:
        start_time = end_time - parse_last(args.last)
    else:
        start_time = end_time - timedelta(minutes=20)

    from_ts = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    to_ts   = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    limit   = None if (args.fetch_all or args.count) else args.limit

    print(f"Time range: {from_ts} → {to_ts}")
    print(f"Limit:      {'all' if limit is None else limit}")
    print(f"API path:   GET /v1/agentops-v3/traces")
    print()

    base, token = _get_base_url_and_token()

    if args.save_ids:
        checkpoint_path = Path(args.save_ids)
    else:
        ts   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        DEFAULT_IDS_DIR.mkdir(parents=True, exist_ok=True)
        checkpoint_path = DEFAULT_IDS_DIR / f"traces_{ts}_ids.txt"

    t0 = time.monotonic()
    traces = search_all_traces(base, token, from_ts, to_ts, limit,
                               checkpoint_path=checkpoint_path)
    elapsed = time.monotonic() - t0

    # Final overwrite: deduplicated, ordered list — cleans up any duplicate IDs
    # that the per-page append could have written during a rate-limit retry.
    trace_ids = [
        tid for t in traces
        if (tid := t.get("traceId") or t.get("trace_id") or t.get("id"))
    ]
    checkpoint_path.write_text("\n".join(trace_ids) + "\n")

    if args.count:
        print(f"\nTotal traces: {len(traces)}  ({elapsed:.1f}s)")
        print(f"IDs saved to: {checkpoint_path}")
        return

    print(f"\nFound {len(traces)} trace(s) in {elapsed:.1f}s\n")
    if not traces:
        print("No traces found in this window.")
        return

    for i, t in enumerate(traces, 1):
        tid      = t.get("traceId") or t.get("trace_id") or t.get("id") or "?"
        duration = t.get("durationMs") or t.get("duration_ms") or t.get("duration") or "n/a"
        spans    = t.get("spanCount")  or t.get("span_count")  or "?"
        agents   = t.get("agentNames") or t.get("agent_names") or []
        agent_s  = ", ".join(agents) if isinstance(agents, list) else str(agents)
        dur_s = f"{duration}ms" if isinstance(duration, int) else str(duration)
        print(f"  [{i:>4}] {tid}  duration={dur_s:<10} spans={spans:<4} agents={agent_s}")

    print(f"\nTrace IDs saved to: {checkpoint_path}")
    print(f"\nTo export spans, run:")
    print(f"  python scripts/export_traces_agentops_v3.py --ids-file {checkpoint_path}")


if __name__ == "__main__":
    main()
