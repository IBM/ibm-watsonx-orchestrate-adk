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
from ibm_watsonx_orchestrate.client.observability.traces import TraceFilters, TraceSort
from datetime import datetime, timezone, timedelta


def example_basic_usage(trace_id):
    """
    Example 1: Fetch and analyze observations for a trace.
    """

    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    try:
        controller = TracesController()

        print(f"\nFetching observations for trace {trace_id}")
        obs_response = controller.fetch_trace_observations(trace_id)

        if obs_response.observations:
            print(f"✓ Fetched {len(obs_response.observations)} observations")
            print(f"  Total count: {obs_response.total_count}")

            # Analyse the observations
            generations = [o for o in obs_response.observations if o.type == "GENERATION"]
            print(f"  LLM calls (GENERATION): {len(generations)}")
        else:
            print("✗ No observations found")
            return None

        return obs_response

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

        print(f"\nExporting trace {trace_id} to file")
        obs_response, json_str = controller.export_trace_to_json(
            trace_id,
            output_file="my_trace.json",
            pretty=True
        )

        if obs_response.observations:
            print(f"✓ Exported {len(obs_response.observations)} observations to my_trace.json")
            print(f"  JSON string length: {len(json_str)} characters")

        return obs_response

    except ClientAPIException as e:
        print(f"✗ API Error ({e.response.status_code}): {e}")
        return None


def example_custom_analysis(trace_id):
    """
    Example 3: Custom trace analysis.
    """

    print("\n" + "=" * 60)
    print("Example 3: Custom Analysis")
    print("=" * 60)

    try:
        controller = TracesController()

        print(f"\nAnalyzing trace {trace_id}")
        obs_response = controller.fetch_trace_observations(trace_id)

        analysis = {
            'total_observations': 0,
            'by_type': {},
            'slow_observations': [],
        }

        if obs_response.observations:
            analysis['total_observations'] = len(obs_response.observations)

            for obs in obs_response.observations:
                # Count by type
                analysis['by_type'][obs.type] = analysis['by_type'].get(obs.type, 0) + 1

                # Find slow observations (> 1 second)
                try:
                    start = datetime.fromisoformat(obs.startTime.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(obs.endTime.replace('Z', '+00:00'))
                    duration_ms = (end - start).total_seconds() * 1000

                    if duration_ms > 1000:
                        analysis['slow_observations'].append({
                            'name': obs.name,
                            'duration_ms': round(duration_ms, 2)
                        })
                except Exception:
                    pass

        print(f"\n✓ Analysis complete:")
        print(f"  Total observations: {analysis['total_observations']}")
        print(f"  By type: {analysis['by_type']}")
        print(f"  Slow observations (>1s): {len(analysis['slow_observations'])}")

        if analysis['slow_observations']:
            print(f"\n  Slowest observations:")
            for slow in sorted(analysis['slow_observations'], key=lambda x: x['duration_ms'], reverse=True)[:3]:
                print(f"    - {slow['name']}: {slow['duration_ms']}ms")

        return analysis

    except ClientAPIException as e:
        print(f"✗ API Error ({e.response.status_code}): {e}")
        return None


def example_search_traces():
    """
    Example 4: Search for traces using filters.
    """
    print("\n" + "=" * 60)
    print("Example 4: Search for Traces")
    print("=" * 60)

    try:
        controller = TracesController()

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)

        filters = TraceFilters(
            start_time=start_time.isoformat().replace('+00:00', 'Z'),
            end_time=end_time.isoformat().replace('+00:00', 'Z'),
        )

        sort = TraceSort(field="start_time", direction="desc")

        print(f"\nSearching for traces from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
        search_response = controller.search_traces(
            filters=filters,
            sort=sort,
        )

        print(f"✓ Found {len(search_response.traceSummaries)} traces")

        if search_response.traceSummaries:
            print(f"\n  First 3 traces:")
            for trace in search_response.traceSummaries[:3]:
                print(f"    - Trace ID: {trace.traceId}")
                print(f"      Duration: {trace.durationMs}ms")
                agent_name = trace.agentNames[0] if trace.agentNames else 'N/A'
                print(f"      Agent: {agent_name}")

        return search_response

    except ClientAPIException as e:
        print(f"✗ API Error ({e.response.status_code}): {e}")
        return None


def example_search_and_export():
    """
    Example 5: Search for traces, then export them.
    """
    print("\n" + "=" * 60)
    print("Example 5: Search and Export Workflow")
    print("=" * 60)

    try:
        controller = TracesController()

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)

        filters = TraceFilters(
            start_time=start_time.isoformat().replace('+00:00', 'Z'),
            end_time=end_time.isoformat().replace('+00:00', 'Z')
        )

        print("\nStep 1: Searching for recent traces...")
        search_response = controller.search_traces(filters=filters)
        print(f"✓ Found {len(search_response.traceSummaries)} traces")

        if search_response.traceSummaries:
            trace_to_export = search_response.traceSummaries[0]
            print(f"\nStep 2: Exporting trace {trace_to_export.traceId[:16]}...")

            obs_response, json_str = controller.export_trace_to_json(
                trace_to_export.traceId,
                output_file=f"trace_{trace_to_export.traceId[:8]}.json",
                pretty=True
            )

            if obs_response.observations:
                print(f"✓ Exported {len(obs_response.observations)} observations")
            print(f"  File: trace_{trace_to_export.traceId[:8]}.json")

            return obs_response

        print("\n  No traces found to export")
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
    print("- Use fetch_trace_observations() or export_trace_to_json() to get trace details")
    print("- Perfect for custom analysis, integrations, CI/CD")
