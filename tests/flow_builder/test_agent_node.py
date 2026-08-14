"""
Unit tests for AgentNode thread_control_policy behaviour.

Covers:
  - REUSE_AND_CORRELATE (valid)
  - CREATE_ALWAYS (valid)
  - None → raises ValueError / ValidationError
  - _UNSET (omitted) → falls back to default with a warning
  - Any invalid string → raises ValueError
"""

import pytest
from pydantic import ValidationError

from ibm_watsonx_orchestrate.flow_builder.flows import FlowFactory
from ibm_watsonx_orchestrate.flow_builder.types import (
    AgentNodeSpec,
    _UNSET,
    _DEFAULT_THREAD_CONTROL_POLICY,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_AGENT_REF = "MyAgent:9b1184a2-cc96-4ff5-9b78-d132efc4e8ee"


def _make_spec(thread_control_policy) -> AgentNodeSpec:
    """Create a minimal AgentNodeSpec with the given thread_control_policy."""
    return AgentNodeSpec(
        name="test_agent_node",
        agent=_AGENT_REF,
        thread_control_policy=thread_control_policy,
    )


def _make_node(flow, thread_control_policy):
    """Add an AgentNode to a flow and return it."""
    return flow.agent(
        name="test_agent_node",
        agent=_AGENT_REF,
        thread_control_policy=thread_control_policy,
    )


# ---------------------------------------------------------------------------
# AgentNodeSpec unit tests
# ---------------------------------------------------------------------------


class TestAgentNodeSpecThreadControlPolicy:
    """Direct AgentNodeSpec validation tests."""

    def test_reuse_and_correlate_is_accepted(self):
        spec = _make_spec("REUSE_AND_CORRELATE")
        assert spec.thread_control_policy == "REUSE_AND_CORRELATE"

    def test_create_always_is_accepted(self):
        spec = _make_spec("CREATE_ALWAYS")
        assert spec.thread_control_policy == "CREATE_ALWAYS"

    def test_none_raises_validation_error(self):
        with pytest.raises((ValueError, ValidationError)):
            _make_spec(None)

    def test_unset_defaults_to_reuse_and_correlate(self):
        spec = _make_spec(_UNSET)
        assert spec.thread_control_policy == _DEFAULT_THREAD_CONTROL_POLICY

    @pytest.mark.parametrize("bad_value", [
        "reuse_and_correlate",
        "create_always",
        "INVALID",
        "NEVER",
        "",
        "  ",
        "None",
        "null",
    ])
    def test_invalid_value_raises_validation_error(self, bad_value):
        with pytest.raises((ValueError, ValidationError)):
            _make_spec(bad_value)

    def test_agent_field_is_required(self):
        """agent is a required field — omitting it must raise."""
        with pytest.raises((ValueError, ValidationError)):
            AgentNodeSpec(name="no_agent_field")

    def test_agent_field_stores_value_as_given(self):
        """The agent string (name:id format) is stored verbatim."""
        spec = _make_spec("CREATE_ALWAYS")
        assert spec.agent == _AGENT_REF


# ---------------------------------------------------------------------------
# AgentNodeSpec.to_json() serialisation
# ---------------------------------------------------------------------------


class TestAgentNodeSpecToJson:
    """Verify that to_json() surfaces thread_control_policy correctly."""

    def test_reuse_and_correlate_serialises(self):
        spec = _make_spec("REUSE_AND_CORRELATE")
        result = spec.to_json()
        assert result["thread_control_policy"] == "REUSE_AND_CORRELATE"

    def test_create_always_serialises(self):
        spec = _make_spec("CREATE_ALWAYS")
        result = spec.to_json()
        assert result["thread_control_policy"] == "CREATE_ALWAYS"

    def test_agent_appears_in_json(self):
        spec = _make_spec("REUSE_AND_CORRELATE")
        result = spec.to_json()
        assert result["agent"] == _AGENT_REF


# ---------------------------------------------------------------------------
# Flow.agent() integration tests
# ---------------------------------------------------------------------------


class TestFlowAgentNode:
    """Test Flow.agent() with each thread_control_policy variant."""

    def test_reuse_and_correlate_via_flow(self):
        flow = FlowFactory.create_flow(name="test_flow")
        node = _make_node(flow, "REUSE_AND_CORRELATE")
        assert node.get_spec().thread_control_policy == "REUSE_AND_CORRELATE"

    def test_create_always_via_flow(self):
        flow = FlowFactory.create_flow(name="test_flow")
        node = _make_node(flow, "CREATE_ALWAYS")
        assert node.get_spec().thread_control_policy == "CREATE_ALWAYS"

    def test_none_via_flow_raises_validation_error(self):
        flow = FlowFactory.create_flow(name="test_flow")
        with pytest.raises((ValueError, ValidationError)):
            _make_node(flow, None)

    def test_omitted_policy_defaults(self):
        """When thread_control_policy is not passed at all it uses _UNSET → default."""
        flow = FlowFactory.create_flow(name="test_flow")
        node = flow.agent(name="test_agent_node", agent=_AGENT_REF)
        assert node.get_spec().thread_control_policy == _DEFAULT_THREAD_CONTROL_POLICY

    @pytest.mark.parametrize("bad_value", [
        "reuse_and_correlate",
        "create_always",
        "INVALID",
        "NEVER",
        "",
    ])
    def test_invalid_policy_via_flow_raises(self, bad_value):
        flow = FlowFactory.create_flow(name="test_flow")
        with pytest.raises((ValueError, ValidationError)):
            _make_node(flow, bad_value)

    def test_node_appears_in_flow_json(self):
        flow = FlowFactory.create_flow(name="test_flow")
        _make_node(flow, "CREATE_ALWAYS")
        flow_json = flow.to_json()
        nodes = flow_json.get("nodes", {})
        assert "test_agent_node" in nodes
        node_spec = nodes["test_agent_node"]["spec"]
        assert node_spec["thread_control_policy"] == "CREATE_ALWAYS"
        assert node_spec["agent"] == _AGENT_REF


# ---------------------------------------------------------------------------
# Warning assertions for None / _UNSET
# ---------------------------------------------------------------------------


class TestThreadControlPolicyWarnings:
    """Ensure a warning is emitted for _UNSET."""

    def test_unset_emits_log_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            _make_spec(_UNSET)
        assert any("thread_control_policy" in record.message for record in caplog.records)

    def test_valid_policy_no_log_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            _make_spec("CREATE_ALWAYS")
        assert not any("thread_control_policy" in record.message for record in caplog.records)
