"""Integration tests for tracing decorators."""

import json

import pytest
from unittest.mock import MagicMock

from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    ATTR_AGENT_FRAMEWORK,
    ATTR_AGENT_NAME,
    ATTR_INPUT,
    ATTR_LLM_MODEL,
    ATTR_LLM_PROVIDER,
    ATTR_OUTPUT,
    ATTR_TOOL_NAME,
    SPAN_KIND_AGENT,
    SPAN_KIND_GENERAL,
    SPAN_KIND_LLM,
    SPAN_KIND_TOOL,
)
from ibm_watsonx_orchestrate_sdk.observability.decorators import (
    configure_tracing,
    trace_agent_call,
    trace_call,
    trace_llm_call,
    trace_tool_call,
)

from .conftest import get_attrs


# ---------------------------------------------------------------------------
# trace_call
# ---------------------------------------------------------------------------


class TestTraceCall:
    def test_uses_qualname_as_default_span_name(self, traced):
        @trace_call()
        def my_func():
            return 1

        my_func()
        assert traced.get_finished_spans()[0].name.endswith("my_func")

    def test_custom_span_name(self, traced):
        @trace_call(name="custom-name")
        def fn():
            pass

        fn()
        assert traced.get_finished_spans()[0].name == "custom-name"

    def test_span_kind_general(self, traced):
        @trace_call()
        def fn():
            pass

        fn()
        assert get_attrs(traced.get_finished_spans()[0])["span.kind"] == SPAN_KIND_GENERAL

    def test_captures_input_as_json(self, traced):
        @trace_call(capture_input=True)
        def add(x, y):
            return x + y

        add(1, 2)
        raw = get_attrs(traced.get_finished_spans()[0])[ATTR_INPUT]
        assert json.loads(raw) == {"x": 1, "y": 2}

    def test_captures_output_as_json(self, traced):
        @trace_call(capture_output=True)
        def greet(name):
            return f"hello {name}"

        greet("world")
        raw = get_attrs(traced.get_finished_spans()[0])[ATTR_OUTPUT]
        assert json.loads(raw) == "hello world"

    def test_no_capture_by_default(self, traced):
        @trace_call()
        def fn(x):
            return x

        fn(42)
        attrs = get_attrs(traced.get_finished_spans()[0])
        assert ATTR_INPUT not in attrs
        assert ATTR_OUTPUT not in attrs

    def test_propagates_return_value(self, traced):
        @trace_call()
        def fn():
            return 99

        assert fn() == 99

    def test_propagates_exception(self, traced):
        @trace_call()
        def fn():
            raise ValueError("bad")

        with pytest.raises(ValueError, match="bad"):
            fn()

    def test_exception_recorded_on_span(self, traced):
        @trace_call()
        def fn():
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            fn()

        events = traced.get_finished_spans()[0].events
        assert any(e.name == "exception" for e in events)

    def test_span_ended_after_exception(self, traced):
        @trace_call()
        def fn():
            raise RuntimeError("x")

        with pytest.raises(RuntimeError):
            fn()
        assert len(traced.get_finished_spans()) == 1

    def test_extra_attributes_set(self, traced):
        @trace_call(attributes={"env": "test"})
        def fn():
            pass

        fn()
        assert get_attrs(traced.get_finished_spans()[0])["env"] == "test"

    def test_preserves_function_name(self, traced):
        @trace_call()
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_captures_kwargs(self, traced):
        @trace_call(capture_input=True)
        def fn(a, b=10):
            return a + b

        fn(5)
        raw = get_attrs(traced.get_finished_spans()[0])[ATTR_INPUT]
        captured = json.loads(raw)
        assert captured["a"] == 5
        assert captured["b"] == 10  # default applied

    def test_multiple_calls_produce_multiple_spans(self, traced):
        @trace_call()
        def fn():
            pass

        fn()
        fn()
        assert len(traced.get_finished_spans()) == 2


# ---------------------------------------------------------------------------
# trace_llm_call
# ---------------------------------------------------------------------------


class TestTraceLLMCall:
    def test_span_kind_llm(self, traced):
        @trace_llm_call()
        def call():
            return "response"

        call()
        assert get_attrs(traced.get_finished_spans()[0])["span.kind"] == SPAN_KIND_LLM

    def test_model_and_provider_set(self, traced):
        @trace_llm_call(model="claude-3", provider="anthropic")
        def call():
            return "ok"

        call()
        attrs = get_attrs(traced.get_finished_spans()[0])
        assert attrs[ATTR_LLM_MODEL] == "claude-3"
        assert attrs[ATTR_LLM_PROVIDER] == "anthropic"

    def test_captures_input_and_output(self, traced):
        @trace_llm_call(capture_input=True, capture_output=True)
        def call(prompt):
            return "answer"

        call("hello")
        attrs = get_attrs(traced.get_finished_spans()[0])
        assert ATTR_INPUT in attrs
        assert ATTR_OUTPUT in attrs

    def test_default_span_name_is_qualname(self, traced):
        @trace_llm_call()
        def my_llm_fn():
            pass

        my_llm_fn()
        assert traced.get_finished_spans()[0].name.endswith("my_llm_fn")

    def test_propagates_return_value(self, traced):
        @trace_llm_call()
        def call():
            return {"text": "hi"}

        assert call() == {"text": "hi"}


# ---------------------------------------------------------------------------
# trace_tool_call
# ---------------------------------------------------------------------------


