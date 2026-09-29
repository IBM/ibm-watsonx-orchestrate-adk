"""Exporter factory for the observability tracer.

Builds the appropriate OpenTelemetry SpanExporter based on TracerConfig:
  * OTLP HTTP exporter when ``WXO_OTLP_ENDPOINT`` or trace_injection_url is set.
  * Includes authentication headers from AgenticSession or API key.
  * Supports dynamic token refresh for long-running applications.
  * Propagates ``session.verify`` so CPD on-prem self-signed certificates are
    accepted without any monkey-patching.
  * Console exporter as a fallback (with a warning).
"""

from __future__ import annotations

import logging
import ssl as _ssl
import threading
from typing import TYPE_CHECKING, Any, Sequence
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan

from ibm_watsonx_orchestrate_sdk.observability.config import TracerConfig

logger = logging.getLogger(__name__)


def _apply_ssl_verify(exporter: Any, ssl_verify: "bool | str | None") -> None:
    """Propagate *ssl_verify* to the OTLP exporter's internal transport.

    No-ops when *ssl_verify* is ``True`` (library default is already correct).
    Probes three transport layouts across known OTLP library versions:
    v0.66b0+ (urllib3 pool), mid (_transport.verify), older (_session.verify).
    Logs a warning if none match.
    """
    # Only act when explicitly disabling verification or supplying a CA bundle.
    # True means "use library default" — no mutation needed.
    if ssl_verify is True:
        return

    applied = False

    # v0.66b0+: urllib3 PoolManager nested inside _client._transport
    client_transport = getattr(getattr(exporter, "_client", None), "_transport", None)
    if client_transport is not None:
        pool = getattr(client_transport, "_pool", None)
        if pool is not None:
            kw = getattr(pool, "connection_pool_kw", None)
            if kw is not None:
                if ssl_verify is False:
                    kw["cert_reqs"] = _ssl.CERT_NONE
                    kw.pop("ca_certs", None)
                elif isinstance(ssl_verify, str):
                    kw["ca_certs"] = ssl_verify
                applied = True

    # mid versions: exporter._transport.verify or ._transport._session.verify
    exporter_transport = getattr(exporter, "_transport", None)
    if exporter_transport is not None:
        if hasattr(exporter_transport, "verify"):
            exporter_transport.verify = ssl_verify
            applied = True
        inner_session = getattr(exporter_transport, "_session", None)
        if inner_session is not None and hasattr(inner_session, "verify"):
            inner_session.verify = ssl_verify
            applied = True

    # older versions: exporter._session.verify directly
    direct_session = getattr(exporter, "_session", None)
    if direct_session is not None and hasattr(direct_session, "verify"):
        direct_session.verify = ssl_verify
        applied = True

    if not applied:
        logger.warning(
            "Could not apply ssl_verify=%r to OTLP exporter: "
            "no recognised transport attribute found. "
            "Trace export may fail with SSL errors on CPD on-prem environments.",
            ssl_verify,
        )


class DynamicAuthOTLPSpanExporter(SpanExporter):
    """OTLP Span Exporter wrapper that refreshes authentication tokens dynamically.

    This wrapper delegates to the standard OTLPSpanExporter but updates the
    Authorization header before each export to ensure tokens are fresh.
    This is essential for long-running applications where tokens may expire.

    Thread-safe: a lock serialises header mutation so that concurrent exports
    do not race on the underlying session headers dict.  The token is copied
    under the lock and the (slow) network export is performed outside it so
    that high-throughput callers are not serialised on I/O.

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
        # Fetch initial headers; if that fails the exporter is still created
        # without auth headers so construction never raises.
        try:
            initial_headers = config.get_auth_headers()
        except Exception as exc:
            logger.warning(
                "Failed to fetch initial authentication headers; "
                "exporter will be created without auth headers: %s",
                exc,
            )
            initial_headers = {}
        self._exporter: Any = OTLPSpanExporter(endpoint=endpoint, headers=initial_headers)
        if config.ssl_verify is not None:
            _apply_ssl_verify(self._exporter, config.ssl_verify)
        logger.debug(
            "Created DynamicAuthOTLPSpanExporter for endpoint: %s (ssl_verify=%r)",
            endpoint, config.ssl_verify,
        )

    def export(self, spans: Sequence["ReadableSpan"]) -> SpanExportResult:
        """Export spans with dynamically refreshed authentication token.

        The header mutation is performed under the lock so concurrent callers
        cannot interleave stale and fresh header updates on the shared
        ``requests.Session``.  The actual network export is intentionally
        outside the lock: ``requests.Session`` connection pools are
        thread-safe for concurrent sends, so serialising the slow I/O call
        is unnecessary and would hurt throughput.

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
                try:
                    self._exporter._session.headers.update(fresh_headers)
                    logger.debug("Refreshed authentication token for span export")
                except Exception as exc:
                    logger.warning(
                        "Failed to update session headers with refreshed token: %s. "
                        "Proceeding with previously cached credentials.",
                        exc,
                    )

        # Export outside the lock: the requests.Session connection pool is
        # thread-safe for concurrent requests; only the header mutation above
        # required serialisation.
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

            exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
            if config.ssl_verify is not None:
                _apply_ssl_verify(exporter, config.ssl_verify)
            return exporter

    from opentelemetry.sdk.trace.export import ConsoleSpanExporter

    logger.warning(
        "WXO_OTLP_ENDPOINT is not set; traces will be logged to the console. "
        "Set the environment variable to export traces to an OTLP collector."
    )
    return ConsoleSpanExporter()
