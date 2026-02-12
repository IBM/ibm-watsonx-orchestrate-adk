import logging
import jwt

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer

from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient

logger = logging.getLogger(__name__)


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


class SpansResponse(BaseModel):
    """Response from the get spans API."""
    traceData: Optional[TraceData] = Field(None, description="Trace data with resource spans")
    spans: Optional[List[Span]] = Field(None, description="Array of spans (legacy format)")
    nextCursor: Optional[Any] = Field(None, alias="next_cursor", description="Cursor for next page")
    totalCount: Optional[int] = Field(None, alias="total_count", description="Total count of spans")
    
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
    start_time: Optional[Union[str, datetime]] = Field(None, description="Start time (ISO 8601 string or datetime object)")
    end_time: Optional[Union[str, datetime]] = Field(None, description="End time (ISO 8601 string or datetime object)")
    service_names: Optional[List[str]] = Field(None, description="Filter by service names")
    agent_ids: Optional[List[str]] = Field(None, description="Filter by agent IDs")
    agent_names: Optional[List[str]] = Field(None, description="Filter by agent names")
    user_ids: Optional[List[str]] = Field(None, description="Filter by user IDs")
    session_ids: Optional[List[str]] = Field(None, description="Filter by session IDs")
    span_count_range: Optional[SpanCountRange] = Field(None, description="Filter by span count range")
    
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
    """Response from the search traces API."""
    generatedAt: str = Field(..., description="Response generation timestamp")
    originalQuery: dict = Field(..., description="Query parameters used")
    traceSummaries: List[TraceSummary] = Field(..., description="Array of trace summaries")
    nextCursor: Optional[Any] = Field(None, description="Cursor for next page")
    totalCount: Optional[int] = Field(None, description="Total count of matching traces")


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
        if is_local_dev(self.base_url):
            self.base_endpoint = "/orchestrate/v1/traces"
        else:
            if self.base_url.endswith("/orchestrate"):
                self.base_url = self.base_url[:-len("/orchestrate")]
                self.base_endpoint = "/traces"    

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
        Retrieve all spans for a specific trace ID.
        
        Args:
            trace_id: Trace ID (32-character hexadecimal string)
            page_size: Number of spans per page (1-1000, default: 50)
            cursor: Pagination cursor for fetching next page
            fetch_all: If True, automatically fetches all pages (default: True)
        
        Returns:
            SpansResponse containing spans and pagination info
        
        Raises:
            ClientAPIException: If the API request fails
                - 400: Invalid request parameters
                - 401: Missing or invalid tenant.id header
                - 404: Trace ID not found
                - 429: Rate limit exceeded (4 requests per minute)
                - 500: Internal server error
        
        Example:
            ```python
            # Fetch all spans for a trace
            response = client.service_instance.traces.get_spans(
                trace_id="1234567890abcdef1234567890abcdef"
            )
            
            print(f"Total spans: {response.total_count}")
            for span in response.spans:
                print(f"Span: {span.name} ({span.kind})")
            ```
        """
        if not trace_id or len(trace_id) != 32:
            raise ValueError("trace_id must be a 32-character hexadecimal string")
        
        if page_size < 1 or page_size > 1000:
            raise ValueError("page_size must be between 1 and 1000")
        
        all_spans = []
        current_cursor = cursor
        total_count = None
        
        while True:
            # Build query parameters
            params = {"page_size": page_size}
            if current_cursor:
                params["cursor"] = current_cursor
            
            # Make API request and parse the response
            response = self._get(f"{self.base_endpoint}/{trace_id}/spans", params=params)
            spans_response = SpansResponse.model_validate(response)
            
            if spans_response.traceData: # extract spans from traceData.resourceSpans
                return spans_response
            elif spans_response.spans: # spans array directly
                all_spans.extend(spans_response.spans)
            else:
                logger.warning("No spans or traceData in response")
                break
            
            if total_count is None and spans_response.totalCount:
                total_count = spans_response.totalCount
            
            if not fetch_all or not spans_response.nextCursor:
                break
            
            current_cursor = spans_response.nextCursor
            logger.info(f"Fetched {len(all_spans)}/{total_count or '?'} spans, continuing...")
                
        return SpansResponse(
            spans=all_spans,
            nextCursor=None if fetch_all else spans_response.nextCursor,
            totalCount=total_count
        )
        
    def search_traces(
        self,
        filters: Optional[TraceFilters] = None,
        sort: Optional[TraceSort] = None,
        page_size: int = 50,
        cursor: Optional[str] = None,
        include_root_spans: bool = False,
        fetch_all: bool = True
    ) -> TraceSearchResponse:
        """
        Search for traces using filters.
        
        This endpoint allows you to find trace IDs based on various criteria such as
        time range, service names, agent IDs, user IDs, session IDs, and span count.
        
        Args:
            filters: TraceFilters object with search criteria (start_time, end_time, etc.)
            sort: TraceSort object for sorting results (field and direction)
            page_size: Number of results per page (1-100, default: 50)
            cursor: Pagination cursor for fetching next page
            include_root_spans: Include root span data in results (default: False)
            fetch_all: If True, automatically fetches all pages (default: True)
        
        Returns:
            TraceSearchResponse containing trace summaries and pagination info
        
        Raises:
            ClientAPIException: If the API request fails
                - 400: Invalid request body or parameters
                - 401: Missing or invalid tenant.id header
                - 429: Rate limit exceeded (4 requests per minute)
                - 500: Internal server error
        
        Note:
            - This endpoint is accessible only to Admins
            - Rate limit: 4 requests per minute
            - Not available in on-premises offering
        
        Example:
            ```python
            from datetime import datetime, timedelta
            
            # Search for traces in the last 24 hours for specific service and agent name
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
            
            filters = TraceFilters(
                start_time=start_time.isoformat() + "Z",
                end_time=end_time.isoformat() + "Z",
                service_names=["wxo-server"],
                agent_names=["mobile-agent"]
            )
            
            sort = TraceSort(field="start_time", direction="desc")
            
            response = client.service_instance.traces.search_traces(
                filters=filters,
                sort=sort,
                include_root_spans=True
            )
            
            print(f"Found {response.total_count} traces")
            for trace in response.traces:
                print(f"Trace ID: {trace.trace_id}, Duration: {trace.duration_ms}ms")
            ```
        """
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        
        if filters is None:
            filters = TraceFilters()
        
        request_body = TraceSearchRequest(
            filters=filters,
            sort=sort,
            page_size=page_size,
            cursor=cursor,
            include_root_spans=include_root_spans
        )
        
        all_traces = []
        current_cursor = cursor
        total_count = None
        
        while True:
            request_body.cursor = current_cursor
            
            request_dict = request_body.model_dump(exclude_none=True) # NOT send empty/None fields
            response = self._post(
                f"{self.base_endpoint}/search",
                data=request_dict
            )
            search_response = TraceSearchResponse.model_validate(response)
            all_traces.extend(search_response.traceSummaries)
            
            # Store total count from first response
            if total_count is None and search_response.totalCount:
                total_count = search_response.totalCount
            
            # Check if we should continue fetching
            if not fetch_all or not search_response.nextCursor:
                break
            
            current_cursor = search_response.nextCursor
        
        return TraceSearchResponse(
            generatedAt=search_response.generatedAt,
            originalQuery=search_response.originalQuery,
            traceSummaries=all_traces,
            nextCursor=None if fetch_all else search_response.nextCursor,
            totalCount=total_count
        )
        