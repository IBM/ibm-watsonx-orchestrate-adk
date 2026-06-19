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
            f"Unrecognised time unit '{unit}'. Use m/minutes, h/hours, or d/days."
        )


@traces_app.command(
    name="search",
    help="Search for traces. Note: With agentops-v3 API, only --session-id and --user-id filters are fully supported."
)
def search_traces(
    start_time: Annotated[
        Optional[datetime],
        typer.Option(
            "--start-time",
            help="Start time (ISO 8601). Required unless --last is used.",
            show_default=False
        )
    ] = None,
    end_time: Annotated[
        Optional[datetime],
        typer.Option(
            "--end-time",
            help="End time (ISO 8601). Required unless --last is used.",
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
            help="Filter by service name (can be specified multiple times)",
            show_default=False
        )
    ] = None,
    agent_ids: Annotated[
        Optional[List[str]],
        typer.Option(
            "--agent-id",
            "-i",
            help="Filter by agent ID (can be specified multiple times)",
            show_default=False
        )
    ] = None,
    agent_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--agent-name",
            "-a",
            help="Filter by agent name (can be specified multiple times)",
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
            help="Minimum number of spans in trace",
            show_default=False
        )
    ] = None,
    max_spans: Annotated[
        Optional[int],
        typer.Option(
            "--max-spans",
            help="Maximum number of spans in trace",
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
            help="Sort direction",
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

    This command allows you to find trace IDs based on criteria such as time range,
    service names, agent IDs/names, user IDs, session IDs, and span count.

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
    
    # Show deprecation warnings for unsupported parameters in agentops-v3 API
    warnings_shown = []
    
    if start_time or end_time or last:
        logger.warning(
            "⚠️  Time filtering (--start-time, --end-time, --last) is not supported by agentops-v3 API. "
            "All traces will be returned regardless of time range."
        )
        warnings_shown.append("time filtering")
    
    if service_names:
        logger.warning(
            "⚠️  Service name filtering (--service-name) is not supported by agentops-v3 API. "
            "This filter will be ignored."
        )
        warnings_shown.append("service filtering")
    
    if agent_ids or agent_names:
        logger.warning(
            "⚠️  Agent filtering (--agent-id, --agent-name) is not supported by agentops-v3 API. "
            "This filter will be ignored."
        )
        warnings_shown.append("agent filtering")
    
    if min_spans or max_spans:
        logger.warning(
            "⚠️  Span count filtering (--min-spans, --max-spans) is not supported by agentops-v3 API. "
            "This filter will be ignored."
        )
        warnings_shown.append("span count filtering")
    
    if sort_field != SortField.START_TIME or sort_direction != SortDirection.DESC:
        logger.warning(
            "⚠️  Custom sorting (--sort-field, --sort-direction) is not supported by agentops-v3 API. "
            "Results will be returned in default order."
        )
        warnings_shown.append("sorting")
    
    if warnings_shown:
        logger.info(
            f"💡 Tip: Use --session-id or --user-id for filtering with the new API. "
            f"Unsupported features: {', '.join(warnings_shown)}"
        )

    trace_search(start_time, end_time, service_names, agent_ids, agent_names, user_ids,
                session_ids, min_spans, max_spans, sort_field=sort_field.value, sort_direction=sort_direction.value, page_size=limit
                )

@traces_app.command(
    name="export",
    help="Export trace spans from the observability platform"
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
    Export trace spans from the Watson Orchestrate observability platform.
    
    This command fetches all spans for a given trace ID and exports them to
    a file or stdout in JSON format (OpenTelemetry-compliant).
    
    The JSON output is compatible with trace analysis tools like Jaeger, Zipkin,
    and can be piped to tools like jq for processing in CI/CD pipelines.
    
    Examples:
        # Print to stdout
        orchestrate observability traces export -t 1234567890abcdef1234567890abcdef
        
        # Pipe to jq for processing
        orchestrate observability traces export -t 1234567890abcdef1234567890abcdef | jq '.traceData.resourceSpans[0].scopeSpans[0].spans | length'

        # Export to JSON file
        orchestrate observability traces export --trace-id 1234567890abcdef1234567890abcdef --output trace.json
          
    Note:
        - This endpoint is only accessible to Admins
        - Rate limit: 4 requests per minute
        - Trace ID must be a 32-character hexadecimal string
    """
    traces_export(trace_id, output, pretty)
    