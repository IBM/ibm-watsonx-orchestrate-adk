from ibm_watsonx_orchestrate.client.agents.agent_client import (
    transform_agents_from_flat_agent_spec,
    transform_agents_to_flat_agent_spec,
)


def test_transform_agents_from_flat_agent_spec_keeps_memory_enabled():
    payload = {
        "name": "test-agent",
        "description": "test description",
        "kind": "native",
        "memory_enabled": True,
    }

    transformed = transform_agents_from_flat_agent_spec(payload)

    assert transformed["memory_enabled"] is True

def test_transform_agents_to_flat_agent_spec_keeps_memory_enabled():
    payload = {
        "name": "test-agent",
        "description": "test description",
        "kind": "native",
        "memory_enabled": True,
        "additional_properties": {},
    }

    transformed = transform_agents_to_flat_agent_spec(payload)

    assert transformed["memory_enabled"] is True

def test_transform_agents_from_flat_agent_spec_with_compaction_settings():
    """Test that compaction_settings is transformed to additional_properties.context_settings"""
    payload = {
        "name": "test-agent",
        "description": "test description",
        "kind": "native",
        "compaction_settings": {
            "context_compaction_enabled": True,
            "context_compaction_threshold": 30000
        }
    }

    transformed = transform_agents_from_flat_agent_spec(payload)

    assert "compaction_settings" not in transformed
    assert "additional_properties" in transformed
    assert "context_settings" in transformed["additional_properties"]
    assert transformed["additional_properties"]["context_settings"]["context_compaction_enabled"] is True
    assert transformed["additional_properties"]["context_settings"]["context_compaction_threshold"] == 30000

def test_transform_agents_to_flat_agent_spec_with_context_settings():
    """Test that additional_properties.context_settings is transformed to compaction_settings"""
    payload = {
        "name": "test-agent",
        "description": "test description",
        "kind": "native",
        "additional_properties": {
            "context_settings": {
                "context_compaction_enabled": True,
                "context_compaction_threshold": 30000
            }
        }
    }

    transformed = transform_agents_to_flat_agent_spec(payload)

    assert "compaction_settings" in transformed
    assert transformed["compaction_settings"]["context_compaction_enabled"] is True
    assert transformed["compaction_settings"]["context_compaction_threshold"] == 30000
