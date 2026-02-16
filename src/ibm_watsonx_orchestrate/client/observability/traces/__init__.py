"""Traces client for IBM Watson Orchestrate observability platform."""

from ibm_watsonx_orchestrate.client.observability.traces.traces_client import (
    TracesClient,
    Span,
    SpanContext,
    SpanStatus,
    SpanEvent,
    SpansResponse,
    TraceFilters,
    TraceSort,
    TraceSearchRequest,
    TraceSearchResponse,
    TraceSummary,
    RootSpan,
    SpanCountRange
)

__all__ = [
    'TracesClient',
    'Span',
    'SpanContext',
    'SpanStatus',
    'SpanEvent',
    'SpansResponse',
    'TraceFilters',
    'TraceSort',
    'TraceSearchRequest',
    'TraceSearchResponse',
    'TraceSummary',
    'RootSpan',
    'SpanCountRange'
]
