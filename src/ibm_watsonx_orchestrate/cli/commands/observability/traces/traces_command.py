import typer

from typing import Optional, List
from typing_extensions import Annotated
from datetime import datetime

from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller import trace_search, traces_export
from ibm_watsonx_orchestrate.cli.commands.observability.traces.types import SortField, SortDirection


traces_app = typer.Typer(no_args_is_help=True)

@traces_app.command(
    name="search",
    help="Search for traces using filters"
)
def search_traces(
    start_time: Annotated[
        datetime,
        typer.Option(
            "--start-time",
            help="Start time",
            show_default=False
        )
    ],
    end_time: Annotated[
        datetime,
        typer.Option(
            "--end-time",
            help="End time",
            show_default=False
        )
    ],
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
    include_root_spans: Annotated[
        bool,
        typer.Option(
            "--include-root-spans/--no-root-spans",
            help="Include root span data in results",
            show_default=True
        )
    ] = False,
    limit: Annotated[
        Optional[int],
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of traces to return (fetches all by default)",
            show_default=False
        )
    ] = None
):
    """
    Search for traces using various filters.
    
    This command allows you to find trace IDs based on criteria such as time range,
    service names, agent IDs/names, user IDs, session IDs, and span count.
    
    Once you find the trace IDs, you can use 'orchestrate observability traces export' to export the full trace data.
    
    Examples:
        # Search for traces in the last 24 hours
        orchestrate observability traces search --start-time 2025-07-20T00:00:00 --end-time 2025-07-20T23:59:59
        
        # Search by service and agent name
        orchestrate observability traces search  --start-time 2025-07-20T00:00:00 --end-time 2025-07-20T23:59:59 --service-name wxo-server --agent-name mobile-agent
        
        # Search by user ID
        orchestrate observability traces search --start-time 2025-07-20T00:00:00 --end-time 2025-07-20T23:59:59 --user-id user123
        
        # Search with span count filter
        orchestrate observability traces search  --start-time 2025-07-20T00:00:00 --end-time 2025-07-20T23:59:59 --min-spans 10 --max-spans 100
        
        # Limit results and include root span data
        orchestrate observability traces search  --start-time 2025-07-20T00:00:00 --end-time 2025-07-20T23:59:59 --limit 10 --include-root-spans
    
    Note:
        - This endpoint is only accessible to Admins
        - Rate limit: 4 requests per minute
        - Not available in on-premises offering
    """
    trace_search(start_time, end_time, service_names, agent_ids, agent_names, user_ids,
                session_ids, min_spans, max_spans, sort_field.value, sort_direction.value, include_root_spans, limit
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
    