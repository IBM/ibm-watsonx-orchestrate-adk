import re
import typer
import logging

from typing import Optional, List
from typing_extensions import Annotated
from datetime import datetime, timedelta, timezone

from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller import trace_search, traces_export
from ibm_watsonx_orchestrate.cli.commands.observability.traces.types import SortField, SortDirection

logger = logging.getLogger(__name__)


traces_app = typer.Typer(no_args_is_help=True)


def parse_last_duration(value: str) -> timedelta:
    """
    Parse a human-readable duration string into a :class:`datetime.timedelta`.

    Accepted formats (case-insensitive):
        Short  : ``30m``, ``3h``, ``10d``
        Long   : ``30 minutes``, ``3 hours``, ``10 days``
                 (singular forms ``minute``, ``hour``, ``day`` are also accepted)

    Returns:
        A :class:`datetime.timedelta` representing the duration.

    Raises:
        :class:`typer.BadParameter`: When the value cannot be parsed.
    """
    value = value.strip()
    # Match value to m/h/d or minutes/hours/days
    pattern = re.compile(
        r'^(\d+)\s*(m|h|d|minutes?|hours?|days?)$',
        re.IGNORECASE
    )
    match = pattern.match(value)
    if not match:
        raise typer.BadParameter(
            f"Invalid --last value '{value}'. "
            "Use formats like: 30m, 3h, 10d, 30 minutes, 3 hours, 10 days"
        )

    amount = int(match.group(1))
    unit = match.group(2).lower()

    if unit in ('m', 'minute', 'minutes'):
        return timedelta(minutes=amount)
    elif unit in ('h', 'hour', 'hours'):
        return timedelta(hours=amount)
    elif unit in ('d', 'day', 'days'):
        return timedelta(days=amount)
    else:
        raise typer.BadParameter(
            f"Unrecognized time unit '{unit}'. Use m/minutes, h/hours, or d/days."
        )


