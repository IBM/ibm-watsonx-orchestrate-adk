"""
Example: Export and search trace data from Watson Orchestrate observability platform

This example demonstrates how to use the TracesController for programmatic access.
The controller is designed to be imported and used in custom Python scripts.

Prerequisites:
- Active Watson Orchestrate environment configured
- Admin access (traces endpoint requires admin privileges)
- Valid trace ID from your observability platform
"""

from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller import TracesController
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.client.observability.traces import TraceFilters, TraceSort, SpanCountRange
from datetime import datetime, timezone, timedelta

def example_basic_usage(trace_id):
    """
    Example 1: Fetch and analyze traces.
    
    """
    
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    try:
        # Create controller
        controller = TracesController()
        
        # Fetch spans
        print(f"\nFetching spans for trace {trace_id}")
        spans_response = controller.fetch_trace_spans(trace_id)
        
        # Handle both response formats
        if spans_response.traceData:
            # New format: traceData with resourceSpans
            print(f"✓ Fetched trace data with resourceSpans")
            resource_spans = spans_response.traceData.resourceSpans
            print(f"  Resource spans: {len(resource_spans)}")
            
            # Count total spans across all resource spans
            total_spans = sum(
                len(scope_span.get('spans', []))
                for rs in resource_spans
                for scope_span in rs.get('scopeSpans', [])
            )
            print(f"  Total spans: {total_spans}")
            
            # Example: Find error spans in the raw data
            error_count = 0
            for rs in resource_spans:
                for scope_span in rs.get('scopeSpans', []):
                    for span in scope_span.get('spans', []):
                        status = span.get('status', {})
                        if status.get('code') == 'STATUS_CODE_ERROR':
                            error_count += 1
            print(f"  Error spans: {error_count}")
            
        elif spans_response.spans:
            # Legacy format: flat spans array
            print(f"✓ Fetched {len(spans_response.spans)} spans")
            print(f"  Total count: {spans_response.total_count}")
            
            # Analyze the spans (Python objects!)
            error_spans = [s for s in spans_response.spans
                          if s.status.status_code == "ERROR"]
            print(f"  Error spans: {len(error_spans)}")
        else:
            print("✗ No trace data found")
            return None
        
        return spans_response
        
    except ClientAPIException as e:
        print(f"✗ API Error ({e.response.status_code}): {e}")
        return None


def example_export_to_file(trace_id):
    """
    Example 2: Export specific trace to JSON file.
    """
    
    print("\n" + "=" * 60)
    print("Example 2: Export to JSON File")
    print("=" * 60)
    
    try:
        controller = TracesController()
        
        # Export to file (returns both objects and JSON string)
        print(f"\nExporting trace {trace_id} to file")
        spans_response, json_str = controller.export_trace_to_json(
            trace_id,
            output_file="my_trace.json",
            pretty=True
        )
        
        # Handle both response formats
        if spans_response.traceData:
            print(f"✓ Exported trace data to my_trace.json")
            print(f"  JSON string length: {len(json_str)} characters")
            print(f"  Format: traceData with resourceSpans")
        elif spans_response.spans:
            print(f"✓ Exported {len(spans_response.spans)} spans to my_trace.json")
            print(f"  JSON string length: {len(json_str)} characters")
            
            # You can still use the spans_response object
            for span in spans_response.spans[:3]:
                print(f"  - {span.name}: {span.status.status_code}")
        
        return spans_response
        
    except ClientAPIException as e:
        print(f"✗ API Error ({e.response.status_code}): {e}")
        return None


