#!/usr/bin/env python3
"""
Search traces for a given agent, with full cursor-based pagination and automatic
429 rate-limit retry.

Usage:
    # Search traces from the last 20 minutes (default)
    python scripts/search_traces_adk.py --agent-name "My Agent"

    # Search by agent ID instead of name
    python scripts/search_traces_adk.py --agent-id <UUID>

    # Search traces from the last N hours / days / minutes
    python scripts/search_traces_adk.py --agent-name "My Agent" --last 6h
    python scripts/search_traces_adk.py --agent-name "My Agent" --last 3d
    python scripts/search_traces_adk.py --agent-name "My Agent" --last 30m

    # Search with an explicit time range
    python scripts/search_traces_adk.py --agent-name "My Agent" \
        --start 2025-01-01T00:00:00Z --end 2025-01-02T00:00:00Z

    # Collect all traces in the window (no limit)
    python scripts/search_traces_adk.py --agent-name "My Agent" --all

    # Only print the total trace count (no per-trace details)
    python scripts/search_traces_adk.py --agent-name "My Agent" --last 30d --count

    # Save discovered trace IDs to a file for use with export_traces_adk.py
    python scripts/search_traces_adk.py --agent-name "My Agent" --save-ids data/trace_ids.txt

Prerequisites:
    - A watsonx Orchestrate environment must be active:
          orchestrate env activate <env-name>
      For local dev, the server must be started with the IBM telemetry profile:
          orchestrate server start --with-ibm-telemetry --accept-terms-and-conditions
    - Virtual environment: venv/bin/activate
    - Environment variables: .env (loaded automatically)

Rate limiting:
    The traces search API is limited to 4 requests per minute.  The script
    automatically reads the ``retry_after`` value from 429 responses and waits
    before retrying — no manual time-window slicing needed.
"""

import argparse
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Walk up from this file to find the repo root (directory containing .git),
# then load .env from there.
def _find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return start  # fallback: use the start directory if .git not found

_repo_root = _find_repo_root(Path(__file__).resolve().parent)
_env_file = _repo_root / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file)

from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller import TracesController
from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper import resolve_agent_names_to_ids
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.client.observability.traces import TraceFilters, TraceSort
from ibm_watsonx_orchestrate.client.utils import is_local_dev

DEFAULT_AGENT_NAME = "My Agent"
PAGE_SIZE = 100  # maximum the API accepts
DEFAULT_IDS_DIR = Path(__file__).resolve().parent.parent / "data"


def _bar(done: int, total: int | None, label: str = "", width: int = 40) -> None:
    """Print an in-place progress bar.  When *total* is unknown, shows a spinner."""
    if total:
        filled = int(width * done / total)
        bar = "█" * filled + "░" * (width - filled)
        pct = done / total * 100
        line = f"\r  [{bar}] {pct:5.1f}%  {done}/{total}  {label}"
    else:
        spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[done % 10]
        line = f"\r  {spinner}  {done} traces fetched  {label}"
    sys.stdout.write(line)
    sys.stdout.flush()


def parse_last(value: str) -> timedelta:
    """Parse a shorthand like '6h', '3d', '30m' into a timedelta."""
    match = re.fullmatch(r"(\d+)\s*(m|h|d|minutes?|hours?|days?)", value.strip(), re.IGNORECASE)
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid --last value '{value}'. Use e.g. 30m, 6h, 3d."
        )
    n, unit = int(match.group(1)), match.group(2).lower()
    if unit.startswith("m"):
        return timedelta(minutes=n)
    if unit.startswith("h"):
        return timedelta(hours=n)
    return timedelta(days=n)


def _get_client():
    return TracesController().get_client()


