"""
Unit tests for AgentPrompt.subtitle default behaviour.

Regression tests for: subtitle must default to "" (empty string) and never
serialise as null/None, which breaks the webchat UI when no subtitle is
provided in the agent YAML.
"""
from ibm_watsonx_orchestrate.agent_builder.agents.webchat_customizations.prompts import (
    AgentPrompt,
    StarterPrompts,
    PromptState,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAgentPromptSubtitle:
    """Verify subtitle defaults to '' and is never null in serialised output."""

    def test_subtitle_defaults_to_empty_string_when_omitted(self):
        """
        Core regression: omitting subtitle must produce "" not None.
        subtitle: Optional[str] = "" ensures no null leaks into the agent YAML.
        """
        prompt = AgentPrompt(id="1", title="Hello", prompt="Say hi")
        assert prompt.subtitle == "", (
            f"Expected subtitle='' but got {prompt.subtitle!r}"
        )

    def test_subtitle_is_not_none_when_omitted(self):
        """
        subtitle must never be None — None serialises to null and breaks the UI.
        """
        prompt = AgentPrompt(id="1", title="Hello", prompt="Say hi")
        assert prompt.subtitle is not None

    def test_subtitle_not_null_in_model_dump(self):
        """
        model_dump() must not contain null for subtitle when it was not provided.
        """
        prompt = AgentPrompt(id="1", title="Hello", prompt="Say hi")
        dumped = prompt.model_dump()
        assert dumped["subtitle"] == ""
        assert dumped["subtitle"] is not None

    def test_subtitle_explicit_empty_string_roundtrips(self):
        """
        Explicitly passing "" is equivalent to omitting the field entirely.
        """
        prompt = AgentPrompt(id="1", title="Hello", subtitle="", prompt="Say hi")
        assert prompt.subtitle == ""
        assert prompt.model_dump()["subtitle"] == ""

    def test_subtitle_explicit_value_is_preserved(self):
        """
        A real subtitle value must be preserved exactly as provided.
        """
        prompt = AgentPrompt(id="1", title="Hello", subtitle="A short description", prompt="Say hi")
        assert prompt.subtitle == "A short description"
        assert prompt.model_dump()["subtitle"] == "A short description"


class TestStarterPromptsSubtitle:
    """Verify subtitle propagates correctly through StarterPrompts."""

    def test_subtitle_defaults_to_empty_string_in_starter_prompts(self):
        """
        Prompts nested inside StarterPrompts must also default subtitle to "".
        """
        starter = StarterPrompts(**{
            "is_default_prompts": False,
            "prompts": [
                {"id": "p1", "title": "Hello", "prompt": "Say hi"},
            ],
        })
        assert starter.prompts[0].subtitle == "", (
            f"Expected subtitle='' but got {starter.prompts[0].subtitle!r}"
        )

    def test_model_dump_contains_no_null_subtitle(self):
        """
        model_dump() on StarterPrompts must not contain null for any subtitle.
        """
        starter = StarterPrompts(**{
            "is_default_prompts": False,
            "prompts": [
                {"id": "p1", "title": "Hello", "prompt": "Say hi"},
                {"id": "p2", "title": "World", "prompt": "Say bye"},
            ],
        })
        dumped = starter.model_dump()
        for p in dumped["prompts"]:
            assert p["subtitle"] is not None, (
                f"Prompt '{p['id']}' has null subtitle in serialised output"
            )
            assert p["subtitle"] == ""

    def test_mixed_subtitle_values_all_serialise_without_null(self):
        """
        Mix of prompts with and without subtitle must all serialise without null.
        """
        starter = StarterPrompts(**{
            "is_default_prompts": False,
            "prompts": [
                {"id": "p1", "title": "With subtitle", "subtitle": "A description", "prompt": "msg1"},
                {"id": "p2", "title": "No subtitle", "prompt": "msg2"},
                {"id": "p3", "title": "Empty subtitle", "subtitle": "", "prompt": "msg3"},
            ],
        })
        dumped = starter.model_dump()

        assert dumped["prompts"][0]["subtitle"] == "A description"
        assert dumped["prompts"][1]["subtitle"] == ""
        assert dumped["prompts"][2]["subtitle"] == ""

        for p in dumped["prompts"]:
            assert p["subtitle"] is not None
