import logging
import os
import pprint
import typer
import rich

from datetime import datetime
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, Table

from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_exporters import TraceExporter
from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper import resolve_agent_names_to_ids
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.client.observability.traces import TraceFilters, TraceSort, SpanCountRange
from ibm_watsonx_orchestrate.client.observability.traces.traces_client import (
    TracesClient,
    SpansResponse,
    TraceSearchResponse,
    TraceFilters,
    TraceSort
)
from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.docker_utils import get_container_env_var


logger = logging.getLogger(__name__)
console = Console()


class TracesController:
    """
    Controller for trace operations.
    
    This controller provides methods to search, fetch and export traces.
    
    Example:
        ```python
        # For CLI commands
        controller = TracesController()
        spans = controller.fetch_trace_spans("abc123...")
        
        # For custom scripts
        from ibm_watsonx_orchestrate.cli.commands.traces.traces_controller import TracesController
        
        controller = TracesController()
        spans = controller.fetch_trace_spans("abc123...")
        # Process spans programmatically
        errors = [s for s in spans.spans if s.status.status_code == "ERROR"]
        ```
    """
    
    def __init__(self):
        self.client: Optional[TracesClient] = None
    
    def get_client(self) -> TracesClient:
        """Get or create TracesClient instance."""
        if not self.client:
            self.client = instantiate_client(TracesClient)
            
            # For local dev, set the API key from Docker container or environment
            if hasattr(self.client, '_is_local') and self.client._is_local:
                
                api_key = get_container_env_var("dev-edition-wxo-builder-1", "AGENT_OPS_API_KEY")
                self.client._local_api_key = api_key
        
        return self.client
    
    def fetch_trace_spans(
        self,
        trace_id: str,
        page_size: int = 100,
        fetch_all: bool = True,
        show_progress: bool = False
    ) -> SpansResponse:
        """
        Fetch all spans for a given trace ID.
        
        This method fetches spans from the API and returns the SpansResponse object.
        
        Args:
            trace_id: Trace ID (32-character hexadecimal string)
            page_size: Number of spans per page (1-1000)
            fetch_all: If True, automatically fetches all pages
            show_progress: If True, log progress (for CLI use)
        
        Returns:
            SpansResponse containing spans and pagination info
        
        Raises:
            ClientAPIException: If the API request fails
            ValueError: If trace_id format is invalid
        
        Example:
            ```python
            controller = TracesController()
            spans = controller.fetch_trace_spans("abc123...")
            print(f"Fetched {len(spans.spans)} spans")
            ```
        """
        if show_progress:
            logger.info(f"Fetching spans for trace {trace_id[:8]}...")
        
        client = self.get_client()
        spans_response = client.get_spans(
            trace_id=trace_id,
            page_size=page_size,
            fetch_all=fetch_all
        )
        
        if show_progress:
            logger.info(f"Fetched {len(spans_response.spans)} spans")
        
        return spans_response
    
    def export_trace_to_json(
        self,
        trace_id: str,
        output_file: Optional[str] = None,
        pretty: bool = True,
        page_size: int = 50
    ) -> tuple[SpansResponse, str]:
        """
        Fetch trace spans and export to JSON format.
        
        Args:
            trace_id: Trace ID (32-character hexadecimal string)
            output_file: Optional file path to write to
            pretty: If True, format with indentation
            page_size: Number of spans per page
        
        Returns:
            Tuple of (SpansResponse, json_string)
            - SpansResponse: The fetched spans (for programmatic use)
            - json_string: The JSON export (for CLI and output file)
        
        Raises:
            ClientAPIException: If the API request fails
            ValueError: If trace_id format is invalid
        
        Example:
            ```python
            controller = TracesController()
            spans, json_str = controller.export_trace_to_json(
                "abc123...",
                output_file="trace.json"
            )
            # Use spans object for analysis
            errors = [s for s in spans.spans if s.status.status_code == "ERROR"]
            ```
        """
        spans_response = self.fetch_trace_spans(
            trace_id=trace_id,
            page_size=page_size,
            fetch_all=True
        )
        
        # Export to JSON
        exporter = TraceExporter()
        json_str = exporter.export_to_json(
            spans_response,
            output_file=output_file,
            pretty=pretty
        )
        
        return spans_response, json_str
        
    def search_traces(
        self,
        filters: Optional[TraceFilters] = None,
        sort: Optional[TraceSort] = None,
        page_size: int = 100,
        show_progress: bool = False
    ) -> TraceSearchResponse:
        """
        Search for traces using filters.
        
        This method searches for traces based on various criteria such as
        time range, service names, agent IDs, agent names, user IDs, session IDs, and span count.
        
        Args:
            filters: TraceFilters object with search criteria
            sort: TraceSort object for sorting results
            page_size: Number of results per page (1-1000)
            show_progress: If True, log progress (for CLI use)
        
        Returns:
            TraceSearchResponse containing trace summaries and pagination info
        
        Raises:
            ClientAPIException: If the API request fails
            ValueError: If parameters are invalid
        
        Example:
            ```python
            from ibm_watsonx_orchestrate.client.traces.traces_client import TraceFilters, TraceSort
            
            controller = TracesController()
            
            # Search by time range
            filters = TraceFilters(
                start_time="2026-01-26T00:00:00.000Z",
                end_time="2026-01-27T23:59:59.000Z"
            )
            
            results = controller.search_traces(filters=filters)
            print(f"Found {len(results.traceSummaries)} traces")
            
            # Search by time range and agent name
            filters = TraceFilters(
                start_time="2026-01-26T00:00:00.000Z",
                end_time="2026-01-27T23:59:59.000Z",
                agent_names=["AskOrchestrate"]
            )
            
            results = controller.search_traces(filters=filters)
            for trace in results.traceSummaries:
                print(f"Trace: {trace.traceId}, Agent: {trace.agentNames[0]}")
            
            # Search with sorting and root spans
            filters = TraceFilters(
                start_time="2026-01-26T00:00:00.000Z",
                end_time="2026-01-27T23:59:59.000Z"
            )
            sort = TraceSort(field="start_time", direction="desc")
            
            results = controller.search_traces(
                filters=filters,
                sort=sort,
            )
            ```
        """
        if show_progress:
            logger.info("Searching for traces...")
        
        client = self.get_client()
        search_response = client.search_traces(
            filters=filters,
            sort=sort,
            page_size=page_size,
        )
        
        if show_progress:
            logger.info(f"Found {len(search_response.traces)} traces")
        
        return search_response


