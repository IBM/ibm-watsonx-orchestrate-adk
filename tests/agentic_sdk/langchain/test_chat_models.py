"""Unit tests for ChatWxO class."""

import pytest
from unittest.mock import Mock, patch
from ibm_watsonx_orchestrate_sdk.langchain.chat_models import ChatWxO


class TestChatWxOInitialization:
    """Test ChatWxO initialization with different authentication modes."""
    
    def test_init_with_agent_api_key_runtime_mode(self):
        """Test initialization with agent_api_key (runtime mode)."""
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-agent-key",
            user_id="test-user",
            tenant_id="test-tenant",
            wxo_base_url="http://localhost:4321"
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._wxo_base_url == "http://localhost:4321"
        assert llm._user_id == "test-user"
        assert llm._tenant_id == "test-tenant"
        assert llm._client is None  # No Client in runtime mode
        # Local dev URL includes /api prefix
        assert llm.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        assert "Authorization" in llm.default_headers
        assert llm.default_headers["Authorization"] == "Bearer test-agent-key"
        assert llm.default_headers["X-User-ID"] == "test-user"
        assert llm.default_headers["X-Tenant-ID"] == "test-tenant"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Credentials')
    def test_init_with_api_key_standalone_mode(self, mock_credentials, mock_client):
        """Test initialization with api_key (standalone mode)."""
        # Mock the Client - token is set on client.token during initialization
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client.return_value = mock_client_instance
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._wxo_base_url == "http://localhost:4321"
        assert llm._user_id is None
        assert llm._tenant_id is None
        assert llm._client is not None  # Client created in standalone mode
        # Local dev URL includes /api prefix
        assert llm.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        assert "Authorization" in llm.default_headers
        assert llm.default_headers["Authorization"] == "Bearer test-token-123"
        assert "X-User-ID" not in llm.default_headers
        assert "X-Tenant-ID" not in llm.default_headers
        
        # Verify Credentials and Client were created
        mock_credentials.assert_called_once_with(
            url="http://localhost:4321",
            api_key="test-api-key",
            iam_url=None,
            auth_type=None
        )
        mock_client.assert_called_once()
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Credentials')
    def test_init_with_api_key_iam_url_and_auth_type(self, mock_credentials, mock_client):
        """Test initialization with api_key, iam_url, and auth_type (standalone mode with custom IAM)."""
        # Mock the Client - token is set on client.token during initialization
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-456"
        mock_client.return_value = mock_client_instance
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            api_key="test-api-key",
            wxo_base_url="https://api.staging.example.com",
            iam_url="https://iam.platform.test.saas.ibm.com",
            auth_type="mcsp_v2"
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._wxo_base_url == "https://api.staging.example.com"
        assert llm._client is not None  # Client created in standalone mode
        # SaaS URL does not include /api prefix
        assert llm.openai_api_base == "https://api.staging.example.com/v1/orchestrate/gateway/model"
        assert "Authorization" in llm.default_headers
        assert llm.default_headers["Authorization"] == "Bearer test-token-456"
        
        # Verify Credentials was created with iam_url and auth_type
        mock_credentials.assert_called_once_with(
            url="https://api.staging.example.com",
            api_key="test-api-key",
            iam_url="https://iam.platform.test.saas.ibm.com",
            auth_type="mcsp_v2"
        )
        mock_client.assert_called_once()
    
    
    def test_init_missing_wxo_base_url(self):
        """Test initialization fails without wxo_base_url."""
        with pytest.raises(TypeError, match="missing required argument: 'wxo_base_url'"):
            ChatWxO(
                model="virtual-model/watsonx/test-model",
                agent_api_key="test-key"
            )
    
    def test_init_empty_wxo_base_url(self):
        """Test initialization fails with empty wxo_base_url."""
        with pytest.raises(ValueError, match="No URL Provided"):
            ChatWxO(
                model="virtual-model/watsonx/test-model",
                agent_api_key="test-key",
                wxo_base_url=""
            )
    
    def test_init_invalid_url_format(self):
        """Test initialization fails with invalid URL format (non-https, non-local)."""
        with pytest.raises(ValueError, match="Invalid URL Format"):
            ChatWxO(
                model="virtual-model/watsonx/test-model",
                agent_api_key="test-key",
                wxo_base_url="http://production.example.com"
            )
    
    def test_init_missing_credentials_saas(self):
        """Test initialization fails without credentials for SaaS environment."""
        with pytest.raises(ValueError, match="api_key is required for SaaS standalone usage"):
            ChatWxO(
                model="virtual-model/watsonx/test-model",
                wxo_base_url="https://api.example.com"
            )
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Credentials')
    def test_init_local_without_api_key(self, mock_credentials, mock_client):
        """Test initialization succeeds for local environment without api_key."""
        # Mock the Client - token is set on client.token during initialization
        mock_client_instance = Mock()
        mock_client_instance.token = "local-token-123"
        mock_client.return_value = mock_client_instance
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            wxo_base_url="http://localhost:4321"
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._wxo_base_url == "http://localhost:4321"
        assert llm._client is not None  # Client created even without api_key for local
        assert llm.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        assert "Authorization" in llm.default_headers
        assert llm.default_headers["Authorization"] == "Bearer local-token-123"
        
        # Verify Credentials was created without api_key (None)
        mock_credentials.assert_called_once_with(
            url="http://localhost:4321",
            api_key=None,
            iam_url=None,
            auth_type=None
        )
        mock_client.assert_called_once()
    
    def test_init_strips_trailing_slash_from_url(self):
        """Test that trailing slash is removed from wxo_base_url."""
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-key",
            wxo_base_url="http://localhost:4321/"
        )
        
        assert llm._wxo_base_url == "http://localhost:4321"
        # Local dev URL includes /api prefix
        assert llm.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
    
    def test_init_with_additional_kwargs(self):
        """Test initialization with additional ChatOpenAI parameters."""
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-key",
            wxo_base_url="http://localhost:4321",
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9
        )
        
        assert llm.temperature == 0.7
        assert llm.max_tokens == 1000


