import logging

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer, ConfigDict

from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient

logger = logging.getLogger(__name__)

# Constants
MAX_PAGINATION_PAGES = 100  # Safety limit to prevent runaway pagination


class SpanContext(BaseModel):
    """Span context containing trace and span identifiers."""
    trace_id: str = Field(..., description="Trace ID (32-character hex string)")
    span_id: str = Field(..., description="Span ID (16-character hex string)")
    trace_state: Optional[str] = Field(None, description="Vendor-specific trace info")


class SpanStatus(BaseModel):
    """Execution status of the span."""
    status_code: str = Field(..., description="Status code: UNSET, OK, or ERROR")
    message: Optional[str] = Field(None, description="Optional status message")


class SpanEvent(BaseModel):
    """Event that occurred during the span."""
    name: str = Field(..., description="Name of the event")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Event attributes")


class Span(BaseModel):
    """OpenTelemetry-compliant span object."""
    name: str = Field(..., description="Human-readable operation name")
    context: SpanContext = Field(..., description="Span context with IDs")
    parent_id: Optional[str] = Field(None, description="Parent span ID (null for root)")
    kind: str = Field(..., description="Span kind (INTERNAL, SERVER, CLIENT, etc.)")
    start_time: str = Field(..., description="Start timestamp (ISO 8601)")
    end_time: str = Field(..., description="End timestamp (ISO 8601)")
    status: SpanStatus = Field(..., description="Span execution status")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Span attributes")
    events: Optional[List[SpanEvent]] = Field(None, description="Span events")


class TraceData(BaseModel):
    """Trace data containing resource spans."""
    resourceSpans: List[Dict[str, Any]] = Field(..., description="Resource spans data")


class PaginationMeta(BaseModel):
    """Pagination metadata for agentops-v3 API responses."""
    model_config = ConfigDict(frozen=True)

    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    totalItems: int = Field(..., description="Total number of items")
    totalPages: int = Field(..., description="Total number of pages")


class Observation(BaseModel):
    """Observation (span) from agentops-v3 API."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Observation ID")
    traceId: str = Field(..., description="Trace ID")
    type: str = Field(..., description="Observation type (e.g., GENERATION)")
    name: str = Field(..., description="Observation name")
    startTime: str = Field(..., description="Start time (ISO 8601)")
    endTime: str = Field(..., description="End time (ISO 8601)")
    model: Optional[str] = Field(None, description="Model used")
    input: Optional[Union[Dict[str, Any], List[Any], str, Any]] = Field(None, description="Input data (can be dict, list, string, or any type)")
    output: Optional[Union[Dict[str, Any], List[Any], str, Any]] = Field(None, description="Output data (can be dict, list, string, or any type)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")
    usage: Optional[Dict[str, Any]] = Field(None, description="Usage statistics")


class ObservationsResponse(BaseModel):
    """Response from GET /v1/agentops-v3/observations."""
    model_config = ConfigDict(frozen=True)

    data: List[Observation] = Field(..., description="List of observations")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class TraceItem(BaseModel):
    """Trace item from agentops-v3 API."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Trace ID")
    name: Optional[str] = Field(None, description="Trace name")
    timestamp: str = Field(..., description="Timestamp (ISO 8601)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")
    input: Optional[Union[Dict[str, Any], List[Any], str, Any]] = Field(None, description="Input data (can be dict, list, string, or any type)")
    output: Optional[Union[Dict[str, Any], List[Any], str, Any]] = Field(None, description="Output data (can be dict, list, string, or any type)")
    sessionId: Optional[str] = Field(None, description="Session ID")
    userId: Optional[str] = Field(None, description="User ID")
    tags: Optional[List[str]] = Field(None, description="Tags")


class TracesResponse(BaseModel):
    """Response from GET /v1/agentops-v3/traces."""
    model_config = ConfigDict(frozen=True)

    data: List[TraceItem] = Field(..., description="List of traces")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class SpansResponse(BaseModel):
    """Response from the get spans API - maintains backward compatibility."""
    traceData: Optional[TraceData] = Field(default=None, description="Trace data with resource spans (legacy)")
    spans: Optional[List[Span]] = Field(default=None, description="Array of spans (legacy format)")
    observations: Optional[List[Observation]] = Field(default=None, description="Array of observations (agentops-v3)")
    nextCursor: Optional[Any] = Field(default=None, description="Cursor for next page (legacy)")
    totalCount: Optional[int] = Field(default=None, description="Total count of spans")
    page: Optional[int] = Field(default=None, description="Current page (agentops-v3)")
    totalPages: Optional[int] = Field(default=None, description="Total pages (agentops-v3)")

    @property
    def next_cursor(self) -> Optional[Any]:
        """Alias for nextCursor for backward compatibility."""
        return self.nextCursor

    @property
    def total_count(self) -> Optional[int]:
        """Alias for totalCount for backward compatibility."""
        return self.totalCount


