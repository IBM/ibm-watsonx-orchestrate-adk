"""Exporter factory for the observability tracer.

Builds the appropriate OpenTelemetry SpanExporter based on TracerConfig:
  * OTLP HTTP exporter when ``WXO_OTLP_ENDPOINT`` or trace_injection_url is set.
  * Includes authentication headers from AgenticSession or API key.
  * Supports dynamic token refresh for long-running applications.
  * Console exporter as a fallback (with a warning).
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any, Sequence
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan

from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig

logger = logging.getLogger(__name__)


class DynamicAuthOTLPSpanExporter(SpanExporter):
    """OTLP Span Exporter wrapper that refreshes authentication tokens dynamically.

    This wrapper delegates to the standard OTLPSpanExporter but updates the
    Authorization header before each export to ensure tokens are fresh.
    This is essential for long-running applications where tokens may expire.

    Thread-safe: a lock serialises header updates so that concurrent exports
    do not race on the underlying session headers dict.

    Implements the SpanExporter protocol from OpenTelemetry SDK.

    Args:
        endpoint: OTLP endpoint URL
        config: TracerConfig instance for dynamic token retrieval
    """

    def __init__(self, endpoint: str, config: TracerConfig):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        self._endpoint = endpoint
        self._config = config
        self._lock = threading.Lock()
        # Create base exporter with initial headers
        initial_headers = config.get_auth_headers()
        self._exporter: Any = OTLPSpanExporter(endpoint=endpoint, headers=initial_headers)
        logger.debug("Created DynamicAuthOTLPSpanExporter for endpoint: %s", endpoint)

    def export(self, spans: Sequence["ReadableSpan"]) -> SpanExportResult:
        """Export spans with dynamically refreshed authentication token.

        The header refresh and the export are serialised under a lock so
        concurrent callers cannot interleave a stale header update with a
        fresh one on the shared ``requests.Session``.

        Args:
            spans: Sequence of spans to export

        Returns:
            SpanExportResult indicating success or failure
        """
        with self._lock:
            try:
                fresh_headers = self._config.get_auth_headers()
            except Exception as exc:
                logger.warning(
                    "Failed to refresh authentication token before export: %s. "
                    "Proceeding with previously cached credentials.",
                    exc,
                )
                fresh_headers = None

            # Update the exporter's session headers (OTLPSpanExporter uses requests.Session)
            if fresh_headers and hasattr(self._exporter, "_session") and self._exporter._session:
                self._exporter._session.headers.update(fresh_headers)
                logger.debug("Refreshed authentication token for span export")

        return self._exporter.export(spans)

    def shutdown(self) -> None:
        """Shutdown the underlying exporter."""
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the underlying exporter.

        Args:
            timeout_millis: Timeout in milliseconds

        Returns:
            True if flush succeeded, False otherwise
        """
        return self._exporter.force_flush(timeout_millis)


def create_exporter(config: TracerConfig) -> Any:
    """Return a configured ``SpanExporter`` based on *config*.

    If ``WXO_OTLP_ENDPOINT`` or ``trace_injection_url`` is set, the OTLP/HTTP
    exporter is used with authentication headers from AgenticSession or API key.

    For configurations with dynamic authentication (Client with authenticator),
    a DynamicAuthOTLPSpanExporter is used to refresh tokens automatically.

    Otherwise a ``ConsoleSpanExporter`` is returned and a warning is logged.

    Args:
        config: TracerConfig with endpoint and authentication settings.

    Returns:
        Configured SpanExporter instance with dynamic token refresh support.
        Returns SpanExporter or DynamicAuthOTLPSpanExporter (both implement the protocol).
    """

    endpoint = config.endpoint

    if endpoint:
        # Check if we need dynamic token refresh
        needs_dynamic_auth = (
            config.session is not None and
            config.session.authenticator is not None
        )

        if needs_dynamic_auth:
            logger.debug(
                "Using OTLP HTTP exporter with dynamic token refresh -> %s",
                endpoint
            )
            return DynamicAuthOTLPSpanExporter(endpoint=endpoint, config=config)
        else:
            # Static authentication (access_token or no auth)
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            headers = config.get_auth_headers()

            if headers:
                logger.debug("Using OTLP HTTP exporter -> %s (with static authentication)", endpoint)
            else:
                logger.debug("Using OTLP HTTP exporter -> %s (no authentication)", endpoint)

            return OTLPSpanExporter(endpoint=endpoint, headers=headers)

    from opentelemetry.sdk.trace.export import ConsoleSpanExporter

    logger.warning(
        "WXO_OTLP_ENDPOINT is not set; traces will be logged to the console. "
        "Set the environment variable to export traces to an OTLP collector."
    )
    return ConsoleSpanExporter()
