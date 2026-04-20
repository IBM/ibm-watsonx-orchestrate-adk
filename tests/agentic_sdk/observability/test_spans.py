"""Unit tests for SpanWrapper and its subclasses.

All OTel spans are replaced with MagicMock so these tests run without a
real TracerProvider.
"""

import json

import pytest
from opentelemetry.trace import StatusCode
from unittest.mock import MagicMock

from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    ATTR_AGENT_FRAMEWORK,
    ATTR_AGENT_NAME,
    ATTR_AGENT_OUTPUT,
    ATTR_LLM_COMPLETION_TOKENS,
    ATTR_LLM_MODEL,
    ATTR_LLM_PROMPT_TOKENS,
    ATTR_LLM_PROVIDER,
    ATTR_LLM_RESPONSE_MODEL,
    ATTR_LLM_STOP_REASON,
    ATTR_LLM_TOTAL_TOKENS,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTPUT,
)
from ibm_watsonx_orchestrate_sdk.observability.spans import (
    AgentSpanWrapper,
    LLMSpanWrapper,
    SpanWrapper,
    ToolSpanWrapper,
    _safe_json,
)


def make_span(name="test-span"):
    span = MagicMock()
    span.name = name
    return span


def recorded_attrs(span) -> set:
    """Return the set of (key, value) tuples passed to set_attribute."""
    return {c.args for c in span.set_attribute.call_args_list}


# ---------------------------------------------------------------------------
# _safe_json
# ---------------------------------------------------------------------------