def _post_with_retry(client_ref: list, body: dict, page: int) -> dict:
    """POST with automatic retry on 429 (rate-limit) and 401 (token expiry)."""
    while True:
        client = client_ref[0]
        endpoint = f"{client.base_endpoint}/search"
        try:
            return client._post(endpoint, data=body)
        except ClientAPIException as exc:
            if exc.response.status_code == 429:
                resp_body = exc.response.json()
                retry_after_str = resp_body.get("retry_after", "60s")
                seconds = int(re.search(r"\d+", retry_after_str).group())
                sys.stdout.write(f"\n  Rate limited — waiting {seconds}s before retrying page {page}...\n")
                sys.stdout.flush()
                time.sleep(seconds + 1)
            elif exc.response.status_code == 401:
                sys.stdout.write(f"\n  401 token expired — refreshing client and retrying page {page}...\n")
                sys.stdout.flush()
                time.sleep(2)
                client_ref[0] = _get_client()
            else:
                raise


def search_all_traces(
    client_ref: list,
    filters: TraceFilters,
    sort: TraceSort,
    limit: int | None,
    checkpoint_path: Path | None = None,
) -> list[dict]:
    """
    Paginate through the traces search API using cursor-based pagination,
    retrying automatically on 429 rate-limit and 401 token-expiry errors.

    Appends discovered trace IDs to *checkpoint_path* after every page so
    progress is never lost on timeout or interruption.

    Returns a flat list of raw traceSummary dicts.  Stops when:
      - ``nextCursor`` is absent/null (last page), or
      - ``limit`` traces have been collected (when limit is not None).
    """
    summaries: list[dict] = []
    cursor = None
    page = 0

    # Seed checkpoint file (create/truncate) so it exists from the first page
    if checkpoint_path:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text("")

    while True:
        page += 1
        page_size = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - len(summaries))

        request_body = {
            "filters": filters.model_dump(exclude_none=True),
            "sort": sort.model_dump(exclude_none=True),
            "page_size": page_size,
            "include_root_spans": False,
        }
        if cursor is not None:
            request_body["cursor"] = cursor
        raw = _post_with_retry(
            client_ref,
            request_body,
            page,
        )

        batch = raw.get("traceSummaries", [])
        summaries.extend(batch)
        cursor = raw.get("nextCursor")

        # Append new IDs to checkpoint file immediately after each page
        if checkpoint_path and batch:
            with checkpoint_path.open("a") as f:
                for t in batch:
                    f.write(t["traceId"] + "\n")

        _bar(len(summaries), limit, label=f"page {page}")

        reached_limit = limit is not None and len(summaries) >= limit
        if not cursor or not batch or reached_limit:
            break

    sys.stdout.write("\n")
    sys.stdout.flush()
    return summaries


