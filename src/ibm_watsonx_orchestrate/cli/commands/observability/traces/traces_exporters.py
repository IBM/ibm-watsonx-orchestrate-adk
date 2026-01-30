import json

from typing import Optional
from datetime import datetime
from pathlib import Path

from ibm_watsonx_orchestrate.client.observability.traces.traces_client import SpansResponse


class TraceExporter:
    """
    Export trace data to JSON format.
    
    The JSON format is OpenTelemetry-compliant, making it compatible with third-party trace analysis tools.
    """
    
    @staticmethod
    def export_to_json(
        spans_response: SpansResponse,
        output_file: Optional[str] = None,
        pretty: bool = True
    ) -> str:
        """
        Export spans to JSON format.
        
        Exports the trace data in json format and can save it in an output file.
        
        Args:
            spans_response: Response containing spans from the API
            output_file: Optional file path to write to. If None, returns JSON string
            pretty: If True, format with indentation for readability
        
        Returns:
            JSON string representation of the trace data
        
        Example:
            ```python
            # Export to file
            exporter = TraceExporter()
            json_str = exporter.export_to_json(
                spans_response,
                output_file="trace_abc123.json",
                pretty=True
            )
            
            # Get JSON string for further processing
            json_str = exporter.export_to_json(spans_response, pretty=False)
            data = json.loads(json_str)
            ```
        """
        if spans_response.traceData: # return raw traceData
            data = {
                "traceData": spans_response.traceData.model_dump(),
                "total_count": spans_response.totalCount,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "format": "traceData"
            }
        elif spans_response.spans: # convert spans array
            data = {
                "spans": [span.model_dump() for span in spans_response.spans],
                "total_count": spans_response.totalCount,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "format": "spans"
            }
        else: # no data
            data = {
                "error": "No trace data available",
                "exported_at": datetime.utcnow().isoformat() + "Z"
            }
        
        # Add trace_id for convenience
        if spans_response.spans and len(spans_response.spans) > 0:
            data["trace_id"] = spans_response.spans[0].context.trace_id
        
        json_str = json.dumps(data, indent=2 if pretty else None)
        
        if output_file:
            Path(output_file).write_text(json_str, encoding='utf-8')
        
        return json_str