class TestSafeJson:
    def test_simple_dict(self):
        result = _safe_json({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_list(self):
        assert json.loads(_safe_json([1, 2, 3])) == [1, 2, 3]

    def test_none(self):
        assert _safe_json(None) == "null"

    def test_non_serializable_falls_back_to_str(self):
        class Unserializable:
            def __repr__(self):
                return "<Unserializable>"

        result = _safe_json(Unserializable())
        assert isinstance(result, str)

    def test_nested_non_serializable_uses_default_str(self):
        import datetime

        result = _safe_json({"ts": datetime.datetime(2024, 1, 1)})
        assert "2024" in result


# ---------------------------------------------------------------------------
# SpanWrapper
# ---------------------------------------------------------------------------


class TestSpanWrapper:
    def test_enter_returns_self(self):
        span = make_span()
        wrapper = SpanWrapper(span)
        assert wrapper.__enter__() is wrapper

    def test_exit_ends_span_normally(self):
        span = make_span()
        with SpanWrapper(span):
            pass
        span.end.assert_called_once()

    def test_exit_does_not_suppress_exception(self):
        span = make_span()
        result = SpanWrapper(span).__exit__(ValueError, ValueError("x"), None)
        assert not result

    def test_exit_records_exception_on_span(self):
        span = make_span()
        wrapper = SpanWrapper(span)
        wrapper.__enter__()
        exc = ValueError("boom")
        wrapper.__exit__(ValueError, exc, None)
        span.record_exception.assert_called_once_with(exc)

    def test_exit_sets_error_status_on_exception(self):
        span = make_span()
        wrapper = SpanWrapper(span)
        wrapper.__enter__()
        wrapper.__exit__(RuntimeError, RuntimeError("fail"), None)
        status = span.set_status.call_args[0][0]
        assert status.status_code == StatusCode.ERROR

    def test_exit_does_not_record_exception_when_clean(self):
        span = make_span()
        with SpanWrapper(span):
            pass
        span.record_exception.assert_not_called()

    def test_set_attribute_delegates(self):
        span = make_span()
        SpanWrapper(span).set_attribute("k", "v")
        span.set_attribute.assert_called_once_with("k", "v")

    def test_set_attributes_sets_each(self):
        span = make_span()
        SpanWrapper(span).set_attributes({"a": 1, "b": 2})
        attrs = recorded_attrs(span)
        assert ("a", 1) in attrs
        assert ("b", 2) in attrs

    def test_add_event_delegates(self):
        span = make_span()
        SpanWrapper(span).add_event("evt", {"x": 1})
        span.add_event.assert_called_once_with("evt", attributes={"x": 1})

    def test_add_event_no_attributes(self):
        span = make_span()
        SpanWrapper(span).add_event("evt")
        span.add_event.assert_called_once_with("evt", attributes=None)

    def test_set_status_ok(self):
        span = make_span()
        SpanWrapper(span).set_status_ok()
        status = span.set_status.call_args[0][0]
        assert status.status_code == StatusCode.OK

    def test_set_status_error(self):
        span = make_span()
        SpanWrapper(span).set_status_error("something failed")
        status = span.set_status.call_args[0][0]
        assert status.status_code == StatusCode.ERROR

    def test_context_manager_ends_span_after_body(self):
        span = make_span()
        with SpanWrapper(span) as s:
            span.end.assert_not_called()
            assert s._span is span
        span.end.assert_called_once()


# ---------------------------------------------------------------------------
# LLMSpanWrapper
# ---------------------------------------------------------------------------


class TestLLMSpanWrapper:
    def test_sets_model_and_provider_on_init(self):
        span = make_span()
        LLMSpanWrapper(span, model="gpt-4", provider="openai")
        attrs = recorded_attrs(span)
        assert (ATTR_LLM_MODEL, "gpt-4") in attrs
        assert (ATTR_LLM_PROVIDER, "openai") in attrs

    def test_skips_none_model_and_provider(self):
        span = make_span()
        LLMSpanWrapper(span)
        span.set_attribute.assert_not_called()

    def test_record_completion_all_fields(self):
        span = make_span()
        LLMSpanWrapper(span).record_completion(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            response_model="gpt-4-0613",
            stop_reason="stop",
        )
        attrs = recorded_attrs(span)
        assert (ATTR_LLM_PROMPT_TOKENS, 10) in attrs
        assert (ATTR_LLM_COMPLETION_TOKENS, 20) in attrs
        assert (ATTR_LLM_TOTAL_TOKENS, 30) in attrs
        assert (ATTR_LLM_RESPONSE_MODEL, "gpt-4-0613") in attrs
        assert (ATTR_LLM_STOP_REASON, "stop") in attrs

    def test_record_completion_auto_sums_total(self):
        span = make_span()
        LLMSpanWrapper(span).record_completion(prompt_tokens=100, completion_tokens=50)
        attrs = recorded_attrs(span)
        assert (ATTR_LLM_TOTAL_TOKENS, 150) in attrs

    def test_record_completion_no_total_when_only_prompt(self):
        span = make_span()
        LLMSpanWrapper(span).record_completion(prompt_tokens=100)
        keys = [c.args[0] for c in span.set_attribute.call_args_list]
        assert ATTR_LLM_TOTAL_TOKENS not in keys

    def test_record_completion_no_total_when_only_completion(self):
        span = make_span()
        LLMSpanWrapper(span).record_completion(completion_tokens=50)
        keys = [c.args[0] for c in span.set_attribute.call_args_list]
        assert ATTR_LLM_TOTAL_TOKENS not in keys

    def test_record_completion_explicit_total_takes_precedence(self):
        span = make_span()
        LLMSpanWrapper(span).record_completion(
            prompt_tokens=10, completion_tokens=20, total_tokens=999
        )
        attrs = recorded_attrs(span)
        assert (ATTR_LLM_TOTAL_TOKENS, 999) in attrs

    def test_record_completion_no_fields_sets_nothing(self):
        span = make_span()
        LLMSpanWrapper(span).record_completion()
        span.set_attribute.assert_not_called()


# ---------------------------------------------------------------------------
# ToolSpanWrapper
# ---------------------------------------------------------------------------


class TestToolSpanWrapper:
    def test_sets_tool_name(self):
        span = make_span()
        ToolSpanWrapper(span, tool_name="search")
        assert (ATTR_TOOL_NAME, "search") in recorded_attrs(span)

    def test_serializes_tool_input_as_json(self):
        span = make_span()
        ToolSpanWrapper(span, tool_input={"query": "hello"})
        attrs = recorded_attrs(span)
        input_vals = {v for k, v in attrs if k == ATTR_TOOL_INPUT}
        assert any('"query"' in v for v in input_vals)

    def test_tool_input_none_not_set(self):
        span = make_span()
        ToolSpanWrapper(span, tool_name="x")
        keys = [c.args[0] for c in span.set_attribute.call_args_list]
        assert ATTR_TOOL_INPUT not in keys

    def test_no_args_sets_nothing(self):
        span = make_span()
        ToolSpanWrapper(span)
        span.set_attribute.assert_not_called()

    def test_record_result_serializes_output(self):
        span = make_span()
        ToolSpanWrapper(span).record_result({"answer": 42})
        attrs = recorded_attrs(span)
        output_vals = {v for k, v in attrs if k == ATTR_TOOL_OUTPUT}
        assert any("42" in v for v in output_vals)

    def test_record_result_string(self):
        span = make_span()
        ToolSpanWrapper(span).record_result("success")
        attrs = recorded_attrs(span)
        assert any(v == '"success"' for k, v in attrs if k == ATTR_TOOL_OUTPUT)


# ---------------------------------------------------------------------------
# AgentSpanWrapper
# ---------------------------------------------------------------------------


class TestAgentSpanWrapper:
    def test_sets_agent_name_and_framework(self):
        span = make_span()
        AgentSpanWrapper(span, agent_name="planner", framework="langgraph")
        attrs = recorded_attrs(span)
        assert (ATTR_AGENT_NAME, "planner") in attrs
        assert (ATTR_AGENT_FRAMEWORK, "langgraph") in attrs

    def test_no_args_sets_nothing(self):
        span = make_span()
        AgentSpanWrapper(span)
        span.set_attribute.assert_not_called()

    def test_record_result_serializes_output(self):
        span = make_span()
        AgentSpanWrapper(span).record_result("task done")
        attrs = recorded_attrs(span)
        output_vals = {v for k, v in attrs if k == ATTR_AGENT_OUTPUT}
        assert any("task done" in v for v in output_vals)

    def test_record_result_dict(self):
        span = make_span()
        AgentSpanWrapper(span).record_result({"status": "ok"})
        attrs = recorded_attrs(span)
        output_vals = {v for k, v in attrs if k == ATTR_AGENT_OUTPUT}
        assert any('"ok"' in v for v in output_vals)
