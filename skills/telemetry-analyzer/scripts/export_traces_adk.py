#!/usr/bin/env python3
"""
Export trace spans for a given agent to JSON files.

Usage:
    # Export a single trace by ID
    python scripts/export_traces_adk.py --trace-id <32-char-hex-id>

    # Export multiple trace IDs from a file (one ID per line)
    python scripts/export_traces_adk.py --ids-file data/trace_ids.txt

    # Specify which agent the traces belong to (for display only)
    python scripts/export_traces_adk.py --trace-id <id> --agent-name "My Agent"
    python scripts/export_traces_adk.py --trace-id <id> --agent-id <UUID>

    # Change output directory (default: data/)
    python scripts/export_traces_adk.py --trace-id <id> --output-dir data

    # Compact JSON (not pretty-printed)
    python scripts/export_traces_adk.py --trace-id <id> --no-pretty

Prerequisites:
    - A watsonx Orchestrate environment must be active:
          orchestrate env activate <env-name>
    - Virtual environment: venv/bin/activate
    - Environment variables: .env (loaded automatically)

Tip: Use search_traces_adk.py --save-ids to discover trace IDs first.
"""

import argparse
import sys
import time
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
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException

def _make_controller() -> TracesController:
    return TracesController()

DEFAULT_AGENT_NAME = "Supervisor"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"


def _bar(done: int, total: int, succeeded: int, failed: int, width: int = 40) -> None:
    """Overwrite the current terminal line with an export progress bar."""
    filled = int(width * done / total) if total else 0
    bar = "█" * filled + "░" * (width - filled)
    pct = done / total * 100 if total else 0
    line = f"\r  [{bar}] {pct:5.1f}%  {done}/{total}  ✓{succeeded}  ✗{failed}"
    sys.stdout.write(line)
    sys.stdout.flush()


def export_trace(controller: TracesController, trace_id: str, output_dir: Path, pretty: bool) -> bool:
    """Export a single trace to a JSON file. Returns True on success."""
    trace_id = trace_id.strip()
    if not trace_id:
        return False

    output_file = output_dir / f"{trace_id}.json"
    t0 = time.monotonic()
    try:
        spans_response, _ = controller.export_trace_to_json(
            trace_id=trace_id,
            output_file=str(output_file),
            pretty=pretty,
        )
        elapsed = time.monotonic() - t0

        # Collect span detail for the summary line printed after the bar clears
        if spans_response.traceData and spans_response.traceData.resourceSpans:
            n_spans = sum(
                len(ss.get("spans", []))
                for rs in spans_response.traceData.resourceSpans
                for ss in rs.get("scopeSpans", [])
            )
            export_trace._last_detail = f"{n_spans} spans, OTel, {elapsed:.1f}s"
        elif spans_response.spans:
            export_trace._last_detail = f"{len(spans_response.spans)} spans, legacy, {elapsed:.1f}s"
        else:
            export_trace._last_detail = f"no span data, {elapsed:.1f}s"

        return True

    except ValueError as e:
        elapsed = time.monotonic() - t0
        export_trace._last_detail = f"FAILED: {e}, {elapsed:.1f}s"
        return False
    except ClientAPIException as e:
        elapsed = time.monotonic() - t0
        export_trace._last_detail = f"FAILED: HTTP {e.response.status_code}, {elapsed:.1f}s"
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Export trace spans for a watsonx Orchestrate agent"
    )

    agent_group = parser.add_mutually_exclusive_group()
    agent_group.add_argument(
        "--agent-name", metavar="NAME", default=DEFAULT_AGENT_NAME,
        help=f"Agent name (for display only, default: {DEFAULT_AGENT_NAME!r})"
    )
    agent_group.add_argument(
        "--agent-id", metavar="UUID",
        help="Agent UUID (for display only)"
    )

    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument(
        "--trace-id", metavar="TRACE_ID",
        help="A single 32-character hexadecimal trace ID to export"
    )
    id_group.add_argument(
        "--ids-file", metavar="FILE",
        help="Path to a file containing trace IDs, one per line"
    )

    parser.add_argument(
        "--output-dir", metavar="DIR", default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory to write JSON files into (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--no-pretty", action="store_true",
        help="Write compact (non-indented) JSON"
    )
    args = parser.parse_args()

    display_agent = args.agent_id if args.agent_id else args.agent_name

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect trace IDs
    if args.trace_id:
        trace_ids = [args.trace_id]
    else:
        ids_file = Path(args.ids_file)
        if not ids_file.exists():
            print(f"ERROR: IDs file not found: {ids_file}", file=sys.stderr)
            sys.exit(1)
        trace_ids = [line.strip() for line in ids_file.read_text().splitlines() if line.strip()]

    if not trace_ids:
        print("No trace IDs found. Nothing to export.")
        sys.exit(0)

    print(f"Agent:      {display_agent}")
    print(f"Output dir: {output_dir}")
    print(f"Traces:     {len(trace_ids)}")
    print()

    controller = _make_controller()
    succeeded, failed = 0, 0
    wall_start = time.monotonic()
    total = len(trace_ids)

    _bar(0, total, succeeded, failed)
    for trace_id in trace_ids:
        ok = export_trace(controller, trace_id, output_dir, pretty=not args.no_pretty)
        if ok:
            succeeded += 1
        else:
            failed += 1
        _bar(succeeded + failed, total, succeeded, failed)

    sys.stdout.write("\n")
    sys.stdout.flush()
    total_elapsed = time.monotonic() - wall_start
    print(f"Done. {succeeded} exported, {failed} failed.  Total time: {total_elapsed:.1f}s")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
