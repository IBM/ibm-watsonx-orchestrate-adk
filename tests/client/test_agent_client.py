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
