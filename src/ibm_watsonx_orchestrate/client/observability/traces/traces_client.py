import logging

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer, ConfigDict

from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient

logger = logging.getLogger(__name__)

# Constants
MAX_PAGINATION_PAGES = 100  # Safety limit to prevent runaway pagination


class PaginationMeta(BaseModel):
    """Pagination metadata for agentops-v3 API responses."""
    model_config = ConfigDict(frozen=True)

    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    totalItems: int = Field(..., description="Total number of items")
    totalPages: int = Field(..., description="Total number of pages")


class Observation(BaseModel):
    """
    A single recorded step within a trace, returned by GET /v1/agentops-v3/observations.
    """
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


class ObservationsExportResponse(BaseModel):
    """Response returned by get_observations() / get_spans()."""
    observations: Optional[List[Observation]] = Field(default=None, description="Array of observations (agentops-v3)")
    totalCount: Optional[int] = Field(default=None, description="Total count of observations")
    page: Optional[int] = Field(default=None, description="Current page")
    totalPages: Optional[int] = Field(default=None, description="Total pages")

    @property
    def total_count(self) -> Optional[int]:
        return self.totalCount


class TraceFilters(BaseModel):
    """Filters for searching traces."""
    start_time: Optional[Union[str, datetime]] = Field(default=None, description="Start time (ISO 8601 string or datetime object)")
    end_time: Optional[Union[str, datetime]] = Field(default=None, description="End time (ISO 8601 string or datetime object)")
    service_names: Optional[List[str]] = Field(default=None, description="Filter by service names")
    agent_ids: Optional[List[str]] = Field(default=None, description="Filter by agent IDs")
    agent_names: Optional[List[str]] = Field(default=None, description="Filter by agent names")
    user_ids: Optional[List[str]] = Field(default=None, description="Filter by user IDs")
    session_ids: Optional[List[str]] = Field(default=None, description="Filter by session IDs")

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


class TraceSummary(BaseModel):
    """Summary information for a trace."""
    traceId: str = Field(..., description="Trace ID")
    startTime: str = Field(..., description="Trace start time (ISO 8601)")
    endTime: str = Field(..., description="Trace end time (ISO 8601)")
    durationMs: float = Field(..., description="Trace duration in milliseconds")
    agentIds: Optional[List[str]] = Field(None, description="Agent IDs")
    agentNames: Optional[List[str]] = Field(None, description="Agent names")
    userIds: Optional[List[str]] = Field(None, description="User IDs")
    sessionIds: Optional[List[str]] = Field(None, description="Session IDs")


class TraceSearchResponse(BaseModel):
    """Response from the search traces API."""
    generatedAt: str = Field(default="", description="Response generation timestamp")
    originalQuery: dict = Field(default_factory=dict, description="Query parameters used")
    traceSummaries: List[TraceSummary] = Field(default_factory=list, description="Array of trace summaries")
    traces: Optional[List[TraceItem]] = Field(default=None, description="Traces from agentops-v3 API")
    totalCount: Optional[int] = Field(default=None, description="Total count of matching traces")
    meta: Optional[PaginationMeta] = Field(default=None, description="Pagination metadata (agentops-v3)")


class TracesClient(BaseWXOClient):
    """
    Client to fetch and export trace data from IBM Watson Orchestrate observability platform.

    This client provides methods to:
    - Fetch observations for a specific trace ID
    - Handle pagination automatically
    - Export traces in JSON format

    Example:
        ```python
        from ibm_watsonx_orchestrate import Client, Credentials

        credentials = Credentials(url="<url>", api_key="<api_key>")
        client = Client(credentials)

        # Get all observations for a trace
        result = client.service_instance.traces.get_observations(
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
        raise RuntimeError('Traces are read-only. Use get_observations() to retrieve trace data.')

    def update(self):
        """Not applicable for traces - read-only resource."""
        raise RuntimeError('Traces are read-only. Use get_observations() to retrieve trace data.')

    def delete(self):
        """Not applicable for traces - read-only resource."""
        raise RuntimeError('Traces are read-only. Use get_observations() to retrieve trace data.')

    def get(self):
        """Use get_observations() with a trace_id instead."""
        raise RuntimeError('Use get_observations(trace_id) to retrieve observations for a specific trace.')

    def get_observations(
        self,
        trace_id: str,
        page_size: int = 50,
        fetch_all: bool = True
    ) -> ObservationsExportResponse:
        """
        Retrieve all observations for a specific trace ID using agentops-v3 API.

        Args:
            trace_id: Trace ID (32-character hexadecimal string)
            page_size: Number of observations per page (1-1000, default: 50)
            fetch_all: If True, automatically fetches all pages (default: True)

        Returns:
            ObservationsExportResponse containing observations and pagination info

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
            response = client.service_instance.traces.get_observations(
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

        while current_page <= MAX_PAGINATION_PAGES:
            params: Dict[str, Any] = {
                "page": current_page,
                "limit": page_size,
                "traceId": trace_id,
            }

            # Add workspace_id if in IBM Cloud environment
            try:
                from ibm_watsonx_orchestrate_core.utils.workspaces import add_workspace_query_param
                params = add_workspace_query_param(params)
            except ImportError:
                pass

            response = self._get(f"{self.base_endpoint}/observations", params=params)
            obs_response = ObservationsResponse.model_validate(response)

            all_observations.extend(obs_response.data)

            if total_count is None:
                total_count = obs_response.meta.totalItems
                total_pages = obs_response.meta.totalPages

            if not fetch_all or current_page >= obs_response.meta.totalPages:
                break

            current_page += 1

        if current_page > MAX_PAGINATION_PAGES:
            logger.warning(
                f"Reached maximum page limit ({MAX_PAGINATION_PAGES}). "
                f"Some observations may not be fetched. Found {len(all_observations)} so far."
            )

        return ObservationsExportResponse(
            observations=all_observations,
            totalCount=total_count,
            page=current_page if not fetch_all else total_pages,
            totalPages=total_pages
        )

    def search_traces(
        self,
        filters: Optional[TraceFilters] = None,
        sort: Optional[TraceSort] = None,
        page_size: int = 100,
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

        all_trace_summaries = []
        all_traces = []
        current_page = 1
        total_items = 0
        total_pages = 0
        last_params: Dict[str, Any] = {}
        traces_response: Optional[TracesResponse] = None

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
                    endTime=trace_item.timestamp,  # Not separately available in agentops-v3 API
                    durationMs=duration_ms,
                    agentIds=[agent_id] if agent_id else [],
                    agentNames=[agent_name] if agent_name else [],
                    userIds=[trace_item.userId] if trace_item.userId else [],
                    sessionIds=[trace_item.sessionId] if trace_item.sessionId else [],
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
        )
