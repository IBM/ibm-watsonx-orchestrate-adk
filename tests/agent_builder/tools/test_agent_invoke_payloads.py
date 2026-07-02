"""Tests for AgentPreInvokePayload and AgentPostInvokePayload context field."""
import pytest
from typing import Any, Dict

from ibm_watsonx_orchestrate_core.types.tools.types import (
    AgentPreInvokePayload,
    AgentPostInvokePayload,
    Message,
    Role,
    TextContent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_message(text: str = "hello") -> Message:
    return Message(role=Role.USER, content=TextContent(type="text", text=text))


# ---------------------------------------------------------------------------
# AgentPreInvokePayload
# ---------------------------------------------------------------------------

class TestAgentPreInvokePayload:
    def test_context_defaults_to_empty_dict(self):
        payload = AgentPreInvokePayload(
            agent_id="agent-1",
            messages=[_make_message()],
        )
        assert payload.context == {}

    def test_context_accepts_none(self):
        payload = AgentPreInvokePayload(
            agent_id="agent-1",
            messages=[_make_message()],
            context=None,
        )
        assert payload.context is None

    def test_context_accepts_populated_dict(self):
        ctx = {"user_id": "u1", "session": "s42", "flags": {"feature_x": True}}
        payload = AgentPreInvokePayload(
            agent_id="agent-1",
            messages=[_make_message()],
            context=ctx,
        )
        assert payload.context == ctx
        assert payload.context["user_id"] == "u1"
        assert payload.context["flags"]["feature_x"] is True

    def test_context_round_trips_via_model_dump(self):
        ctx = {"k": "v"}
        payload = AgentPreInvokePayload(
            agent_id="agent-1",
            messages=[_make_message()],
            context=ctx,
        )
        dumped = payload.model_dump()
        assert dumped["context"] == ctx

    def test_context_round_trips_via_model_validate(self):
        data = {
            "agent_id": "agent-2",
            "messages": [{"role": "user", "content": {"type": "text", "text": "hi"}}],
            "context": {"trace_id": "t123"},
        }
        payload = AgentPreInvokePayload.model_validate(data)
        assert payload.context == {"trace_id": "t123"}

    def test_existing_fields_unaffected(self):
        """Adding context must not break existing fields."""
        payload = AgentPreInvokePayload(
            agent_id="agent-99",
            messages=[_make_message("test")],
            tools=["tool_a"],
            model="gpt-4",
            system_prompt="be helpful",
            parameters={"temperature": 0.7},
            context={"env": "production"},
        )
        assert payload.agent_id == "agent-99"
        assert payload.tools == ["tool_a"]
        assert payload.model == "gpt-4"
        assert payload.system_prompt == "be helpful"
        assert payload.parameters == {"temperature": 0.7}
        assert payload.context == {"env": "production"}


# ---------------------------------------------------------------------------
# AgentPostInvokePayload
# ---------------------------------------------------------------------------

class TestAgentPostInvokePayload:
    def test_context_defaults_to_empty_dict(self):
        payload = AgentPostInvokePayload(
            agent_id="agent-1",
            messages=[_make_message()],
        )
        assert payload.context == {}

    def test_context_accepts_none(self):
        payload = AgentPostInvokePayload(
            agent_id="agent-1",
            messages=[_make_message()],
            context=None,
        )
        assert payload.context is None

    def test_context_accepts_populated_dict(self):
        ctx = {"result_code": 200, "tags": ["ok", "fast"]}
        payload = AgentPostInvokePayload(
            agent_id="agent-1",
            messages=[_make_message()],
            context=ctx,
        )
        assert payload.context == ctx
        assert payload.context["result_code"] == 200

    def test_context_round_trips_via_model_dump(self):
        ctx = {"post_key": "post_val"}
        payload = AgentPostInvokePayload(
            agent_id="agent-1",
            messages=[_make_message()],
            context=ctx,
        )
        dumped = payload.model_dump()
        assert dumped["context"] == ctx

    def test_context_round_trips_via_model_validate(self):
        data = {
            "agent_id": "agent-3",
            "messages": [{"role": "assistant", "content": {"type": "text", "text": "done"}}],
            "context": {"post_trace": "abc"},
        }
        payload = AgentPostInvokePayload.model_validate(data)
        assert payload.context == {"post_trace": "abc"}

    def test_existing_fields_unaffected(self):
        """Adding context must not break existing fields."""
        tool_calls = [{"id": "call_1", "type": "function", "function": {"name": "tool_a"}}]
        payload = AgentPostInvokePayload(
            agent_id="agent-99",
            messages=[_make_message("response")],
            tool_calls=tool_calls,
            context={"env": "staging"},
        )
        assert payload.agent_id == "agent-99"
        assert payload.tool_calls == tool_calls
        assert payload.context == {"env": "staging"}
