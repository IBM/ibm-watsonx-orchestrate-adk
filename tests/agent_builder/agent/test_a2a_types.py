import pytest
from ibm_watsonx_orchestrate.agent_builder.agents.a2a_types import AgentCard


class TestAgentCard:
    """Test AgentCard model and conversion logic."""
    
    @pytest.fixture
    def public_agent_card(self):
        """Agent card for public agent (no auth)."""
        return {
            "name": "Public Weather Agent",
            "description": "A public weather information agent",
            "url": "https://weather.example.com/api"
        }
    
    @pytest.fixture
    def authenticated_agent_card(self):
        """Agent card for authenticated agent."""
        return {
            "name": "Secure Banking Agent",
            "description": "A secure banking assistant",
            "url": "https://bank.example.com/api"
        }
    
    def test_public_agent_card_parsing(self, public_agent_card):
        """Test parsing a public agent card."""
        card = AgentCard(**public_agent_card)
        
        assert card.name == "Public Weather Agent"
        assert card.description == "A public weather information agent"
        assert card.url == "https://weather.example.com/api"
    
    def test_authenticated_agent_card_parsing(self, authenticated_agent_card):
        """Test parsing an authenticated agent card."""
        card = AgentCard(**authenticated_agent_card)
        
        assert card.name == "Secure Banking Agent"
    
    def test_public_agent_conversion_without_app_id(self, public_agent_card):
        """Test converting public agent without app_id (should succeed)."""
        card = AgentCard(**public_agent_card)
        
        wxo_spec = card.convert_to_wxo_external_agent_dict(
            agent_name="weather_agent",
            app_id=None
        )
        
        # Verify essential fields only
        assert wxo_spec["spec_version"] == "v1"
        assert wxo_spec["kind"] == "external"
        assert wxo_spec["name"] == "weather_agent"
        assert wxo_spec["title"] == "Public Weather Agent"
        assert wxo_spec["provider"] == "external_chat/A2A/0.3.0"
        assert wxo_spec["description"] == "A public weather information agent"
        assert wxo_spec["api_url"] == "https://weather.example.com/api"
        assert "app_id" not in wxo_spec
        
        # Verify no extra fields
        assert "nickname" not in wxo_spec
        assert "auth_scheme" not in wxo_spec
        assert "auth_config" not in wxo_spec
        assert "chat_params" not in wxo_spec
        assert "config" not in wxo_spec
    
    def test_authenticated_agent_conversion_with_app_id(self, authenticated_agent_card):
        """Test converting authenticated agent with app_id (should succeed)."""
        card = AgentCard(**authenticated_agent_card)
        
        wxo_spec = card.convert_to_wxo_external_agent_dict(
            agent_name="banking_agent",
            app_id="my-banking-connection"
        )
        
        # Verify essential fields
        assert wxo_spec["spec_version"] == "v1"
        assert wxo_spec["kind"] == "external"
        assert wxo_spec["name"] == "banking_agent"
        assert wxo_spec["title"] == "Secure Banking Agent"
        assert wxo_spec["provider"] == "external_chat/A2A/0.3.0"
        assert wxo_spec["description"] == "A secure banking assistant"
        assert wxo_spec["api_url"] == "https://bank.example.com/api"
        assert wxo_spec["app_id"] == "my-banking-connection"
        
        # Verify no extra fields
        assert "nickname" not in wxo_spec
        assert "auth_scheme" not in wxo_spec
        assert "auth_config" not in wxo_spec
        assert "chat_params" not in wxo_spec
        assert "config" not in wxo_spec
    
    def test_agent_conversion_without_app_id(self, authenticated_agent_card):
        """Test converting agent without app_id (no error, just no app_id in spec)."""
        card = AgentCard(**authenticated_agent_card)
        
        wxo_spec = card.convert_to_wxo_external_agent_dict(
            agent_name="banking_agent",
            app_id=None
        )
        
        # Should succeed but not include app_id
        assert wxo_spec["name"] == "banking_agent"
        assert "app_id" not in wxo_spec
    
    def test_default_agent_name_from_card_name(self, public_agent_card):
        """Test that agent name defaults to card name (lowercase, underscored)."""
        card = AgentCard(**public_agent_card)
        
        wxo_spec = card.convert_to_wxo_external_agent_dict()
        
        # "Public Weather Agent" -> "public_weather_agent"
        assert wxo_spec["name"] == "public_weather_agent"
        assert wxo_spec["title"] == "Public Weather Agent"
    
    def test_custom_agent_name(self, public_agent_card):
        """Test that custom agent name is used when provided."""
        card = AgentCard(**public_agent_card)
        
        wxo_spec = card.convert_to_wxo_external_agent_dict(
            agent_name="custom_name"
        )
        
        assert wxo_spec["name"] == "custom_name"
        assert wxo_spec["title"] == "Public Weather Agent"
    
    def test_api_key_authentication_scheme(self):
        """Test agent with API key authentication."""
        card_data = {
            "name": "API Key Agent",
            "description": "Agent with API key auth",
            "url": "https://api.example.com",
            "authentication_required": True,
            "authentication_scheme": "api_key"
        }
        card = AgentCard(**card_data)
        
        wxo_spec = card.convert_to_wxo_external_agent_dict(
            app_id="api-key-connection"
        )
        
        assert wxo_spec["name"] == "api_key_agent"
        assert wxo_spec["app_id"] == "api-key-connection"
    
    def test_minimal_agent_card(self):
        """Test agent card with only required fields."""
        minimal_card = {
            "name": "Minimal Agent",
            "description": "Minimal description",
            "url": "https://minimal.example.com"
        }
        card = AgentCard(**minimal_card)
        
        assert card.name == "Minimal Agent"
    
    def test_spec_version_and_kind(self, public_agent_card):
        """Test that spec_version and kind are correctly set."""
        card = AgentCard(**public_agent_card)
        
        wxo_spec = card.convert_to_wxo_external_agent_dict()
        
        assert wxo_spec["spec_version"] == "v1"
        assert wxo_spec["kind"] == "external"