def example_custom_analysis(trace_id):
    """
    Example 3: Custom trace analysis.
    
    Shows how to use the controller for custom analysis workflows.
    """
    
    print("\n" + "=" * 60)
    print("Example 3: Custom Analysis")
    print("=" * 60)
    
    try:
        controller = TracesController()
        
        # Fetch spans
        print(f"\nAnalyzing trace {trace_id}")
        spans_response = controller.fetch_trace_spans(trace_id)
        
        # Custom analysis
        
        analysis = {
            'total_spans': 0,
            'errors': 0,
            'warnings': 0,
            'slow_spans': [],
            'span_types': {}
        }
        
        # Handle both response formats
        if spans_response.traceData:
            # Analyze traceData format
            for rs in spans_response.traceData.resourceSpans:
                for scope_span in rs.get('scopeSpans', []):
                    for span in scope_span.get('spans', []):
                        analysis['total_spans'] += 1
                        
                        # Count errors
                        status = span.get('status', {})
                        if status.get('code') == 'STATUS_CODE_ERROR':
                            analysis['errors'] += 1
                        
                        # Calculate duration
                        try:
                            start_nano = int(span.get('startTimeUnixNano', 0))
                            end_nano = int(span.get('endTimeUnixNano', 0))
                            duration_ms = (end_nano - start_nano) / 1_000_000
                            
                            if duration_ms > 1000:  # Slow spans (>1 second)
                                analysis['slow_spans'].append({
                                    'name': span.get('name', 'unknown'),
                                    'duration_ms': round(duration_ms, 2)
                                })
                        except:
                            pass
                        
                        # Count span types
                        kind = span.get('kind', 'UNKNOWN')
                        analysis['span_types'][kind] = analysis['span_types'].get(kind, 0) + 1
        
        elif spans_response.spans:
            # Analyze legacy spans format
            analysis['total_spans'] = len(spans_response.spans)
            
            for span in spans_response.spans:
                # Count errors
                if span.status.status_code == "ERROR":
                    analysis['errors'] += 1
                
                # Calculate duration
                try:
                    start = datetime.fromisoformat(span.start_time.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(span.end_time.replace('Z', '+00:00'))
                    duration_ms = (end - start).total_seconds() * 1000
                    
                    if duration_ms > 1000:  # Slow spans (>1 second)
                        analysis['slow_spans'].append({
                            'name': span.name,
                            'duration_ms': round(duration_ms, 2)
                        })
                except:
                    pass
                
                # Count span types
                analysis['span_types'][span.kind] = analysis['span_types'].get(span.kind, 0) + 1
        
        # Print analysis
        print(f"\n✓ Analysis complete:")
        print(f"  Total spans: {analysis['total_spans']}")
        print(f"  Errors: {analysis['errors']}")
        print(f"  Slow spans (>1s): {len(analysis['slow_spans'])}")
        print(f"  Span types: {analysis['span_types']}")
        
        if analysis['slow_spans']:
            print(f"\n  Slowest spans:")
            for slow in sorted(analysis['slow_spans'], key=lambda x: x['duration_ms'], reverse=True)[:3]:
                print(f"    - {slow['name']}: {slow['duration_ms']}ms")
        
        return analysis
        
    except ClientAPIException as e:
        print(f"✗ API Error ({e.response.status_code}): {e}")
        return None


def example_search_traces():
    """
    Example 4: Search for traces using filters.
    
    Shows how to find trace IDs before exporting them.
    """
    print("\n" + "=" * 60)
    print("Example 4: Search for Traces")
    print("=" * 60)
    
    try:
        controller = TracesController()
        
        # Search for traces in the last 24 hours
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)
        
        filters = TraceFilters(
            start_time=start_time.isoformat().replace('+00:00', 'Z'),
            end_time=end_time.isoformat().replace('+00:00', 'Z'),
            service_names=["wxo-server"]
        )
        
        sort = TraceSort(field="start_time", direction="desc")
        
        print(f"\nSearching for traces from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
        search_response = controller.search_traces(
            filters=filters,
            sort=sort,
            include_root_spans=False
        )
        
        print(f"✓ Found {len(search_response.traceSummaries)} traces")
        
        if search_response.traceSummaries:
            print(f"\n  First 3 traces:")
            for trace in search_response.traceSummaries[:3]:
                print(f"    - Trace ID: {trace.traceId}")
                print(f"      Duration: {trace.durationMs}ms")
                print(f"      Spans: {trace.spanCount}")
                agent_name = trace.agentNames[0] if trace.agentNames else 'N/A'
                print(f"      Agent: {agent_name}")
        
        return search_response
        
    except ClientAPIException as e:
        print(f"✗ API Error ({e.response.status_code}): {e}")
        return None


def example_search_and_export():
    """
    Example 5: Search for traces, then export them.
    
    Complete workflow: search -> find trace IDs -> export error traces.
    """
    print("\n" + "=" * 60)
    print("Example 5: Search and Export Workflow")
    print("=" * 60)
    
    try:
        controller = TracesController()
        
        # Step 1: Search for traces with errors
        print("\nStep 1: Searching for traces with errors...")
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        filters = TraceFilters(
            start_time=start_time.isoformat().replace('+00:00', 'Z'),
            end_time=end_time.isoformat().replace('+00:00', 'Z')
        )
        
        search_response = controller.search_traces(
            filters=filters,
            include_root_spans=True  # Include root span to check status
        )
        
        print(f"✓ Found {len(search_response.traceSummaries)} traces")
        
        # Step 2: Filter traces with errors (if root span has error status)
        error_traces = []
        for trace in search_response.traceSummaries:
            if trace.rootSpans:
                for root_span in trace.rootSpans:
                    if root_span.status.code == "STATUS_CODE_ERROR":
                        error_traces.append(trace)
                        break
        
        print(f"  Traces with errors: {len(error_traces)}")
        
        # Step 3: Export the first error trace
        if error_traces:
            trace_to_export = error_traces[0]
            print(f"\nStep 2: Exporting error trace {trace_to_export.traceId[:16]}...")
            
            spans_response, json_str = controller.export_trace_to_json(
                trace_to_export.traceId,
                output_file=f"error_trace_{trace_to_export.traceId[:8]}.json",
                pretty=True
            )
            
            if spans_response.traceData:
                print(f"✓ Exported trace data")
            elif spans_response.spans:
                print(f"✓ Exported {len(spans_response.spans)} spans")
            print(f"  File: error_trace_{trace_to_export.traceId[:8]}.json")
            
            return spans_response
        else:
            print("\n  No error traces found to export")
            return None
        
    except ClientAPIException as e:
        print(f"✗ API Error ({e.response.status_code}): {e}")
        return None




if __name__ == "__main__":
    # Example trace ID (replace with your actual trace ID)
    trace_id = "1234567890abcdef1234567890abcdef"
                
    print("\n" + "=" * 60)
    print("Watson Orchestrate Trace Export & Search Examples")
    print("=" * 60)
    print("\nThese examples show how to use TracesController")
    print("in your own Python scripts.")
    
    
    # Run export examples
    print("\n" + "=" * 60)
    print("PART 1: EXPORT EXAMPLES")
    print("=" * 60)
    example_basic_usage(trace_id)
    example_export_to_file(trace_id)
    example_custom_analysis(trace_id)
    
    # Run search examples
    print("\n" + "=" * 60)
    print("PART 2: SEARCH EXAMPLES")
    print("=" * 60)
    example_search_traces()
    example_search_and_export()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nKey points:")
    print("- Import TracesController from the CLI commands")
    print("- Controller methods return Python objects")
    print("- Use search_traces() to find trace IDs based on filters")
    print("- Use fetch_trace_spans() or export_trace_to_json() to get trace details")
    print("- Perfect for custom analysis, integrations, CI/CD")