@traces_app.command(
    name="search",
    help="Search for traces using filters like session ID, user ID, time range, and sorting."
)
def search_traces(
    start_time: Annotated[
        Optional[datetime],
        typer.Option(
            "--start-time",
            help="Start time (ISO 8601 format). Required unless --last is used.",
            show_default=False
        )
    ] = None,
    end_time: Annotated[
        Optional[datetime],
        typer.Option(
            "--end-time",
            help="End time (ISO 8601 format). Required unless --last is used.",
            show_default=False
        )
    ] = None,
    last: Annotated[
        Optional[str],
        typer.Option(
            "--last",
            help=(
                "Shorthand for a relative time window ending now. "
                "Accepts minutes (30m / 30 minutes), hours (3h / 3 hours), "
                "or days (10d / 10 days). "
                "Mutually exclusive with --start-time / --end-time."
            ),
            show_default=False
        )
    ] = None,
    service_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--service-name",
            "-s",
            help="[DEPRECATED] Filter by service name - No longer supported",
            show_default=False
        )
    ] = None,
    agent_ids: Annotated[
        Optional[List[str]],
        typer.Option(
            "--agent-id",
            "-i",
            help="[DEPRECATED] Filter by agent ID - No longer supported",
            show_default=False
        )
    ] = None,
    agent_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--agent-name",
            "-a",
            help="[DEPRECATED] Filter by agent name - No longer supported",
            show_default=False
        )
    ] = None,
    user_ids: Annotated[
        Optional[List[str]],
        typer.Option(
            "--user-id",
            "-u",
            help="Filter by user ID (can be specified multiple times)",
            show_default=False
        )
    ] = None,
    session_ids: Annotated[
        Optional[List[str]],
        typer.Option(
            "--session-id",
            help="Filter by session ID (can be specified multiple times)",
            show_default=False
        )
    ] = None,
    min_spans: Annotated[
        Optional[int],
        typer.Option(
            "--min-spans",
            help="[DEPRECATED] Minimum number of spans - No longer supported",
            show_default=False
        )
    ] = None,
    max_spans: Annotated[
        Optional[int],
        typer.Option(
            "--max-spans",
            help="[DEPRECATED] Maximum number of spans - No longer supported",
            show_default=False
        )
    ] = None,
    sort_field: Annotated[
        SortField,
        typer.Option(
            "--sort-field",
            help="Field to sort by",
            show_default=True
        )
    ] = SortField.START_TIME,
    sort_direction: Annotated[
        SortDirection,
        typer.Option(
            "--sort-direction",
            help="Sort direction (asc or desc)",
            show_default=True
        )
    ] = SortDirection.DESC,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of traces",
            min=1,
            max=1000,
            show_default=True,
        )
    ] = 100,
):
    """
    Search for traces using various filters.

    You must supply either a relative time window via --last, or an explicit
    --start-time together with --end-time.

    SUPPORTED FILTERS:
        --session-id         Filter by session ID
        --user-id            Filter by user ID
        --start-time         Filter by start time (ISO 8601)
        --end-time           Filter by end time (ISO 8601)
        --last               Relative time window (e.g., 30m, 3h, 10d)
        --sort-field         Field to sort by (start_time, end_time)
        --sort-direction     Sort direction (asc or desc)
        --limit              Maximum number of results

      DEPRECATED FILTERS (will show warnings):
        --service-name       Service filtering no longer supported
        --agent-id           Agent filtering no longer supported
        --agent-name         Agent filtering no longer supported
        --min-spans          Span count filtering no longer supported
        --max-spans          Span count filtering no longer supported

    Once you find the trace IDs, you can use 'orchestrate observability traces export'
    to export the full trace data.

    Examples:
        # Search for traces in the last 30 minutes
        orchestrate observability traces search --last 30m

        # Search for traces in the last 3 hours
        orchestrate observability traces search --last 3h

        # Search for traces in the last 10 days
        orchestrate observability traces search --last 10d

        # Long-form duration values are also accepted
        orchestrate observability traces search --last "30 minutes"
        orchestrate observability traces search --last "3 hours"
        orchestrate observability traces search --last "10 days"

        # Explicit time range
        orchestrate observability traces search --start-time 2025-07-20T00:00:00 --end-time 2025-07-20T23:59:59

        # Search by service and agent name
        orchestrate observability traces search --last 1h --service-name wxo-server --agent-name mobile-agent

        # Search by user ID
        orchestrate observability traces search --last 1h --user-id user123

        # Search with span count filter
        orchestrate observability traces search --last 1h --min-spans 10 --max-spans 100

        # Limit results
        orchestrate observability traces search --last 1h --limit 10

    Note:
        - This endpoint is only accessible to Admins
        - Rate limit: 4 requests per minute
        - Not available in on-premises offering
        - Agent and service filtering are deprecated
    """
    if last is not None:
        if start_time is not None or end_time is not None:
            raise typer.BadParameter(
                "--last cannot be combined with --start-time or --end-time. "
                "Use one or the other."
            )
        delta = parse_last_duration(last)
        end_time = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        start_time = end_time - delta
    else:
        if start_time is None or end_time is None:
            raise typer.BadParameter(
                "You must provide either --last or both --start-time and --end-time."
            )

    # Show deprecation warnings for unsupported parameters only
    has_warnings = False

    if service_names:
        logger.warning(
            "Service name filtering (--service-name) is no longer supported. "
            "This filter will be ignored."
        )
        has_warnings = True

    if agent_ids or agent_names:
        logger.warning(
            "Agent filtering (--agent-id, --agent-name) is no longer supported. "
            "This filter will be ignored."
        )
        has_warnings = True

    if min_spans or max_spans:
        logger.warning(
            "Span count filtering (--min-spans, --max-spans) is no longer supported. "
            "This filter will be ignored."
        )
        has_warnings = True

    if has_warnings:
        logger.info(
            "💡 Tip: Use --session-id, --user-id, or time filters (--start-time, --end-time, --last) for filtering."
        )

    trace_search(
        start_time=start_time,
        end_time=end_time,
        service_names=service_names,
        agent_ids=agent_ids,
        agent_names=agent_names,
        user_ids=user_ids,
        session_ids=session_ids,
        min_spans=min_spans,
        max_spans=max_spans,
        sort_field=sort_field.value,
        sort_direction=sort_direction.value,
        page_size=limit
    )

@traces_app.command(
    name="export",
    help="Export trace observations from the observability platform"
)
def export_trace(
    trace_id: Annotated[
        str,
        typer.Option(
            "--trace-id",
            "-t",
            help="Trace ID to export (32-character hexadecimal string)",
            show_default=False
        )
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            "--output",
            "-o",
            help="Output file path. If not specified, prints to stdout",
            show_default=False
        )
    ] = None,
    pretty: Annotated[
        bool,
        typer.Option(
            "--pretty/--no-pretty",
            help="Pretty-print JSON for saving in output files with --output/-o flag",
            show_default=True
        )
    ] = True
):
    """
    Export trace observations from the Watson Orchestrate observability platform.

    This command fetches all observations for a given trace ID and exports them
    to a file or stdout in JSON format.

    Examples:
        # Print to stdout
        orchestrate observability traces export -t 1234567890abcdef1234567890abcdef

        # Pipe to jq for processing
        orchestrate observability traces export -t 1234567890abcdef1234567890abcdef | jq '.observations | length'

        # Export to JSON file
        orchestrate observability traces export --trace-id 1234567890abcdef1234567890abcdef --output trace.json

    Note:
        - This endpoint is only accessible to Admins
        - Rate limit: 4 requests per minute
        - Trace ID must be a 32-character hexadecimal string
    """
    traces_export(trace_id, output, pretty)