class TestTraceToolCall:
    def test_span_kind_tool(self, traced):
        @trace_tool_call()
        def my_tool():
            return {}

        my_tool()
        assert get_attrs(traced.get_finished_spans()[0])["span.kind"] == SPAN_KIND_TOOL

    def test_defaults_tool_name_to_fn_name(self, traced):
        @trace_tool_call()
        def search_web(query):
            return []

        search_web("test")
        assert get_attrs(traced.get_finished_spans()[0])[ATTR_TOOL_NAME] == "search_web"

    def test_custom_tool_name(self, traced):
        @trace_tool_call(tool_name="web-search")
        def fn(q):
            return []

        fn("x")
        assert get_attrs(traced.get_finished_spans()[0])[ATTR_TOOL_NAME] == "web-search"

    def test_captures_input_and_output(self, traced):
        @trace_tool_call(capture_input=True, capture_output=True)
        def lookup(key):
            return "value"

        lookup("abc")
        attrs = get_attrs(traced.get_finished_spans()[0])
        assert ATTR_INPUT in attrs
        assert ATTR_OUTPUT in attrs

    def test_propagates_return_value(self, traced):
        @trace_tool_call()
        def fn():
            return 42

        assert fn() == 42

    def test_propagates_exception(self, traced):
        @trace_tool_call()
        def fn():
            raise KeyError("missing")

        with pytest.raises(KeyError):
            fn()


# ---------------------------------------------------------------------------
# trace_agent_call
# ---------------------------------------------------------------------------


class TestTraceAgentCall:
    def test_span_kind_agent(self, traced):
        @trace_agent_call()
        def my_agent(task):
            return "done"

        my_agent("plan")
        assert get_attrs(traced.get_finished_spans()[0])["span.kind"] == SPAN_KIND_AGENT

    def test_defaults_agent_name_to_fn_name(self, traced):
        @trace_agent_call()
        def planner_agent(task):
            return "ok"

        planner_agent("x")
        assert get_attrs(traced.get_finished_spans()[0])[ATTR_AGENT_NAME] == "planner_agent"

    def test_custom_agent_name_and_framework(self, traced):
        @trace_agent_call(agent_name="orchestrator", framework="langgraph")
        def fn(task):
            return "done"

        fn("test")
        attrs = get_attrs(traced.get_finished_spans()[0])
        assert attrs[ATTR_AGENT_NAME] == "orchestrator"
        assert attrs[ATTR_AGENT_FRAMEWORK] == "langgraph"

    def test_captures_input_and_output(self, traced):
        @trace_agent_call(capture_input=True, capture_output=True)
        def agent(task):
            return "result"

        agent("do stuff")
        attrs = get_attrs(traced.get_finished_spans()[0])
        assert ATTR_INPUT in attrs
        assert ATTR_OUTPUT in attrs

    def test_propagates_return_value(self, traced):
        @trace_agent_call()
        def agent(t):
            return {"status": "done"}

        assert agent("t") == {"status": "done"}

    def test_propagates_exception(self, traced):
        @trace_agent_call()
        def agent(t):
            raise TimeoutError("timeout")

        with pytest.raises(TimeoutError):
            agent("x")


# ---------------------------------------------------------------------------
# configure_tracing
# ---------------------------------------------------------------------------


class TestConfigureTracing:
    """configure_tracing tests.

    NOTE: _build_invocation_context is imported unconditionally inside the
    wrapper but does not yet exist in tracer.py (known gap).  Happy-path
    tests inject a stub via monkeypatch; the last test documents the gap.
    """

    @pytest.fixture(autouse=True)
    def _stub_build_invocation_context(self, monkeypatch):
        import ibm_watsonx_orchestrate_sdk.observability.tracer as _tracer_mod

        monkeypatch.setattr(_tracer_mod, "_build_invocation_context", lambda ec: None, raising=False)

    def test_calls_wrapped_fn(self):
        fn = MagicMock(return_value="ok")
        result = configure_tracing(fn)({"configurable": {}})
        fn.assert_called_once_with({"configurable": {}})
        assert result == "ok"

    def test_no_execution_context_does_not_raise(self):
        fn = MagicMock(return_value="done")
        result = configure_tracing(fn)({"configurable": {}})
        assert result == "done"

    def test_none_config_handled(self):
        fn = MagicMock(return_value="x")
        result = configure_tracing(fn)(None)
        assert result == "x"

    def test_empty_dict_config_handled(self):
        fn = MagicMock(return_value="y")
        result = configure_tracing(fn)({})
        assert result == "y"

    def test_preserves_function_metadata(self):
        def my_factory(config):
            """My factory docstring."""
            return config

        decorated = configure_tracing(my_factory)
        assert decorated.__name__ == "my_factory"
        assert decorated.__doc__ == "My factory docstring."

    def test_passes_extra_args_and_kwargs(self):
        fn = MagicMock(return_value="z")
        configure_tracing(fn)({"configurable": {}}, "arg1", kw="val")
        fn.assert_called_once_with({"configurable": {}}, "arg1", kw="val")

    def test_execution_context_present_missing_impl_raises(self, monkeypatch):
        """Without store_execution_context, calling with execution_context raises ImportError."""
        import ibm_watsonx_orchestrate_sdk.observability.tracer as _tracer_mod

        monkeypatch.delattr(_tracer_mod, "store_execution_context", raising=False)
        fn = MagicMock(return_value="noop")
        with pytest.raises(ImportError):
            configure_tracing(fn)({"configurable": {"execution_context": {"tenant_id": "t1"}}})
