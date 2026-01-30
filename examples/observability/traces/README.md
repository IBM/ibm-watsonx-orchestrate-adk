# Trace Export and Search Examples

This directory contains examples for searching and exporting trace data from the IBM Watson Orchestrate observability platform.

## Overview

The trace functionality allows you to:
- **Search for traces** using filters (time range, service names, agent IDs, user IDs, etc.)
- **Fetch trace spans** from the Watson Orchestrate observability platform
- Work with trace data as Python objects for programmatic analysis
- Export traces to JSON format (OpenTelemetry-compliant)
- Pipe trace data to tools like `jq` for CI/CD pipelines
- Import trace data into third-party trace analysis tools

## Prerequisites

1. **Admin Access**: The traces API endpoint requires admin privileges
2. **Active Environment**: Configure your Watson Orchestrate environment using `wxo env add`
3. **Trace ID**: Obtain a trace ID from your observability platform (32-character hexadecimal string)

## Quick Start

### Using the CLI

**Search for traces:**
```bash
# Search by time range (required parameters)
# Accepted formats: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or YYYY-MM-DD HH:MM:SS
orchestrate observability traces search \
  --start-time 2025-07-20T00:00:00 \
  --end-time 2025-07-20T23:59:59

# Search for the previous day
orchestrate observability traces search   --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S)   --end-time $(date -u +%Y-%m-%dT%H:%M:%S) 

# Search by service and agent
orchestrate observability traces search \
  --start-time 2025-07-20T00:00:00 \
  --end-time 2025-07-20T23:59:59 \
  --service-name wxo-server \
  --agent-name mobile-agent

# Search by user ID
orchestrate observability traces search \
  --start-time 2025-07-20T00:00:00 \
  --end-time 2025-07-20T23:59:59 \
  --user-id user123

# Search with span count filter and sorting
orchestrate observability traces search \
  --start-time 2025-07-20T00:00:00 \
  --end-time 2025-07-20T23:59:59 \
  --min-spans 10 \
  --max-spans 100 \
  --sort-field start_time \
  --sort-direction desc \
  --limit 20

# Include root span data
orchestrate observability traces search \
  --start-time 2025-07-20T00:00:00 \
  --end-time 2025-07-20T23:59:59 \
  --include-root-spans \
  --limit 10

```

**Print to stdout (for piping to jq):**
```bash
orchestrate observability traces export \
  --trace-id 1234567890abcdef1234567890abcdef
```

**Pipe to jq for filtering:**
```bash
orchestrate observability traces export \
  -t 1234567890abcdef1234567890abcdef | \
  jq '.spans[] | select(.status.status_code == "ERROR")'
```
**Export a trace to JSON file:**
```bash
orchestrate observability traces export \
  --trace-id 1234567890abcdef1234567890abcdef \
  --output trace.json
```

### Using the Python SDK

**Search for traces:**
```python
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.observability.traces import TracesClient, TraceFilters, TraceSort
from datetime import datetime, timedelta

# Initialize client
client = instantiate_client(TracesClient)

# Search for traces in the last 24 hours
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=1)

filters = TraceFilters(
    start_time=start_time,  # Can pass datetime objects directly
    end_time=end_time,
    service_names=["wxo-server"],
    agent_names=["mobile-agent"]
)

sort = TraceSort(field="start_time", direction="desc")

# Search returns TraceSummary objects
search_response = client.search_traces(
    filters=filters,
    sort=sort,
    include_root_spans=True
)

# Work with the results
print(f"Found {len(search_response.traceSummaries)} traces")
for trace in search_response.traceSummaries:
    print(f"Trace ID: {trace.traceId}")
    print(f"  Duration: {trace.durationMs}ms")
    print(f"  Spans: {trace.spanCount}")
    print(f"  Agent: {trace.agentNames[0] if trace.agentNames else 'N/A'}")
```

**Fetch spans for a specific trace:**
```python
# Fetch spans - returns SpansResponse object with Python objects
spans_response = client.get_spans(
    trace_id="1234567890abcdef1234567890abcdef"
)

# Work with the data directly
for span in spans_response.spans:
    print(f"Span: {span.name}, Status: {span.status.status_code}")
    if span.attributes:
        print(f"  Attributes: {span.attributes}")
```

**Export to JSON:**
```python
from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_exporters import TraceExporter

# Export to file
exporter = TraceExporter()
exporter.export_to_json(spans_response, output_file="trace.json")

# Get JSON string for further processing
json_str = exporter.export_to_json(spans_response, output_file=None)
```

**Complete workflow (search then export):**
```python
# 1. Search for traces with errors
filters = TraceFilters(
    start_time=(datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
)

search_response = client.search_traces(
    filters=filters,
    include_root_spans=True
)

# 2. Find traces with errors
error_traces = [
    t for t in search_response.traces
    if t.root_span and t.root_span.status.status_code == "ERROR"
]

# 3. Export the first error trace
if error_traces:
    trace_id = error_traces[0].trace_id
    spans = client.get_spans(trace_id)
    
    exporter = TraceExporter()
    exporter.export_to_json(spans, output_file=f"error_trace_{trace_id[:8]}.json")
```

## Export Format

### JSON Format (OpenTelemetry-compliant)
- **Use case**: Import into trace analysis tools, CI/CD pipelines
- **Format**: OpenTelemetry-compliant JSON (as returned by the API)
- **Features**: Preserves complete trace structure, attributes, and events

```

## API Details

### Search Traces API

**Available Filters**:
- `start_time`: Start time [required]
- `end_time`: End time [required]
- `service_names`: List of service names
- `agent_ids`: List of agent IDs
- `agent_names`: List of agent names
- `user_ids`: List of user IDs
- `session_ids`: List of session IDs
- `span_count_range`: Min/max span count filter

**Sorting**:
- `field`: Field to sort by ("start_time" or "duration_ms")
- `direction`: "asc" or "desc"

**Options**:
- `include_root_spans`: Include root span data in results (default: false)

**Example**:
```python
from ibm_watsonx_orchestrate.client.traces import TraceFilters, TraceSort, SpanCountRange

# Complex search with multiple filters
filters = TraceFilters(
    start_time="2025-07-20T00:00:00",
    end_time="2025-07-20T23:59:59",
    service_names=["wxo-server", "agent-service"],
    agent_names=["mobile-agent"],
    user_ids=["user123"],
    span_count_range=SpanCountRange(min=10, max=100)
)

sort = TraceSort(field="duration_ms", direction="desc")

results = client.search_traces(filters=filters, sort=sort)
```

### Get Spans API

**Endpoint**: `GET /v1/traces/{trace_id}/spans`

### Rate Limits
- **Limit**: 4 requests per minute per user (both search and get spans)
- **Tip**: Use larger page sizes to minimize requests
  - Search: up to 100 results per page
  - Get spans: up to 1000 spans per page


### Error Handling

Common errors and solutions:

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 400 | Invalid parameters | Check trace_id format (32-char hex) |
| 401 | Authentication failed | Verify credentials with `wxo env list` |
| 404 | Trace not found | Verify trace_id exists in your environment |
| 429 | Rate limit exceeded | Wait 15+ seconds before retrying |
| 500 | Server error | Retry after a short delay |

## Examples

See `export_trace_example.py` for complete examples:

**Export Examples:**
1. Working with trace data as Python objects
2. Exporting to JSON files
3. Custom trace analysis
4. Integration with external systems
5. CI/CD pipeline usage

**Search Examples:**
6. Searching for traces with filters
7. Search and export workflow
8. Searching by user ID
9. Searching by span count range
