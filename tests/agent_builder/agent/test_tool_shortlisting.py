"""
tool_shortlisting is a root-level field on the native agent spec.

It is agent configuration rather than a lifecycle hook, so it sits beside
compaction_settings. The ADK's only job is to carry
it verbatim: both fields are a tri-state, where omitting one means "leave the
agent runtime on its per-style default", so neither may be filled in on the way
through.
"""

import logging

import pytest
import yaml

from ibm_watsonx_orchestrate.agent_builder.agents import AgentStyle
from ibm_watsonx_orchestrate.agent_builder.agents.plugins import Plugins
from ibm_watsonx_orchestrate.agent_builder.agents.types import (
    AgentKind,
    AgentSpec,
    ToolShortlistingConfig,
)
from ibm_watsonx_orchestrate.cli.commands.partners.offering.partners_offering_controller import (
    NATIVE_AGENT_CATALOG_FIELDS,
)
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


def _spec(style=AgentStyle.REACT_CORE, **kwargs):
    return {
        "spec_version": "v1",
        "kind": AgentKind.NATIVE,
        "name": "test_agent",
        "description": "An agent with a lot of tools",
        "style": style,
        **kwargs,
    }


def _sent(agent):
    """
    What `agents_controller.publish_or_update_agents` hands to the native agents client.
    """
    return agent.model_dump(exclude_none=True)


class TestPlacement:
    def test_it_is_a_root_level_field(self):
        assert "tool_shortlisting" in AgentSpec.model_fields

    def test_it_is_not_nested_under_plugins(self):
        assert "tool_shortlisting" not in Plugins.model_fields

    def test_it_does_not_reach_the_catalog_schema(self):
        """The catalog rejects unknown properties, so platform-only fields are stripped."""
        assert "tool_shortlisting" not in NATIVE_AGENT_CATALOG_FIELDS


class TestWhatGetsSent:
    def test_a_full_block_is_sent_verbatim(self):
        agent = AgentSpec(**_spec(tool_shortlisting={"enabled": True, "max_tools": 12}))
        assert _sent(agent)["tool_shortlisting"] == {"enabled": True, "max_tools": 12}

    def test_max_tools_alone_does_not_fabricate_enabled(self):
        """A missing `enabled` is what tells the runtime to keep the style default."""
        agent = AgentSpec(**_spec(tool_shortlisting={"max_tools": 7}))
        assert _sent(agent)["tool_shortlisting"] == {"max_tools": 7}

    def test_enabled_alone_does_not_fabricate_max_tools(self):
        agent = AgentSpec(**_spec(tool_shortlisting={"enabled": True}))
        assert _sent(agent)["tool_shortlisting"] == {"enabled": True}

    def test_an_explicit_false_survives_the_none_stripping(self):
        agent = AgentSpec(**_spec(tool_shortlisting={"enabled": False}))
        assert _sent(agent)["tool_shortlisting"] == {"enabled": False}

    def test_omitting_the_block_sends_nothing(self):
        """
        Existing agents must be left exactly as they are.
        """
        assert "tool_shortlisting" not in _sent(AgentSpec(**_spec()))

    def test_it_survives_a_yaml_round_trip(self, tmp_path):
        spec_file = tmp_path / "agent.yaml"
        AgentSpec(**_spec(tool_shortlisting={"enabled": True, "max_tools": 30})).dump_spec(
            str(spec_file)
        )
        reloaded = AgentSpec(**yaml.safe_load(spec_file.read_text()))
        assert reloaded.tool_shortlisting == ToolShortlistingConfig(
            enabled=True, max_tools=30
        )


class TestCustomerCare:
    """
    The style shortlisting defaults to on for must be able to carry the block.
    """

    def test_the_block_is_accepted(self):
        agent = AgentSpec(
            **_spec(
                style=AgentStyle.CUSTOMER_CARE,
                tool_shortlisting={"enabled": True, "max_tools": 20},
            )
        )
        assert agent.tool_shortlisting.max_tools == 20

    def test_it_warns_that_only_the_v2_chat_api_applies_it(self, caplog):
        with caplog.at_level(logging.WARNING):
            AgentSpec(
                **_spec(
                    style=AgentStyle.CUSTOMER_CARE,
                    tool_shortlisting={"enabled": True},
                )
            )
        assert any("tool_shortlisting" in r.message for r in caplog.records)

    @pytest.mark.parametrize("style", [AgentStyle.REACT_CORE, AgentStyle.DEFAULT])
    def test_no_warning_for_styles_the_python_runtime_does_not_serve(self, caplog, style):
        with caplog.at_level(logging.WARNING):
            AgentSpec(**_spec(style=style, tool_shortlisting={"enabled": True}))
        assert not any("tool_shortlisting" in r.message for r in caplog.records)

    def test_hook_plugins_are_still_rejected(self):
        """Reverting the plugins carve-out must not loosen the existing check."""
        with pytest.raises(BadRequest, match="plugins"):
            AgentSpec(
                **_spec(
                    style=AgentStyle.CUSTOMER_CARE,
                    plugins={"agent_pre_invoke": [{"plugin_name": "pii_redactor"}]},
                )
            )


class TestValidation:
    def test_max_tools_must_be_a_number(self):
        with pytest.raises(Exception):
            AgentSpec(**_spec(tool_shortlisting={"max_tools": "twenty"}))

    @pytest.mark.parametrize("bad", [0, -1])
    def test_max_tools_must_be_a_positive_count(self, bad):
        """
        Caught here rather than as a 422 from the server.
        """
        with pytest.raises(Exception):
            AgentSpec(**_spec(tool_shortlisting={"max_tools": bad}))

    def test_unknown_keys_do_not_reach_the_server(self):
        agent = AgentSpec(**_spec(tool_shortlisting={"enabled": True, "maxtools": 9}))
        assert "maxtools" not in _sent(agent)["tool_shortlisting"]
