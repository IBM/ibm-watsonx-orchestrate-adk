import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController
from ibm_watsonx_orchestrate.agent_builder.agents.a2a_discovery import A2ADiscoveryService
from ibm_watsonx_orchestrate.agent_builder.agents.a2a_types import AgentCard


class TestA2ADiscoveryService:
    """Test A2ADiscoveryService HTTP operations."""
    
    @pytest.fixture
    def mock_agent_card_response(self):
        """Mock successful agent card response."""
        return {
            "name": "Test Agent",
            "description": "A test agent",
            "url": "https://test-agent.example.com/api"
        }
    
    @pytest.fixture
    def mock_authenticated_agent_card_response(self):
        """Mock agent card response requiring authentication."""
        return {
            "name": "Secure Agent",
            "description": "A secure agent",
            "url": "https://secure-agent.example.com/api"
        }
    
    @patch('requests.Session.get')
    def test_discover_from_wellknown_success(self, mock_get, mock_agent_card_response):
        """Test successful discovery from well-known URI."""
        mock_response = Mock()
        mock_response.json.return_value = mock_agent_card_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with A2ADiscoveryService() as client:
            agent_card = client.discover_from_wellknown(
                base_url="https://example.com",
                endpoint=".well-known/agent-card.json"
            )
        
        assert isinstance(agent_card, AgentCard)
        assert agent_card.name == "Test Agent"
        assert agent_card.url == "https://test-agent.example.com/api"
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_discover_url_not_found(self, mock_get):
        """Test discovery when URL returns 404."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.HTTPError):
            with A2ADiscoveryService() as client:
                client.discover_from_wellknown(
                    base_url="https://nonexistent.example.com",
                    endpoint=".well-known/agent-card.json"
                )
    
    @patch('requests.Session.get')
    def test_discover_invalid_json(self, mock_get):
        """Test discovery when response is invalid JSON."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError):
            with A2ADiscoveryService() as client:
                client.discover_from_wellknown(
                    base_url="https://example.com",
                    endpoint=".well-known/agent-card.json"
                )
    
    @patch('ibm_watsonx_orchestrate.agent_builder.agents.a2a_discovery.AgentCard')
    @patch('requests.Session.get')
    def test_discover_and_convert_success(self, mock_get, mock_agent_card_class, mock_agent_card_response):
        """Test discover_and_convert method."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = mock_agent_card_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock AgentCard instance and its conversion method
        mock_agent_card_instance = Mock()
        mock_wxo_spec = {
            "spec_version": "v1",
            "kind": "external",
            "name": "my_agent",
            "title": "Test Agent",
            "provider": "external_chat/A2A/0.3.0",
            "description": "A test agent",
            "api_url": "https://test-agent.example.com/api"
        }
        mock_agent_card_instance.convert_to_wxo_external_agent_dict.return_value = mock_wxo_spec
        mock_agent_card_class.return_value = mock_agent_card_instance
        
        with A2ADiscoveryService() as client:
            wxo_spec = client.discover_and_convert(
                base_url="https://example.com",
                endpoint=".well-known/agent-card.json",
                agent_name="my_agent"
            )
        
        mock_get.assert_called_once()
        mock_agent_card_class.assert_called_once_with(**mock_agent_card_response)
        mock_agent_card_instance.convert_to_wxo_external_agent_dict.assert_called_once_with(
            agent_name="my_agent",
            app_id=None
        )
        
        # Verify returned spec has essential fields only
        assert wxo_spec["spec_version"] == "v1"
        assert wxo_spec["kind"] == "external"
        assert wxo_spec["name"] == "my_agent"
        assert wxo_spec["title"] == "Test Agent"
        assert wxo_spec["provider"] == "external_chat/A2A/0.3.0"
    
    @patch('requests.Session.get')
    def test_discover_connection_timeout(self, mock_get):
        """Test discovery when connection times out."""
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        with pytest.raises(requests.Timeout):
            with A2ADiscoveryService() as client:
                client.discover_from_wellknown(
                    base_url="https://slow.example.com",
                    endpoint=".well-known/agent-card.json"
                )


class TestAgentsControllerDiscovery:
    """Test AgentsController.discover_and_import_agent method."""
    
    @pytest.fixture
    def mock_agent_card_json(self):
        """Mock agent card JSON."""
        return {
            "name": "Weather Agent",
            "description": "Weather information agent",
            "url": "https://weather.example.com/api"
        }
    
    @pytest.fixture
    def mock_authenticated_agent_card_json(self):
        """Mock authenticated agent card JSON."""
        return {
            "name": "Banking Agent",
            "description": "Secure banking agent",
            "url": "https://bank.example.com/api"
        }
    
    @patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.A2ADiscoveryService')
    @patch.object(AgentsController, 'publish_or_update_agents')
    def test_discover_public_agent_success(
        self,
        mock_publish,
        mock_discovery_client,
        mock_agent_card_json
    ):
        """Test successful discovery of public agent (no authentication)."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_discovery_client.return_value.__enter__.return_value = mock_client_instance
        
        wxo_spec = {
            "spec_version": "v1",
            "kind": "external",
            "name": "weather_agent",
            "title": "Weather Agent",
            "provider": "external_chat/A2A/0.3.0",
            "description": "Weather information agent",
            "api_url": "https://weather.example.com/api"
        }
        mock_client_instance.discover_and_convert.return_value = wxo_spec
        
        # Execute
        controller = AgentsController()
        controller.discover_and_import_agent(
            base_url="https://weather.example.com",
            endpoint=".well-known/agent-card.json",
            agent_name="weather_agent"
        )
        
        # Verify
        mock_client_instance.discover_and_convert.assert_called_once()
        mock_publish.assert_called_once()
        # Verify that an ExternalAgent object was passed (not a dict)
        call_args = mock_publish.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].name == "weather_agent"
        assert call_args[0].title == "Weather Agent"
    
    @patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.A2ADiscoveryService')
    @patch.object(AgentsController, 'publish_or_update_agents')
    def test_discover_authenticated_agent_with_app_id(
        self,
        mock_publish,
        mock_discovery_client,
        mock_authenticated_agent_card_json
    ):
        """Test successful discovery of authenticated agent with app_id."""
        # Setup discovery mock
        mock_client_instance = MagicMock()
        mock_discovery_client.return_value.__enter__.return_value = mock_client_instance
        
        wxo_spec = {
            "spec_version": "v1",
            "kind": "external",
            "name": "banking_agent",
            "title": "Banking Agent",
            "provider": "external_chat/A2A/0.3.0",
            "description": "Secure banking agent",
            "api_url": "https://bank.example.com/api",
            "app_id": "my-banking-connection"
        }
        mock_client_instance.discover_and_convert.return_value = wxo_spec
        
        # Execute
        controller = AgentsController()
        controller.discover_and_import_agent(
            base_url="https://bank.example.com",
            endpoint=".well-known/agent-card.json",
            agent_name="banking_agent",
            app_id="my-banking-connection"
        )
        
        # Verify discovery was called with app_id
        call_kwargs = mock_client_instance.discover_and_convert.call_args[1]
        assert call_kwargs['app_id'] == "my-banking-connection"
        
        mock_publish.assert_called_once()
        # Verify that an ExternalAgent object was passed with app_id
        call_args = mock_publish.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].name == "banking_agent"
        assert call_args[0].app_id == "my-banking-connection"
    
    @patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.A2ADiscoveryService')
    def test_discover_url_does_not_exist(self, mock_discovery_client):
        """Test discovery when URL does not exist."""
        mock_client_instance = MagicMock()
        mock_discovery_client.return_value.__enter__.return_value = mock_client_instance
        mock_client_instance.discover_and_convert.side_effect = requests.RequestException("Connection failed")
        
        controller = AgentsController()
        
        with pytest.raises(SystemExit):
            controller.discover_and_import_agent(
                base_url="https://nonexistent.example.com"
            )
    
    @patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.A2ADiscoveryService')
    def test_discover_invalid_agent_card_format(self, mock_discovery_client):
        """Test discovery when agent card has invalid format."""
        mock_client_instance = MagicMock()
        mock_discovery_client.return_value.__enter__.return_value = mock_client_instance
        mock_client_instance.discover_and_convert.side_effect = ValueError("Invalid agent card format")
        
        controller = AgentsController()
        
        with pytest.raises(SystemExit):
            controller.discover_and_import_agent(
                base_url="https://example.com"
            )