class TestChatWxOTokenManagement:
    """Test token refresh and management."""
    
    def test_get_current_token_runtime_mode(self):
        """Test _get_current_token in runtime mode."""
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-agent-key",
            wxo_base_url="http://localhost:4321"
        )
        
        token = llm._get_current_token()
        assert token == "test-agent-key"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Credentials')
    def test_get_current_token_api_key_mode(self, mock_credentials, mock_client):
        """Test _get_current_token in API key mode with refresh."""
        # Mock the Client with ServiceInstance that has _get_token method
        mock_service_instance = Mock()
        mock_service_instance._get_token.return_value = "test-token-refreshed"
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client_instance.service_instance = mock_service_instance
        mock_client.return_value = mock_client_instance
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        # Initial token from client.token
        assert llm.default_headers["Authorization"] == "Bearer test-token-123"
        
        # Each call to _get_current_token() calls service_instance._get_token() for refresh
        token1 = llm._get_current_token()
        assert token1 == "test-token-refreshed"
        assert mock_service_instance._get_token.call_count == 1
        
        token2 = llm._get_current_token()
        assert token2 == "test-token-refreshed"
        assert mock_service_instance._get_token.call_count == 2
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.invoke')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Credentials')
    def test_invoke_refreshes_token_api_key_mode(self, mock_credentials, mock_client, mock_super_invoke):
        """Test that invoke() refreshes token in API key mode."""
        # Mock the Client with ServiceInstance that has _get_token method
        mock_service_instance = Mock()
        mock_service_instance._get_token.return_value = "test-token-refreshed"
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client_instance.service_instance = mock_service_instance
        mock_client.return_value = mock_client_instance
        
        # Mock the parent invoke to return a simple response
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_super_invoke.return_value = mock_response
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        # Call invoke
        response = llm.invoke("Test message")
        
        # Verify token is in headers (refreshed before invoke)
        assert llm.default_headers["Authorization"] == "Bearer test-token-refreshed"
        assert response.content == "Test response"
        mock_super_invoke.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.invoke')
    def test_invoke_no_refresh_runtime_mode(self, mock_super_invoke):
        """Test that invoke() doesn't refresh token in runtime mode."""
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_super_invoke.return_value = mock_response
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-agent-key",
            wxo_base_url="http://localhost:4321"
        )
        
        original_token = llm.default_headers["Authorization"]
        
        # Call invoke
        response = llm.invoke("Test message")
        
        # Verify token wasn't changed
        assert llm.default_headers["Authorization"] == original_token
        assert response.content == "Test response"
        mock_super_invoke.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.ainvoke')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Credentials')
    @pytest.mark.asyncio
    async def test_ainvoke_refreshes_token_api_key_mode(self, mock_credentials, mock_client, mock_super_ainvoke):
        """Test that ainvoke() refreshes token in API key mode."""
        # Mock the Client with ServiceInstance that has _get_token method
        mock_service_instance = Mock()
        mock_service_instance._get_token.return_value = "test-token-refreshed"
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client_instance.service_instance = mock_service_instance
        mock_client.return_value = mock_client_instance
        
        # Mock the parent ainvoke to return a simple response
        mock_response = Mock()
        mock_response.content = "Test async response"
        mock_super_ainvoke.return_value = mock_response
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        # Call ainvoke
        response = await llm.ainvoke("Test message")
        
        # Verify token is in headers (refreshed before ainvoke)
        assert llm.default_headers["Authorization"] == "Bearer test-token-refreshed"
        assert response.content == "Test async response"
        mock_super_ainvoke.assert_called_once()


