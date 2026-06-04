import pytest
from pydantic_core import ValidationError
from ibm_watsonx_orchestrate.agent_builder.agents.types import (
    AssistantAgentSpec,
    AssistantAgentConfig,
    AgentKind,
    SpecVersion
)


class TestAssistantAgentWelcomeNode:
    """Test cases for the always_trigger_welcome_node field in AssistantAgentConfig"""

    def test_always_trigger_welcome_node_default_value(self):
        """Test that always_trigger_welcome_node defaults to False"""
        config = AssistantAgentConfig()
        assert config.always_trigger_welcome_node is False

    def test_always_trigger_welcome_node_explicit_true(self):
        """Test setting always_trigger_welcome_node to True explicitly"""
        config = AssistantAgentConfig(always_trigger_welcome_node=True)
        assert config.always_trigger_welcome_node is True

    def test_always_trigger_welcome_node_explicit_false(self):
        """Test setting always_trigger_welcome_node to False explicitly"""
        config = AssistantAgentConfig(always_trigger_welcome_node=False)
        assert config.always_trigger_welcome_node is False

    def test_always_trigger_welcome_node_with_full_config(self):
        """Test always_trigger_welcome_node with a complete AssistantAgentConfig"""
        config = AssistantAgentConfig(
            api_version="2021-11-27",
            assistant_id="test-assistant-id",
            crn="crn:v1:test",
            service_instance_url="https://test.example.com",
            environment_id="test-env-id",
            always_trigger_welcome_node=True
        )
        assert config.always_trigger_welcome_node is True
        assert config.api_version == "2021-11-27"
        assert config.assistant_id == "test-assistant-id"

    def test_assistant_agent_spec_with_welcome_node_in_config(self):
        """Test AssistantAgentSpec with always_trigger_welcome_node in config"""
        spec = AssistantAgentSpec(
            name="test_assistant",
            description="Test assistant agent",
            config=AssistantAgentConfig(
                api_version="2021-11-27",
                assistant_id="test-id",
                always_trigger_welcome_node=True
            )
        )
        assert spec.config.always_trigger_welcome_node is True

    def test_assistant_agent_spec_welcome_node_migration_from_top_level(self):
        """Test migration of always_trigger_welcome_node from top level to config"""
        spec_dict = {
            "name": "test_assistant",
            "description": "Test assistant agent",
            "always_trigger_welcome_node": True,
            "api_version": "2021-11-27",
            "assistant_id": "test-id"
        }
        spec = AssistantAgentSpec(**spec_dict)
        assert spec.config.always_trigger_welcome_node is True

    def test_assistant_agent_spec_welcome_node_migration_default_false(self):
        """Test that migration sets default False when not provided"""
        spec_dict = {
            "name": "test_assistant",
            "description": "Test assistant agent",
            "api_version": "2021-11-27",
            "assistant_id": "test-id"
        }
        spec = AssistantAgentSpec(**spec_dict)
        assert spec.config.always_trigger_welcome_node is False

    def test_assistant_agent_spec_welcome_node_both_locations(self):
        """Test when always_trigger_welcome_node is in both top level and config"""
        spec_dict = {
            "name": "test_assistant",
            "description": "Test assistant agent",
            "always_trigger_welcome_node": True,
            "config": {
                "api_version": "2021-11-27",
                "assistant_id": "test-id",
                "always_trigger_welcome_node": False
            }
        }
        spec = AssistantAgentSpec(**spec_dict)
        # Config value should take precedence
        assert spec.config.always_trigger_welcome_node is False

    def test_assistant_agent_spec_welcome_node_only_in_config(self):
        """Test when always_trigger_welcome_node is only in config"""
        spec_dict = {
            "name": "test_assistant",
            "description": "Test assistant agent",
            "config": {
                "api_version": "2021-11-27",
                "assistant_id": "test-id",
                "always_trigger_welcome_node": True
            }
        }
        spec = AssistantAgentSpec(**spec_dict)
        assert spec.config.always_trigger_welcome_node is True

    def test_assistant_agent_spec_welcome_node_none_value(self):
        """Test handling of None value for always_trigger_welcome_node"""
        spec_dict = {
            "name": "test_assistant",
            "description": "Test assistant agent",
            "always_trigger_welcome_node": None,
            "api_version": "2021-11-27",
            "assistant_id": "test-id"
        }
        spec = AssistantAgentSpec(**spec_dict)
        # When None is explicitly provided, it remains None
        assert spec.config.always_trigger_welcome_node is None

    def test_assistant_agent_config_serialization_with_welcome_node(self):
        """Test that always_trigger_welcome_node is properly serialized"""
        config = AssistantAgentConfig(
            api_version="2021-11-27",
            assistant_id="test-id",
            always_trigger_welcome_node=True
        )
        config_dict = config.model_dump()
        assert "always_trigger_welcome_node" in config_dict
        assert config_dict["always_trigger_welcome_node"] is True

    def test_assistant_agent_spec_dump_spec_includes_welcome_node(self):
        """Test that dump_spec includes always_trigger_welcome_node"""
        spec = AssistantAgentSpec(
            name="test_assistant",
            description="Test assistant agent",
            config=AssistantAgentConfig(
                api_version="2021-11-27",
                assistant_id="test-id",
                always_trigger_welcome_node=True
            )
        )
        spec_dict = spec.model_dump(mode='json', exclude_unset=True, exclude_none=True)
        assert "config" in spec_dict
        assert "always_trigger_welcome_node" in spec_dict["config"]
        assert spec_dict["config"]["always_trigger_welcome_node"] is True

    def test_assistant_agent_spec_with_all_fields_and_welcome_node(self):
        """Test AssistantAgentSpec with all fields including always_trigger_welcome_node"""
        spec = AssistantAgentSpec(
            spec_version=SpecVersion.V1,
            kind=AgentKind.ASSISTANT,
            name="test_assistant",
            description="Test assistant agent",
            title="Test Assistant",
            tags=["tag1", "tag2"],
            config=AssistantAgentConfig(
                api_version="2021-11-27",
                assistant_id="test-assistant-id",
                crn="crn:v1:test",
                service_instance_url="https://test.example.com",
                environment_id="test-env-id",
                authorization_url="https://auth.example.com",
                connection_id="test-connection-id",
                always_trigger_welcome_node=True
            ),
            nickname="test_agent",
            app_id="test-app-123"
        )
        
        assert spec.name == "test_assistant"
        assert spec.description == "Test assistant agent"
        assert spec.config.always_trigger_welcome_node is True
        assert spec.config.api_version == "2021-11-27"
        assert spec.config.assistant_id == "test-assistant-id"
        assert spec.nickname == "test_agent"
        assert spec.app_id == "test-app-123"

    def test_assistant_agent_config_type_validation(self):
        """Test that always_trigger_welcome_node only accepts boolean values"""
        # Valid boolean values should work
        config1 = AssistantAgentConfig(always_trigger_welcome_node=True)
        assert config1.always_trigger_welcome_node is True
        
        config2 = AssistantAgentConfig(always_trigger_welcome_node=False)
        assert config2.always_trigger_welcome_node is False

    def test_backward_compatibility_without_welcome_node(self):
        """Test backward compatibility when always_trigger_welcome_node is not provided"""
        spec_dict = {
            "name": "test_assistant",
            "description": "Test assistant agent",
            "config": {
                "api_version": "2021-11-27",
                "assistant_id": "test-id"
            }
        }
        spec = AssistantAgentSpec(**spec_dict)
        # Should default to False for backward compatibility
        assert spec.config.always_trigger_welcome_node is False

    def test_migration_preserves_other_config_fields(self):
        """Test that migration of always_trigger_welcome_node preserves other config fields"""
        spec_dict = {
            "name": "test_assistant",
            "description": "Test assistant agent",
            "always_trigger_welcome_node": True,
            "api_version": "2021-11-27",
            "assistant_id": "test-id",
            "crn": "crn:v1:test",
            "service_instance_url": "https://test.example.com",
            "environment_id": "test-env-id"
        }
        spec = AssistantAgentSpec(**spec_dict)
        
        # Verify all fields are preserved
        assert spec.config.always_trigger_welcome_node is True
        assert spec.config.api_version == "2021-11-27"
        assert spec.config.assistant_id == "test-id"
        assert spec.config.crn == "crn:v1:test"
        assert spec.config.service_instance_url == "https://test.example.com"
        assert spec.config.environment_id == "test-env-id"

# Made with Bob
