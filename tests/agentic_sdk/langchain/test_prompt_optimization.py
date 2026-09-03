from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ibm_watsonx_orchestrate_sdk.langchain.prompt_optimization import (
    _extract_directives,
    _get_text,
    _is_system,
    _ManagedGraph,
)


DEFAULT_PROMPT = "You are a default agent."


def _make_managed_graph(active_prompt=None, candidate=None):
    inner = MagicMock()
    inner.invoke = MagicMock(return_value={"messages": [AIMessage(content="ok")]})

    client = MagicMock()
    client.active_prompt = active_prompt
    client.connect = MagicMock()
    client.load_active_prompt = MagicMock()
    client.fetch_candidate = MagicMock(return_value=candidate)

    graph = _ManagedGraph.__new__(_ManagedGraph)
    graph._graph = inner
    graph._default = DEFAULT_PROMPT
    graph._client = client
    return graph


# -- _get_text --


def test_get_text_from_tuple():
    assert _get_text(("user", "hello")) == "hello"


def test_get_text_from_message_object():
    assert _get_text(HumanMessage(content="hi")) == "hi"


def test_get_text_from_dict():
    assert _get_text({"content": "hey"}) == "hey"
    assert _get_text({"text": "hey"}) == "hey"


def test_get_text_returns_none_for_unknown():
    assert _get_text(42) is None


# -- _is_system --


def test_is_system_with_system_message():
    assert _is_system(SystemMessage(content="sys")) is True


def test_is_system_with_tuple():
    assert _is_system(("system", "sys")) is True


def test_is_system_with_human():
    assert _is_system(HumanMessage(content="hi")) is False
    assert _is_system(("user", "hi")) is False


# -- _extract_directives --


def test_extract_directives_parses_and_strips():
    msgs = [("user", "hello [agentops:refresh-prompt] world")]
    result = _extract_directives(msgs)
    assert result == {"refresh-prompt": None}
    assert msgs[0][1] == "hello  world"


def test_extract_directives_with_value():
    msgs = [("user", "[agentops:optimization-run-id=run-42]")]
    result = _extract_directives(msgs)
    assert result == {"optimization-run-id": "run-42"}
    assert len(msgs) == 0  # message removed when only directive


def test_extract_directives_empty_messages():
    assert _extract_directives([]) == {}


def test_extract_directives_no_directives():
    msgs = [("user", "just a normal message")]
    result = _extract_directives(msgs)
    assert result == {}
    assert msgs[0][1] == "just a normal message"


def test_extract_multiple_directives():
    msgs = [("user", "[agentops:refresh-prompt][agentops:optimization-run-id=run-7]")]
    result = _extract_directives(msgs)
    assert "refresh-prompt" in result
    assert result["optimization-run-id"] == "run-7"
    assert len(msgs) == 0


# -- _ManagedGraph --


def test_invoke_injects_system_message():
    graph = _make_managed_graph()
    graph.invoke({"messages": [("user", "hello")]})

    call_args = graph._graph.invoke.call_args
    injected = call_args[0][0]["messages"]
    assert isinstance(injected[0], SystemMessage)
    assert injected[0].content == DEFAULT_PROMPT


def test_invoke_uses_active_prompt_over_default():
    graph = _make_managed_graph(active_prompt="Active prompt here.")
    graph.invoke({"messages": [("user", "hello")]})

    call_args = graph._graph.invoke.call_args
    injected = call_args[0][0]["messages"]
    assert injected[0].content == "Active prompt here."


def test_invoke_replaces_existing_system_message():
    graph = _make_managed_graph()
    graph.invoke({"messages": [("system", "old system"), ("user", "hello")]})

    call_args = graph._graph.invoke.call_args
    injected = call_args[0][0]["messages"]
    assert isinstance(injected[0], SystemMessage)
    assert injected[0].content == DEFAULT_PROMPT
    assert len(injected) == 2


def test_get_prompt_short_circuits():
    graph = _make_managed_graph(active_prompt="The active one.")
    result = graph.invoke({"messages": [("user", "[agentops:get-prompt]")]})

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == "The active one."
    graph._graph.invoke.assert_not_called()


def test_get_prompt_falls_back_to_default():
    graph = _make_managed_graph(active_prompt=None)
    result = graph.invoke({"messages": [("user", "[agentops:get-prompt]")]})

    assert result["messages"][0].content == DEFAULT_PROMPT


def test_refresh_prompt_directive_triggers_reload():
    graph = _make_managed_graph()
    graph.invoke({"messages": [("user", "hello [agentops:refresh-prompt]")]})

    graph._client.load_active_prompt.assert_called_once()


def test_optimization_run_id_fetches_candidate():
    graph = _make_managed_graph(candidate="optimized prompt")
    graph.invoke({"messages": [("user", "[agentops:optimization-run-id=run-5] hello")]})

    graph._client.fetch_candidate.assert_called_once_with("run-5")
    call_args = graph._graph.invoke.call_args
    injected = call_args[0][0]["messages"]
    assert injected[0].content == "optimized prompt"


def test_optimization_run_id_falls_back_when_no_candidate():
    graph = _make_managed_graph(active_prompt="active", candidate=None)
    graph.invoke({"messages": [("user", "[agentops:optimization-run-id=run-5] hello")]})

    call_args = graph._graph.invoke.call_args
    injected = call_args[0][0]["messages"]
    assert injected[0].content == "active"


def test_stream_short_circuits():
    graph = _make_managed_graph(active_prompt="streamed prompt")
    results = list(graph.stream({"messages": [("user", "[agentops:get-prompt]")]}))

    assert len(results) == 1
    assert results[0]["messages"][0].content == "streamed prompt"


def test_getattr_delegates_to_inner_graph():
    graph = _make_managed_graph()
    graph._graph.get_graph = MagicMock(return_value="graph-viz")
    assert graph.get_graph() == "graph-viz"