def trace_search (  start_time: datetime,
                    end_time: datetime,
                    service_names: Optional[List[str]] = None,
                    agent_ids: Optional[List[str]] = None,
                    agent_names: Optional[List[str]] = None,
                    user_ids: Optional[List[str]] = None,
                    session_ids: Optional[List[str]] = None,
                    min_spans: Optional[int] = None,
                    max_spans: Optional[int] = None,
                    sort_field: str = "start_time",
                    sort_direction: str = "desc",
                    page_size: int = 100,
                    ):
        try:
            # Validate sort_field (API bug: only start_time works, end_time causes 500 error)
            if sort_field == "end_time":
                logger.warning("Sorting by 'end_time' is not currently supported by the API backend.")
                logger.warning("Falling back to 'start_time' sorting instead.")
                sort_field = "start_time"
            # Resolve agent names to IDs, should be removed when API bug is fixed
            resolved_agent_ids = resolve_agent_names_to_ids(agent_names, agent_ids)
            
            # For local development with FORCE_SINGLE_TENANT=true, service_name is required, defaulting to "wxo-server" if not provided
            try:
                if is_local_dev() and (not service_names or len(service_names) == 0):
                    logger.info("Local development detected: defaulting to service_name='wxo-server'")
                    service_names = ["wxo-server"]
            except (KeyError, AttributeError): # In test environments or when config is not set up, skip local dev check
                pass
            
            span_count_range = None
            if min_spans is not None or max_spans is not None:
                span_count_range = SpanCountRange(min=min_spans, max=max_spans)
            filters = TraceFilters(
                start_time=start_time,
                end_time=end_time,
                service_names=service_names,
                agent_ids=resolved_agent_ids,
                agent_names=None,
                user_id=user_ids,
                session_ids=session_ids,
                span_count_range=span_count_range
            )
            
            sort = TraceSort(field=sort_field, direction=sort_direction)
            
            controller = TracesController()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                # Set progress on client so it can stop spinner before logging
                controller.get_client().progress = progress
                task = progress.add_task("Searching for traces...", total=None)
                
                search_response = controller.search_traces(
                    filters=filters,
                    sort=sort,
                    page_size=page_size,
                )
                
                progress.update(task, description=f"Found {len(search_response.traceSummaries)} traces")
            
            if not search_response.traceSummaries:
                logger.warning("No traces found matching the criteria")
                return
            
            traces_to_display = search_response.traceSummaries
            
            # Display results in a table
            table = Table(title=f"Found {len(search_response.traceSummaries)} traces")
            table.add_column("Trace ID", no_wrap=True)
            table.add_column("Start Time")
            table.add_column("Duration (ms)")
            table.add_column("Spans")
            table.add_column("Agent Name")
            table.add_column("Agent ID")
            table.add_column("User ID")
            
            for trace in traces_to_display:
                # Handle both list and single value for agent_names, agent_ids, and user_ids
                agent_name = trace.agentNames[0] if trace.agentNames else "-"
                agent_id = trace.agentIds[0] if trace.agentIds else "-"
                user_id = trace.userIds[0] if trace.userIds else "-"
                
                table.add_row(
                    trace.traceId,
                    trace.startTime[:19],  # Show date and time only
                    str(trace.durationMs),
                    str(trace.spanCount),
                    agent_name,
                    agent_id,
                    user_id
                )
            
            console.print()
            console.print(table)
            console.print()
            
            if traces_to_display: # Show tip for exporting
                logger.info("Tip: Use 'orchestrate observability traces export --trace-id <TRACE_ID>' to export full trace data")
        
        except ClientAPIException as e:
            status_code = e.response.status_code
            error_messages = {
                400: "Invalid request parameters. Check your filter values.",
                401: "Authentication failed. Missing or invalid tenant.id header.",
                429: "Rate limit exceeded. Maximum 4 requests per minute. Please wait and try again.",
                500: "Internal server error. Please try again later."
            }
            
            error_msg = error_messages.get(status_code, f"API error (status {status_code})")
            logger.error(f"Error: {error_msg}")
            
            if status_code == 429:
                logger.info("Tip: Wait at least 15 seconds before retrying")
            
            logger.error(f"API error: {e}")
            raise typer.Exit(1)
            
        except ValueError as e:
            logger.error(f"Error: {str(e)}")
            raise typer.Exit(1)
        
        except Exception as e:
            logger.error(f"Unexpected error during trace search: {str(e)}")
            raise typer.Exit(1)