class TestChatWxOFromConfig:
    """Test from_config() classmethod."""
    
    def test_from_config_with_agent_api_key(self):
        """Test from_config with agent_api_key (runtime mode)."""
        config = {
            "configurable": {
                "agent_api_key": "test-agent-key",
                "user_id": "test-user",
                "tenant_id": "test-tenant",
                "wxo_base_url": "http://localhost:4321"
            }
        }
        
        llm = ChatWxO.from_config(
            config=config,
            model="virtual-model/watsonx/test-model",
            temperature=0.5
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._wxo_base_url == "http://localhost:4321"
        assert llm._user_id == "test-user"
        assert llm._tenant_id == "test-tenant"
        assert llm.temperature == 0.5
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Credentials')
    def test_from_config_with_api_key(self, mock_credentials, mock_client):
        """Test from_config with api_key (standalone mode)."""
        # Mock the Client - token is set on client.token during initialization
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token"
        mock_client.return_value = mock_client_instance
        
        config = {
            "configurable": {
                "api_key": "test-api-key",
                "wxo_base_url": "http://localhost:4321"
            }
        }
        
        llm = ChatWxO.from_config(
            config=config,
            model="virtual-model/watsonx/test-model"
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._wxo_base_url == "http://localhost:4321"
        assert llm._user_id is None
        assert llm._tenant_id is None
        assert llm._client is not None
    
    def test_from_config_missing_wxo_base_url(self):
        """Test from_config fails without wxo_base_url."""
        config = {
            "configurable": {
                "agent_api_key": "test-key"
            }
        }
        
        with pytest.raises(ValueError, match="wxo_base_url not found"):
            ChatWxO.from_config(config, model="virtual-model/watsonx/test-model")
    
    def test_from_config_missing_credentials(self):
        """Test from_config fails without any credentials."""
        config = {
            "configurable": {
                "wxo_base_url": "http://localhost:4321"
            }
        }
        
        with pytest.raises(ValueError, match="Neither agent_api_key nor api_key found"):
            ChatWxO.from_config(config, model="virtual-model/watsonx/test-model")
    
    def test_from_config_empty_configurable(self):
        """Test from_config with empty configurable dict."""
        config = {}
        
        with pytest.raises(ValueError, match="wxo_base_url not found"):
            ChatWxO.from_config(config, model="virtual-model/watsonx/test-model")


class TestChatWxOInheritedFeatures:
    """Test that inherited ChatOpenAI features work correctly."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.stream')
    def test_stream_inherited(self, mock_super_stream):
        """Test that stream() is inherited and works."""
        # Mock streaming chunks
        mock_chunks = [Mock(content="Hello"), Mock(content=" world")]
        mock_super_stream.return_value = iter(mock_chunks)
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-key",
            wxo_base_url="http://localhost:4321"
        )
        
        chunks = list(llm.stream("Test message"))
        
        assert len(chunks) == 2
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " world"
        mock_super_stream.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.batch')
    def test_batch_inherited(self, mock_super_batch):
        """Test that batch() is inherited and works."""
        mock_responses = [Mock(content="Response 1"), Mock(content="Response 2")]
        mock_super_batch.return_value = mock_responses
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-key",
            wxo_base_url="http://localhost:4321"
        )
        
        responses = llm.batch(["Message 1", "Message 2"])
        
        assert len(responses) == 2
        assert responses[0].content == "Response 1"
        assert responses[1].content == "Response 2"
        mock_super_batch.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.bind_tools')
    def test_bind_tools_inherited(self, mock_super_bind_tools):
        """Test that bind_tools() is inherited and works."""
        mock_bound_llm = Mock()
        mock_super_bind_tools.return_value = mock_bound_llm
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-key",
            wxo_base_url="http://localhost:4321"
        )
        
        tools = [{"type": "function", "function": {"name": "get_weather"}}]
        bound_llm = llm.bind_tools(tools)
        
        assert bound_llm == mock_bound_llm
        mock_super_bind_tools.assert_called_once_with(tools)
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.with_structured_output')
    def test_with_structured_output_inherited(self, mock_super_structured):
        """Test that with_structured_output() is inherited and works."""
        mock_structured_llm = Mock()
        mock_super_structured.return_value = mock_structured_llm
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            agent_api_key="test-key",
            wxo_base_url="http://localhost:4321"
        )
        
        class TestSchema:
            pass
        
        structured_llm = llm.with_structured_output(TestSchema)
        
        assert structured_llm == mock_structured_llm
        mock_super_structured.assert_called_once()
