import copy
import pytest

from ibm_watsonx_orchestrate.agent_builder.agents import Agent
from ibm_watsonx_orchestrate.agent_builder.agents.webchat_customizations import WelcomeContent
from ibm_watsonx_orchestrate_clients.agents.agent_client import (
    transform_agents_from_flat_agent_spec,
    transform_agents_to_flat_agent_spec,
)

LOCALE_KEYED = {
    "pt-BR": {
        "description": "Accuracy of generated answers may vary. Please double-check responses.",
        "welcome_message": "Hello, welcome to watsonx Orchestrate",
        "is_default_voice_greeting": False,
    },
    "default": {
        "description": "Accuracy of generated answers may vary. Please double-check responses.",
        "welcome_message": "Hello, welcome to watsonx Orchestrate",
        "is_default_voice_greeting": False,
    },
    "is_default_message": False,
}

FLAT = {
    "welcome_message": "Hello, I'm Agent Test.",
    "description": "This is not default",
    "is_default_message": False,
    "is_user_barge_in_disabled": False,
}

BASE_AGENT = {
    "name": "welcome_agent",
    "kind": "native",
    "description": "test",
    "llm": "groq/openai/gpt-oss-120b",
    "style": "default",
}


class TestWelcomeContentShapes:
    def test_flat_shape_unchanged(self):
        wc = WelcomeContent.model_validate(FLAT)
        assert wc.welcome_message == FLAT["welcome_message"]
        assert wc.model_dump(exclude_none=True) == FLAT

    def test_locale_keyed_shape_accepted(self):
        wc = WelcomeContent.model_validate(LOCALE_KEYED)
        assert wc.welcome_message is None
        assert wc.model_extra["default"]["welcome_message"] == "Hello, welcome to watsonx Orchestrate"

    def test_locale_keyed_dump_does_not_gain_flat_defaults(self):
        dumped = WelcomeContent.model_validate(LOCALE_KEYED).model_dump(mode="json", exclude_none=True)
        assert dumped == LOCALE_KEYED
        assert "is_user_barge_in_disabled" not in dumped
        assert "description" not in dumped

    @pytest.mark.parametrize("bad", [{}, {"description": "only a description"}])
    def test_missing_message_and_locales_rejected(self, bad):
        with pytest.raises(ValueError):
            WelcomeContent.model_validate(bad)

    @pytest.mark.parametrize("message", ["   ", "\n\t"])
    def test_flat_blank_message_rejected(self, message):
        with pytest.raises(ValueError):
            WelcomeContent.model_validate({"welcome_message": message})


class TestAgentWithWelcomeContent:
    def test_agent_parses_locale_keyed_welcome_content(self):
        agent = Agent.model_validate({**BASE_AGENT, "welcome_content": copy.deepcopy(LOCALE_KEYED)})
        assert isinstance(agent.welcome_content, WelcomeContent)

    def test_agent_parses_flat_welcome_content(self):
        agent = Agent.model_validate({**BASE_AGENT, "welcome_content": copy.deepcopy(FLAT)})
        assert agent.welcome_content.welcome_message == FLAT["welcome_message"]

    def test_locale_keyed_round_trips_unchanged_through_client(self):
        server_agent = {**BASE_AGENT, "additional_properties": {"welcome_content": copy.deepcopy(LOCALE_KEYED)}}

        flat_spec = transform_agents_to_flat_agent_spec(copy.deepcopy(server_agent))
        agent = Agent.model_validate(flat_spec)
        dumped = agent.model_dump(mode="json", exclude_none=True)
        sent = transform_agents_from_flat_agent_spec(copy.deepcopy(dumped))

        assert sent["additional_properties"]["welcome_content"] == LOCALE_KEYED

    def test_flat_still_drops_is_default_message_when_sent(self):
        sent = transform_agents_from_flat_agent_spec({**BASE_AGENT, "welcome_content": copy.deepcopy(FLAT)})
        assert "is_default_message" not in sent["additional_properties"]["welcome_content"]

    def test_flat_still_gets_is_default_message_false_when_received(self):
        server = {**BASE_AGENT, "additional_properties": {"welcome_content": {"welcome_message": "hi"}}}
        flat = transform_agents_to_flat_agent_spec(server)
        assert flat["welcome_content"]["is_default_message"] is False