def main():
    parser = argparse.ArgumentParser(
        description="Search traces for a watsonx Orchestrate agent (paginated, rate-limit aware)"
    )
    agent_group = parser.add_mutually_exclusive_group()
    agent_group.add_argument(
        "--agent-name", metavar="NAME", default=DEFAULT_AGENT_NAME,
        help=f"Agent name to filter by (default: {DEFAULT_AGENT_NAME!r})"
    )
    agent_group.add_argument(
        "--agent-id", metavar="UUID",
        help="Agent UUID to filter by (skips name-to-ID resolution)"
    )
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument(
        "--last", metavar="WINDOW",
        help="Relative time window ending now, e.g. 6h, 3d, 30m. Default: 20m"
    )
    time_group.add_argument(
        "--start", metavar="ISO8601",
        help="Explicit start time (ISO 8601 UTC, e.g. 2025-01-01T00:00:00Z)"
    )
    parser.add_argument(
        "--end", metavar="ISO8601",
        help="Explicit end time (ISO 8601 UTC). Requires --start."
    )

    limit_group = parser.add_mutually_exclusive_group()
    limit_group.add_argument(
        "--limit", type=int, default=50,
        help="Maximum number of traces to return (default: 50)"
    )
    limit_group.add_argument(
        "--all", dest="fetch_all", action="store_true",
        help="Fetch every trace in the window (ignores --limit, paginates until exhausted)"
    )

    parser.add_argument(
        "--count", action="store_true",
        help="Print only the total trace count; implies --all (no per-trace output)"
    )
    parser.add_argument(
        "--save-ids", metavar="FILE",
        help="Save discovered trace IDs (one per line) to this file. "
             "Defaults to data/<agent>_<YYYYMMDD_HHMM>_ids.txt when omitted."
    )
    args = parser.parse_args()

    # Resolve agent identity
    if args.agent_id:
        agent_name = None
        agent_ids = [args.agent_id]
    else:
        agent_name = args.agent_name
        # Resolve agent name → agent ID (works around an API bug where agent_names
        # filtering may not work on some tenants; mirrors what the CLI does).
        agent_ids = resolve_agent_names_to_ids(agent_names=[agent_name], agent_ids=None)

    display_agent = args.agent_id if args.agent_id else agent_name

    # Resolve time window
    end_time = datetime.now(timezone.utc)
    if args.start:
        start_time = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
        if args.end:
            end_time = datetime.fromisoformat(args.end.replace("Z", "+00:00"))
    elif args.last:
        start_time = end_time - parse_last(args.last)
    else:
        start_time = end_time - timedelta(minutes=20)

    limit = None if (args.fetch_all or args.count) else args.limit

    print(f"Agent:      {display_agent}")
    print(f"Time range: {start_time.strftime('%Y-%m-%d %H:%M UTC')} → {end_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Limit:      {'all' if limit is None else limit}")
    print()

    # Local dev requires service_names when FORCE_SINGLE_TENANT=true; not needed on SaaS.
    service_names = ["wxo-server"] if is_local_dev() else None

    filters = TraceFilters(
        start_time=start_time.isoformat().replace("+00:00", "Z"),
        end_time=end_time.isoformat().replace("+00:00", "Z"),
        service_names=service_names,
        agent_ids=agent_ids or None,
        agent_names=[agent_name] if agent_name else None,
    )
    sort = TraceSort(field="start_time", direction="desc")

    t0 = time.monotonic()
    # Always checkpoint IDs page-by-page so progress survives an API rate-limit abort.
    # Use the explicit --save-ids path if given, otherwise auto-generate one.
    if args.save_ids:
        checkpoint_path = Path(args.save_ids)
    else:
        safe_agent = re.sub(r"[^\w-]", "_", display_agent or "agent")
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        DEFAULT_IDS_DIR.mkdir(parents=True, exist_ok=True)
        checkpoint_path = DEFAULT_IDS_DIR / f"{safe_agent}_{ts}_ids.txt"

    try:
        client_ref = [_get_client()]
        summaries = search_all_traces(client_ref, filters, sort, limit,
                                      checkpoint_path=checkpoint_path)
    except ClientAPIException as e:
        elapsed = time.monotonic() - t0
        print(f"ERROR: API call failed ({e.response.status_code}): {e}  ({elapsed:.1f}s)", file=sys.stderr)
        sys.exit(1)
    elapsed = time.monotonic() - t0

    if args.count:
        print(f"\nTotal traces: {len(summaries)}  ({elapsed:.1f}s)")
        print(f"Trace IDs saved to: {checkpoint_path}")
        sys.exit(0)

    print(f"\nFound {len(summaries)} trace(s) in {elapsed:.1f}s\n")

    if not summaries:
        print("No traces found. Make sure the environment is active and the agent has been invoked.")
        sys.exit(0)

    trace_ids = []
    for i, trace in enumerate(summaries, 1):
        trace_id = trace["traceId"]
        trace_ids.append(trace_id)
        duration = f"{trace.get('durationMs')}ms" if trace.get("durationMs") else "n/a"
        span_count = trace.get("spanCount") or 0
        agent_names = trace.get("agentNames") or []
        agents = ", ".join(agent_names) if agent_names else "n/a"
        print(f"  [{i:>4}] {trace_id}  duration={duration:<10} spans={span_count:<4} agents={agents}")

    # Final write: overwrite with the complete ordered list (deduplicates any
    # partial page written during a rate-limit retry).
    checkpoint_path.write_text("\n".join(trace_ids) + "\n")
    print(f"\nTrace IDs saved to: {checkpoint_path}")

    print(f"\nTo export spans for a trace, run:")
    print(f"  python scripts/export_traces_adk.py --trace-id <TRACE_ID>")
    print(f"  python scripts/export_traces_adk.py --ids-file {checkpoint_path}")


if __name__ == "__main__":
    main()
