"""Exporter factory for the observability tracer.

Builds the appropriate OpenTelemetry SpanExporter based on TracerConfig:
  * OTLP HTTP exporter when ``WXO_OTLP_ENDPOINT`` or trace_injection_url is set.
  * Includes authentication headers from AgenticSession or API key.
  * Console exporter as a fallback (with a warning).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace.export import SpanExporter

from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig

logger = logging.getLogger(__name__)

def create_exporter(config: TracerConfig) -> "SpanExporter":
    """Return a configured ``SpanExporter`` based on *config*.

    If ``WXO_OTLP_ENDPOINT`` or ``trace_injection_url`` is set, the OTLP/HTTP
    exporter is used with authentication headers from AgenticSession or API key.
    Otherwise a ``ConsoleSpanExporter`` is returned and a warning is logged.
    
    Args:
        config: TracerConfig with endpoint and authentication settings.
        
    Returns:
        Configured SpanExporter instance.
    """

    endpoint = config.endpoint

    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        # Get authentication headers
        headers = config.get_auth_headers()
        
        if headers:
            logger.debug("Using OTLP HTTP exporter -> %s (with authentication)", endpoint)
        else:
            logger.debug("Using OTLP HTTP exporter -> %s (no authentication)", endpoint)
        
        return OTLPSpanExporter(endpoint=endpoint, headers=headers)

    from opentelemetry.sdk.trace.export import ConsoleSpanExporter

    logger.warning(
        "WXO_OTLP_ENDPOINT is not set; traces will be printed to the console. "
        "Set the environment variable to export traces to an OTLP collector."
    )
    return ConsoleSpanExporter()
