"""Exporter factory for the observability tracer.

Builds the appropriate OpenTelemetry SpanExporter based on TracerConfig:
  * OTLP HTTP exporter when ``WXO_OTLP_ENDPOINT`` is set.
  * Console exporter as a fallback (with a warning).
"""

import logging

from opentelemetry.sdk.trace.export import SpanExporter

from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig

logger = logging.getLogger(__name__)

def create_exporter(config: TracerConfig) -> "SpanExporter":
    """Return a configured ``SpanExporter`` based on *config*.

    If ``WXO_OTLP_ENDPOINT`` is set the OTLP/HTTP exporter is used;
    otherwise a ``ConsoleSpanExporter`` is returned and a warning is logged.
    """

    endpoint = config.endpoint

    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        logger.debug("Using OTLP HTTP exporter -> %s", endpoint)
        return OTLPSpanExporter(endpoint=endpoint)

    from opentelemetry.sdk.trace.export import ConsoleSpanExporter

    logger.warning(
        "WXO_OTLP_ENDPOINT is not set; traces will be printed to the console. "
        "Set the environment variable to export traces to an OTLP collector."
    )
    return ConsoleSpanExporter()