def traces_export(trace_id: str, output: Optional[str] = None, pretty: bool = True):

    try:
        if not trace_id or len(trace_id) != 32:
            logger.error("Error: trace_id must be a 32-character hexadecimal string")
            raise typer.Exit(1)

        if output and not output.lower().endswith('.json'): # check json output file
            logger.warning(f"Output file '{output}' must have .json extension. Displaying output to stdout")
            output=None
        
        if not output and not pretty:
            logger.warning("--no-pretty can only be used when exporting to a file using --output/-o")
        
        controller = TracesController()
        
        if output: # Show progress only if outputting to file
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Fetching spans for trace {trace_id[:8]}...", total=None)
                spans_response, json_str = controller.export_trace_to_json(
                    trace_id=trace_id,
                    output_file=output,
                    pretty=pretty,
                )
                
                if spans_response.spans:
                    progress.update(task, description=f"Fetched {len(spans_response.spans)} spans")
                elif spans_response.traceData:
                    progress.update(task, description=f"Fetched trace data")
        else: # Fetch without progress bar when outputting to stdout
            spans_response, json_str = controller.export_trace_to_json(
                trace_id=trace_id,
                output_file=output,
                pretty=pretty,
            )
        
        if not spans_response.spans and not spans_response.traceData: # Check if we have any data
            logger.warning(f"No trace data found for trace ID {trace_id}")
            return
        
        # Display success message or output to stdout
        if output:
            if spans_response.spans:
                logger.info(f"Successfully exported {len(spans_response.spans)} spans to {output}")
            elif spans_response.traceData:
                logger.info(f"Successfully exported trace data to {output}")
            logger.info(f"Trace ID: {trace_id}")
            if spans_response.totalCount:
                logger.info(f"  Total spans in trace: {spans_response.totalCount}")
        else:
            rich.print_json(json_str)
    
    except ClientAPIException as e:
        status_code = e.response.status_code
        error_messages = {
            400: "Invalid request parameters. Check that trace_id is a valid 32-character hex string.",
            401: "Authentication failed. Missing or invalid tenant.id header.",
            404: f"Trace ID '{trace_id}' not found.",
            429: "Rate limit exceeded. Maximum 4 requests per minute. Please wait and try again.",
            500: "Internal server error. Please try again later."
        }
        
        error_msg = error_messages.get(status_code, f"API error (status {status_code})")
        logger.error(f"Error: {error_msg}")
        
        if status_code == 429:
            logger.info("Tip: Wait at least 15 seconds before retrying")
        
        logger.error(f"API error: {e}")
        raise typer.Exit(1)
    
    except ValueError as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(1)
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise typer.Exit(1)