class SpanCountRange(BaseModel):
    """Range for filtering traces by span count."""
    min: Optional[int] = Field(None, description="Minimum span count")
    max: Optional[int] = Field(None, description="Maximum span count")


class TraceFilters(BaseModel):
    """Filters for searching traces."""
    start_time: Optional[Union[str, datetime]] = Field(default=None, description="Start time (ISO 8601 string or datetime object)")
    end_time: Optional[Union[str, datetime]] = Field(default=None, description="End time (ISO 8601 string or datetime object)")
    service_names: Optional[List[str]] = Field(default=None, description="Filter by service names")
    agent_ids: Optional[List[str]] = Field(default=None, description="Filter by agent IDs")
    agent_names: Optional[List[str]] = Field(default=None, description="Filter by agent names")
    user_ids: Optional[List[str]] = Field(default=None, description="Filter by user IDs")
    session_ids: Optional[List[str]] = Field(default=None, description="Filter by session IDs")
    span_count_range: Optional[SpanCountRange] = Field(default=None, description="Filter by span count range")

    @field_serializer('start_time', 'end_time')
    def serialize_datetime(self, value: Optional[Union[str, datetime]]) -> Optional[str]:
        """Convert datetime objects to ISO 8601 strings with Z suffix."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat() + "Z"
        return value


class TraceSort(BaseModel):
    """Sort configuration for trace search."""
    field: str = Field(..., description="Field to sort by (e.g., 'start_time')")
    direction: str = Field(..., description="Sort direction: 'asc' or 'desc'")


class TraceSearchRequest(BaseModel):
    """Request body for searching traces."""
    filters: TraceFilters = Field(..., description="Search filters")
    sort: Optional[TraceSort] = Field(None, description="Sort configuration")
    page_size: Optional[int] = Field(50, description="Number of results per page (1-100)")
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    include_root_spans: Optional[bool] = Field(False, description="Include root span data")


class RootSpanStatus(BaseModel):
    """Status in root span (different from regular SpanStatus)."""
    code: str = Field(..., description="Status code (e.g., STATUS_CODE_OK)")


class RootSpan(BaseModel):
    """Root span information in trace summary."""
    traceId: str = Field(..., description="Trace ID")
    spanId: str = Field(..., description="Root span ID")
    name: str = Field(..., description="Root span name")
    kind: str = Field(..., description="Span kind")
    startTimeUnixNano: str = Field(..., description="Start timestamp in Unix nanoseconds")
    endTimeUnixNano: str = Field(..., description="End timestamp in Unix nanoseconds")
    status: RootSpanStatus = Field(..., description="Span status")
    attributes: List[Dict[str, Any]] = Field(default_factory=list, description="Span attributes as list of key-value pairs")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Span events")


class TraceSummary(BaseModel):
    """Summary information for a trace."""
    traceId: str = Field(..., description="Trace ID")
    startTime: str = Field(..., description="Trace start time (ISO 8601)")
    endTime: str = Field(..., description="Trace end time (ISO 8601)")
    durationMs: float = Field(..., description="Trace duration in milliseconds")
    spanCount: int = Field(..., description="Number of spans in trace")
    serviceNames: List[str] = Field(..., description="Services involved in trace")
    agentIds: Optional[List[str]] = Field(None, description="Agent IDs")
    agentNames: Optional[List[str]] = Field(None, description="Agent names")
    userIds: Optional[List[str]] = Field(None, description="User IDs")
    sessionIds: Optional[List[str]] = Field(None, description="Session IDs")
    rootSpans: Optional[List[RootSpan]] = Field(None, description="Root spans (if requested)")


class TraceSearchResponse(BaseModel):
    """Response from the search traces API - maintains backward compatibility."""
    generatedAt: str = Field(default="", description="Response generation timestamp")
    originalQuery: dict = Field(default_factory=dict, description="Query parameters used")
    traceSummaries: List[TraceSummary] = Field(default_factory=list, description="Array of trace summaries")
    traces: Optional[List[TraceItem]] = Field(default=None, description="Traces from agentops-v3 API")
    nextCursor: Optional[Any] = Field(default=None, description="Cursor for next page (legacy)")
    totalCount: Optional[int] = Field(default=None, description="Total count of matching traces")
    meta: Optional[PaginationMeta] = Field(default=None, description="Pagination metadata (agentops-v3)")


class TracesClient(BaseWXOClient):
    """
    Client to fetch and export trace data from IBM Watson Orchestrate observability platform.

    This client provides methods to:
    - Fetch spans for a specific trace ID
    - Handle pagination automatically
    - Export traces in json format

    Example:
        ```python
        from ibm_watsonx_orchestrate import Client, Credentials

        credentials = Credentials(url="<url>", api_key="<api_key>")
        client = Client(credentials)

        # Get all spans for a trace
        spans = client.service_instance.traces.get_spans(
            trace_id="1234567890abcdef1234567890abcdef"
        )
        ```
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_local = is_local_dev(self.base_url)
        self.progress: Optional[Any] = None  # Will be set by controller to stop spinner before logging

        if self._is_local: # Override the base_url to point to the agentops-v3 service
            # wxo-server implements the /v1/agentops-v3 endpoints and proxies to Langfuse
            # Use localhost since the CLI runs outside the Docker network
            self.base_url = "http://localhost:4321"
            self.base_endpoint = "/v1/agentops-v3"
            # HTTP doesn't need SSL verification
            self.verify = True
        else:
            # For SaaS: BaseWXOClient already added /v1/orchestrate to base_url
            # We need to strip it and add the agentops-v3 path directly
            # to avoid duplicate /v1 in the path
            if self.base_url.endswith("/v1/orchestrate"):
                self.base_url = self.base_url[:-len("/v1/orchestrate")]
            self.base_endpoint = "/v1/agentops-v3"

    def _stop_progress(self):
        if self.progress:
            self.progress.stop()

    def create(self):
        """Not applicable for traces - read-only resource."""
        raise RuntimeError('Traces are read-only. Use get_spans() to retrieve trace data.')

    def update(self):
        """Not applicable for traces - read-only resource."""
        raise RuntimeError('Traces are read-only. Use get_spans() to retrieve trace data.')

    def delete(self):
        """Not applicable for traces - read-only resource."""
        raise RuntimeError('Traces are read-only. Use get_spans() to retrieve trace data.')

    def get(self):
        """Use get_spans() with a trace_id instead."""
        raise RuntimeError('Use get_spans(trace_id) to retrieve spans for a specific trace.')

    def get_spans(
        self,
        trace_id: str,
        page_size: int = 50,
        cursor: Optional[str] = None,
        fetch_all: bool = True
    ) -> SpansResponse:
        """
        Retrieve all observations (spans) for a specific trace ID using agentops-v3 API.

        Args:
            trace_id: Trace ID (32-character hexadecimal string)
            page_size: Number of observations per page (1-1000, default: 50)
            cursor: Pagination cursor (not used in agentops-v3, kept for compatibility)
            fetch_all: If True, automatically fetches all pages (default: True)

        Returns:
            SpansResponse containing observations and pagination info

        Raises:
            ClientAPIException: If the API request fails
                - 400: Invalid request parameters
                - 401: Missing or invalid tenant.id header
                - 404: Trace ID not found
                - 429: Rate limit exceeded (4 requests per minute)
                - 500: Internal server error

        Example:
            ```python
            # Fetch all observations for a trace
            response = client.service_instance.traces.get_spans(
                trace_id="1234567890abcdef1234567890abcdef"
            )

            print(f"Total observations: {response.total_count}")
            for obs in response.observations:
                print(f"Observation: {obs.name} ({obs.type})")
            ```
        """
        if not trace_id or len(trace_id) != 32:
            raise ValueError("trace_id must be a 32-character hexadecimal string")

        if page_size < 1 or page_size > 1000:
            raise ValueError("page_size must be between 1 and 1000")

        all_observations = []
        current_page = 1
        total_count = None
        total_pages = None
        pages_fetched = 0

        # NOTE: This is a temporary workaround. The agentops-v3 API doesn't support
        # filtering by traceId in the query parameters, so we must fetch all observations
        # and filter client-side. This is inefficient and should be updated once the API
        # supports server-side filtering.
        while current_page <= MAX_PAGINATION_PAGES:
            # Build query parameters for agentops-v3 API
            # Note: The new API only supports page, limit, workspace_id, and include_trace_details
            # traceId filtering must be done client-side
            params = {
                "page": current_page,
                "limit": page_size,
                "include_trace_details": False  # Start with false to avoid backend issues
            }

            # Add workspace_id if in IBM Cloud environment
            try:
                from ibm_watsonx_orchestrate_core.utils.workspaces import add_workspace_query_param
                params = add_workspace_query_param(params)
            except ImportError:
                # Workspace utilities not available, continue without workspace_id
                pass

            # Make API request to observations endpoint
            response = self._get(f"{self.base_endpoint}/observations", params=params)
            obs_response = ObservationsResponse.model_validate(response)

            # Filter observations by traceId client-side since API doesn't support it
            filtered_observations = [
                obs for obs in obs_response.data
                if obs.traceId == trace_id
            ]
            all_observations.extend(filtered_observations)
            pages_fetched += 1

            if total_count is None:
                # Note: total count reflects all observations, not just filtered ones
                total_count = obs_response.meta.totalItems
                total_pages = obs_response.meta.totalPages

            # Check if we should continue fetching
            if not fetch_all or current_page >= obs_response.meta.totalPages:
                break

            current_page += 1

            # Log progress for large fetches
            if pages_fetched % 10 == 0:
                logger.info(f"Fetched {pages_fetched} pages, found {len(all_observations)} matching observations...")

        # Warn if we hit the safety limit
        if current_page > MAX_PAGINATION_PAGES:
            logger.warning(
                f"Reached maximum page limit ({MAX_PAGINATION_PAGES}). "
                f"Some observations may not be fetched. Found {len(all_observations)} observations so far."
            )

        # Warn if we fetched many pages but found few matching observations (inefficient filtering)
        if pages_fetched > 10 and len(all_observations) < pages_fetched * page_size * 0.1:
            logger.warning(
                f"Client-side filtering is inefficient: fetched {pages_fetched} pages "
                f"but only {len(all_observations)} observations match trace_id. "
                f"This is a known limitation of the current API."
            )

        # Return in SpansResponse format for backward compatibility
        return SpansResponse(
            observations=all_observations,
            spans=None,  # Legacy format not used
            traceData=None,  # Legacy format not used
            nextCursor=None,  # Not used in agentops-v3
            totalCount=total_count,
            page=current_page if not fetch_all else total_pages,
            totalPages=total_pages
        )

    def search_traces(
        self,
        filters: Optional[TraceFilters] = None,
        sort: Optional[TraceSort] = None,
        page_size: int = 100,
        cursor: Optional[str] = None,
    ) -> TraceSearchResponse:
        """
        Search for traces using agentops-v3 API.

        This endpoint allows you to find trace IDs based on various criteria such as
        time range, user IDs, session IDs, and sorting.

        Args:
            filters: TraceFilters object with search criteria
                - start_time: Filter by start time (ISO 8601 or datetime)
                - end_time: Filter by end time (ISO 8601 or datetime)
                - user_ids: Filter by user ID (only first ID is used)
                - session_ids: Filter by session ID (only first ID is used)
            sort: TraceSort object for sorting results
                - field: Sort field (use "start_time", "end_time", or "timestamp" - all map to API's "timestamp")
                - direction: Sort direction ("asc" or "desc")
            page_size: Number of results per page (1-1000, default: 100)
            cursor: Pagination cursor (not used in agentops-v3, kept for compatibility)

        Returns:
            TraceSearchResponse containing trace items and pagination info

        Raises:
            ClientAPIException: If the API request fails
                - 400: Invalid request parameters
                - 401: Missing or invalid authentication
                - 429: Rate limit exceeded
                - 500: Internal server error

        Note:
            - Uses GET /v1/agentops-v3/traces with query parameters
            - Supported API parameters: page, limit, userId, sessionId, fromTimestamp, toTimestamp, orderBy
            - API uses "timestamp" field for sorting (start_time/end_time are mapped to timestamp)
            - Pagination uses page/limit instead of cursor
            - Only the first userId and sessionId are used if multiple are provided

        Example:
            ```python
            from datetime import datetime, timedelta

            # Search for traces with session ID and time range
            filters = TraceFilters(
                session_ids=["sess-abc123"],
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now()
            )

            # Sort by timestamp (can also use "start_time" or "end_time" - all map to "timestamp")
            sort = TraceSort(field="timestamp", direction="desc")

            response = client.service_instance.traces.search_traces(
                filters=filters,
                sort=sort,
                page_size=50
            )

            print(f"Found {response.totalCount} traces")
            for trace in response.traces:
                print(f"Trace ID: {trace.id}, Session: {trace.sessionId}")
            ```
        """
        if page_size < 1 or page_size > 1000:
            raise ValueError("page_size must be between 1 and 1000")

        if filters is None:
            filters = TraceFilters()

        # API now handles filtering server-side, so we only fetch one page
        all_trace_summaries = []
        all_traces = []
        current_page = 1
        total_items = 0
        total_pages = 0
        last_params: Dict[str, Any] = {}
        traces_response: Optional[TracesResponse] = None

        # Only fetch the first page since API handles filtering
        max_pages_to_fetch = 1

        while current_page <= max_pages_to_fetch:
            # Build query parameters for GET request
            # API supports: page, limit, userId, sessionId, fromTimestamp, toTimestamp, orderBy,
            # name, tags, version, workspace_id, and include_trace_details
            last_params = {
                "page": current_page,
                "limit": page_size,
                "include_trace_details": False  # Start with false to avoid backend issues
            }

            # Add API-supported filter parameters
            if filters.user_ids and len(filters.user_ids) > 0:
                # API supports single userId parameter
                last_params["userId"] = filters.user_ids[0]

            if filters.session_ids and len(filters.session_ids) > 0:
                # API supports single sessionId parameter
                last_params["sessionId"] = filters.session_ids[0]

            # Add time range filters if provided
            if filters.start_time:
                start_time_str = filters.start_time if isinstance(filters.start_time, str) else filters.start_time.isoformat() + "Z"
                last_params["fromTimestamp"] = start_time_str

            if filters.end_time:
                end_time_str = filters.end_time if isinstance(filters.end_time, str) else filters.end_time.isoformat() + "Z"
                last_params["toTimestamp"] = end_time_str

            # Add sort parameter if provided
            if sort:
                # API uses orderBy parameter with format "field.direction" (e.g., "timestamp.desc")
                # Map internal field names to API field names
                field_mapping = {
                    "start_time": "timestamp",
                    "end_time": "timestamp",
                    "timestamp": "timestamp"
                }
                api_field = field_mapping.get(sort.field, sort.field)
                last_params["orderBy"] = f"{api_field}.{sort.direction}"

            # Add workspace_id if in IBM Cloud environment
            try:
                from ibm_watsonx_orchestrate_core.utils.workspaces import add_workspace_query_param
                last_params = add_workspace_query_param(last_params)
            except ImportError:
                # Workspace utilities not available, continue without workspace_id
                pass

            try:
                response = self._get(
                    f"{self.base_endpoint}/traces",
                    params=last_params
                )
            except Exception as e:
                raise e

            # Parse response in agentops-v3 format
            traces_response = TracesResponse.model_validate(response)

            if current_page == 1:
                total_items = traces_response.meta.totalItems
                total_pages = traces_response.meta.totalPages

            # Convert to TraceSummary format
            # Note: API now handles userId and sessionId filtering, so no client-side filtering needed
            for trace_item in traces_response.data:
                # Extract agent name and ID from metadata if available
                agent_name = None
                agent_id = None
                if trace_item.metadata and isinstance(trace_item.metadata, dict):
                    attributes = trace_item.metadata.get('attributes', {})
                    if isinstance(attributes, dict):
                        agent_name = attributes.get('agent.name')
                        agent_id = attributes.get('agent.id')

                # Calculate latency from trace metadata if available
                latency_seconds = None
                if trace_item.metadata and isinstance(trace_item.metadata, dict):
                    latency_seconds = trace_item.metadata.get('latency')

                # Convert latency to milliseconds
                duration_ms = 0.0
                if latency_seconds is not None:
                    duration_ms = float(latency_seconds) * 1000.0

                # Create a TraceSummary from TraceItem
                summary = TraceSummary(
                    traceId=trace_item.id,
                    startTime=trace_item.timestamp,
                    endTime=trace_item.timestamp,  # TODO: Not available in agentops-v3 API
                    durationMs=duration_ms,
                    spanCount=0,  # TODO: Not available in agentops-v3 API
                    serviceNames=[],  # TODO: Not available in agentops-v3 API
                    agentIds=[agent_id] if agent_id else [],
                    agentNames=[agent_name] if agent_name else [],
                    userIds=[trace_item.userId] if trace_item.userId else [],
                    sessionIds=[trace_item.sessionId] if trace_item.sessionId else [],
                    rootSpans=None
                )
                all_trace_summaries.append(summary)
                all_traces.append(trace_item)

            # Only fetch first page since API handles filtering
            break

        # Warn if there are more pages available
        if len(all_trace_summaries) == page_size and total_pages > 1:
            self._stop_progress()
            logger.warning(
                f"Limit reached. More traces may exist (page 1 of {total_pages}). "
                f"Tip: Increase --limit or use more specific filters"
            )

        return TraceSearchResponse(
            generatedAt=datetime.now().isoformat() + "Z",
            originalQuery=last_params,
            traceSummaries=all_trace_summaries,
            traces=all_traces,
            totalCount=total_items,
            meta=traces_response.meta if traces_response else None,
            nextCursor=None
        )
