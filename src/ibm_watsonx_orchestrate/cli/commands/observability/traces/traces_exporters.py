import json

from typing import Optional
from datetime import datetime
from pathlib import Path

from ibm_watsonx_orchestrate.client.observability.traces.traces_client import ObservationsExportResponse


class TraceExporter:
    """
    Export trace data to JSON format.
    """

    @staticmethod
    def export_to_json(
        observations_response: ObservationsExportResponse,
        output_file: Optional[str] = None,
        pretty: bool = True
    ) -> str:
        """
        Export observations to JSON format.

        Exports the trace data in JSON format and can save it to an output file.

        Args:
            observations_response: Response containing observations from the API
            output_file: Optional file path to write to. If None, returns JSON string
            pretty: If True, format with indentation for readability

        Returns:
            JSON string representation of the trace data

        Example:
            ```python
            # Export to file
            exporter = TraceExporter()
            json_str = exporter.export_to_json(
                observations_response,
                output_file="trace_abc123.json",
                pretty=True
            )

            # Get JSON string for further processing
            json_str = exporter.export_to_json(observations_response, pretty=False)
            data = json.loads(json_str)
            ```
        """
        if observations_response.observations:
            data = {
                "observations": [obs.model_dump() for obs in observations_response.observations],
                "total_count": observations_response.totalCount,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "format": "observations"
            }
            # Add trace_id from first observation
            if len(observations_response.observations) > 0:
                data["trace_id"] = observations_response.observations[0].traceId
        else:
            data = {
                "error": "No trace data available",
                "exported_at": datetime.utcnow().isoformat() + "Z"
            }

        json_str = json.dumps(data, indent=2 if pretty else None)

        if output_file:
            Path(output_file).write_text(json_str, encoding='utf-8')

        return json_str
