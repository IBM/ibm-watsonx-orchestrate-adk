"""Unit tests for WxOEmbeddings class."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from ibm_watsonx_orchestrate_sdk.langchain.embeddings import WxOEmbeddings


class TestWxOEmbeddingsInitialization:
    """Test WxOEmbeddings initialization with different authentication modes."""
    
    def test_init_with_agent_api_key_runtime_mode(self):
        """Test initialization with agent_api_key (runtime mode)."""
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            agent_api_key="test-agent-key",
            user_id="test-user",
            tenant_id="test-tenant",
            wxo_base_url="http://localhost:4321"
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._wxo_base_url == "http://localhost:4321"
        assert embeddings._user_id == "test-user"
        assert embeddings._tenant_id == "test-tenant"
        assert embeddings._client is None  # No Client in runtime mode
        # Local dev URL includes /api prefix
        assert embeddings.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        assert "Authorization" in embeddings.default_headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-agent-key"
        assert embeddings.default_headers["X-User-ID"] == "test-user"
        assert embeddings.default_headers["X-Tenant-ID"] == "test-tenant"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_init_with_api_key_standalone_mode(self, mock_credentials, mock_client):
        """Test initialization with api_key (standalone mode)."""
        # Mock the Client - token is set on client.token during initialization
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._wxo_base_url == "http://localhost:4321"
        assert embeddings._user_id is None
        assert embeddings._tenant_id is None
        assert embeddings._client is not None  # Client created in standalone mode
        # Local dev URL includes /api prefix
        assert embeddings.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        assert "Authorization" in embeddings.default_headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        assert "X-User-ID" not in embeddings.default_headers
        assert "X-Tenant-ID" not in embeddings.default_headers
        
        # Verify Credentials and Client were created
        mock_credentials.assert_called_once_with(
            url="http://localhost:4321",
            api_key="test-api-key",
            iam_url=None,
            auth_type=None
        )
        mock_client.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_init_with_api_key_iam_url_and_auth_type(self, mock_credentials, mock_client):
        """Test initialization with api_key, iam_url, and auth_type (standalone mode with custom IAM)."""
        # Mock the Client - token is set on client.token during initialization
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-456"
        mock_client.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            wxo_base_url="https://api.staging.example.com",
            iam_url="https://iam.platform.test.saas.ibm.com",
            auth_type="mcsp_v2"
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._wxo_base_url == "https://api.staging.example.com"
        assert embeddings._client is not None  # Client created in standalone mode
        # SaaS URL does not include /api prefix
        assert embeddings.openai_api_base == "https://api.staging.example.com/v1/orchestrate/gateway/model"
        assert "Authorization" in embeddings.default_headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-456"
        
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
            WxOEmbeddings(
                model="openai/text-embedding-3-small",
                agent_api_key="test-key"
            )
    
    def test_init_empty_wxo_base_url(self):
        """Test initialization fails with empty wxo_base_url."""
        with pytest.raises(ValueError, match="No URL Provided"):
            WxOEmbeddings(
                model="openai/text-embedding-3-small",
                agent_api_key="test-key",
                wxo_base_url=""
            )
    
    def test_init_invalid_url_format(self):
        """Test initialization fails with invalid URL format (non-https, non-local)."""
        with pytest.raises(ValueError, match="Invalid URL Format"):
            WxOEmbeddings(
                model="openai/text-embedding-3-small",
                agent_api_key="test-key",
                wxo_base_url="http://production.example.com"
            )
    
    def test_init_missing_credentials_saas(self):
        """Test initialization fails without credentials for SaaS environment."""
        with pytest.raises(ValueError, match="api_key is required for SaaS standalone usage"):
            WxOEmbeddings(
                model="openai/text-embedding-3-small",
                wxo_base_url="https://api.example.com"
            )
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_init_local_without_api_key(self, mock_credentials, mock_client):
        """Test initialization succeeds for local environment without api_key."""
        # Mock the Client - token is set on client.token during initialization
        mock_client_instance = Mock()
        mock_client_instance.token = "local-token-123"
        mock_client.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            wxo_base_url="http://localhost:4321"
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._wxo_base_url == "http://localhost:4321"
        assert embeddings._client is not None  # Client created even without api_key for local
        assert embeddings.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        assert "Authorization" in embeddings.default_headers
        assert embeddings.default_headers["Authorization"] == "Bearer local-token-123"
        
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
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            agent_api_key="test-key",
            wxo_base_url="http://localhost:4321/"
        )
        
        assert embeddings._wxo_base_url == "http://localhost:4321"
        # Local dev URL includes /api prefix
        assert embeddings.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
    
    def test_init_with_additional_kwargs(self):
        """Test initialization with additional OpenAIEmbeddings parameters."""
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            agent_api_key="test-key",
            wxo_base_url="http://localhost:4321",
            chunk_size=100,
            max_retries=5,
            request_timeout=60.0
        )
        
        assert embeddings.chunk_size == 100
        assert embeddings.max_retries == 5
        assert embeddings.request_timeout == 60.0


class TestWxOEmbeddingsTokenManagement:
    """Test token refresh and management."""
    
    def test_get_current_token_runtime_mode(self):
        """Test _get_current_token in runtime mode."""
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            agent_api_key="test-agent-key",
            wxo_base_url="http://localhost:4321"
        )
        
        token = embeddings._get_current_token()
        assert token == "test-agent-key"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_get_current_token_api_key_mode(self, mock_credentials, mock_client):
        """Test _get_current_token in API key mode with refresh."""
        # Mock the Client with ServiceInstance that has _get_token method
        mock_service_instance = Mock()
        mock_service_instance._get_token.return_value = "test-token-refreshed"
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client_instance.service_instance = mock_service_instance
        mock_client.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        # Initial token from client.token
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        
        # Each call to _get_current_token() calls service_instance._get_token() for refresh
        token1 = embeddings._get_current_token()
        assert token1 == "test-token-refreshed"
        assert mock_service_instance._get_token.call_count == 1
        
        token2 = embeddings._get_current_token()
        assert token2 == "test-token-refreshed"
        assert mock_service_instance._get_token.call_count == 2
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.embed_query')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_embed_query_refreshes_token_api_key_mode(self, mock_credentials, mock_client, mock_super_embed):
        """Test that embed_query() refreshes token in API key mode."""
        # Mock the Client with ServiceInstance that has _get_token method
        mock_service_instance = Mock()
        mock_service_instance._get_token.return_value = "test-token-refreshed"
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client_instance.service_instance = mock_service_instance
        mock_client.return_value = mock_client_instance
        
        # Mock the parent class method
        mock_super_embed.return_value = [0.1, 0.2, 0.3]
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        # Initial token
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        
        # Call embed_query - should refresh token
        result = embeddings.embed_query("test text")
        
        # Token should be refreshed in headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-refreshed"
        assert mock_service_instance._get_token.call_count == 1
        assert result == [0.1, 0.2, 0.3]
        mock_super_embed.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.embed_documents')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_embed_documents_refreshes_token_api_key_mode(self, mock_credentials, mock_client, mock_super_embed):
        """Test that embed_documents() refreshes token in API key mode."""
        # Mock the Client with ServiceInstance that has _get_token method
        mock_service_instance = Mock()
        mock_service_instance._get_token.return_value = "test-token-refreshed"
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client_instance.service_instance = mock_service_instance
        mock_client.return_value = mock_client_instance
        
        # Mock the parent class method
        mock_super_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        # Initial token
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        
        # Call embed_documents - should refresh token
        result = embeddings.embed_documents(["text1", "text2"])
        
        # Token should be refreshed in headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-refreshed"
        assert mock_service_instance._get_token.call_count == 1
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_super_embed.assert_called_once()
    
    def test_embed_query_no_token_refresh_runtime_mode(self):
        """Test that embed_query() does not refresh token in runtime mode."""
        with patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.embed_query') as mock_super_embed:
            mock_super_embed.return_value = [0.1, 0.2, 0.3]
            
            embeddings = WxOEmbeddings(
                model="openai/text-embedding-3-small",
                agent_api_key="test-agent-key",
                wxo_base_url="http://localhost:4321"
            )
            
            # Initial token
            initial_token = embeddings.default_headers["Authorization"]
            
            # Call embed_query - should NOT refresh token (no _client)
            result = embeddings.embed_query("test text")
            
            # Token should remain the same
            assert embeddings.default_headers["Authorization"] == initial_token
            assert result == [0.1, 0.2, 0.3]
            mock_super_embed.assert_called_once()


class TestWxOEmbeddingsAsyncMethods:
    """Test async embedding methods."""
    
    @pytest.mark.asyncio
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.aembed_query')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    async def test_aembed_query_refreshes_token(self, mock_credentials, mock_client, mock_super_aembed):
        """Test that aembed_query() refreshes token in API key mode."""
        # Mock the Client with ServiceInstance that has _get_token method
        mock_service_instance = Mock()
        mock_service_instance._get_token.return_value = "test-token-refreshed"
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client_instance.service_instance = mock_service_instance
        mock_client.return_value = mock_client_instance
        
        # Mock the parent class async method
        mock_super_aembed.return_value = [0.1, 0.2, 0.3]
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        # Initial token
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        
        # Call aembed_query - should refresh token
        result = await embeddings.aembed_query("test text")
        
        # Token should be refreshed in headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-refreshed"
        assert mock_service_instance._get_token.call_count == 1
        assert result == [0.1, 0.2, 0.3]
        mock_super_aembed.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.aembed_documents')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    async def test_aembed_documents_refreshes_token(self, mock_credentials, mock_client, mock_super_aembed):
        """Test that aembed_documents() refreshes token in API key mode."""
        # Mock the Client with ServiceInstance that has _get_token method
        mock_service_instance = Mock()
        mock_service_instance._get_token.return_value = "test-token-refreshed"
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client_instance.service_instance = mock_service_instance
        mock_client.return_value = mock_client_instance
        
        # Mock the parent class async method
        mock_super_aembed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            wxo_base_url="http://localhost:4321"
        )
        
        # Initial token
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        
        # Call aembed_documents - should refresh token
        result = await embeddings.aembed_documents(["text1", "text2"])
        
        # Token should be refreshed in headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-refreshed"
        assert mock_service_instance._get_token.call_count == 1
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_super_aembed.assert_called_once()


class TestWxOEmbeddingsFromConfig:
    """Test from_config class method."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_from_config_with_agent_api_key(self, mock_credentials, mock_client):
        """Test from_config with agent_api_key (runtime mode)."""
        config = {
            "configurable": {
                "agent_api_key": "test-agent-key",
                "user_id": "test-user",
                "tenant_id": "test-tenant",
                "wxo_base_url": "http://localhost:4321"
            }
        }
        
        embeddings = WxOEmbeddings.from_config(
            config=config,
            model="openai/text-embedding-3-small"
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._wxo_base_url == "http://localhost:4321"
        assert embeddings._user_id == "test-user"
        assert embeddings._tenant_id == "test-tenant"
        assert embeddings._client is None
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_from_config_with_api_key(self, mock_credentials, mock_client):
        """Test from_config with api_key (standalone mode)."""
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client.return_value = mock_client_instance
        
        config = {
            "configurable": {
                "api_key": "test-api-key",
                "wxo_base_url": "http://localhost:4321"
            }
        }
        
        embeddings = WxOEmbeddings.from_config(
            config=config,
            model="openai/text-embedding-3-small"
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._wxo_base_url == "http://localhost:4321"
        assert embeddings._client is not None
    
    def test_from_config_missing_wxo_base_url(self):
        """Test from_config fails without wxo_base_url."""
        config = {
            "configurable": {
                "agent_api_key": "test-key"
            }
        }
        
        with pytest.raises(ValueError, match="wxo_base_url not found"):
            WxOEmbeddings.from_config(
                config=config,
                model="openai/text-embedding-3-small"
            )
    
    def test_from_config_missing_credentials_saas(self):
        """Test from_config fails without credentials for SaaS."""
        config = {
            "configurable": {
                "wxo_base_url": "https://api.example.com"
            }
        }
        
        with pytest.raises(ValueError, match="Neither agent_api_key nor api_key found"):
            WxOEmbeddings.from_config(
                config=config,
                model="openai/text-embedding-3-small"
            )
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_from_config_local_without_credentials(self, mock_credentials, mock_client):
        """Test from_config succeeds for local without credentials."""
        mock_client_instance = Mock()
        mock_client_instance.token = "local-token-123"
        mock_client.return_value = mock_client_instance
        
        config = {
            "configurable": {
                "wxo_base_url": "http://localhost:4321"
            }
        }
        
        embeddings = WxOEmbeddings.from_config(
            config=config,
            model="openai/text-embedding-3-small"
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._wxo_base_url == "http://localhost:4321"
        assert embeddings._client is not None
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Credentials')
    def test_from_config_with_additional_kwargs(self, mock_credentials, mock_client):
        """Test from_config with additional parameters."""
        mock_client_instance = Mock()
        mock_client_instance.token = "test-token-123"
        mock_client.return_value = mock_client_instance
        
        config = {
            "configurable": {
                "api_key": "test-api-key",
                "wxo_base_url": "http://localhost:4321",
                "iam_url": "https://iam.test.com",
                "auth_type": "mcsp"
            }
        }
        
        embeddings = WxOEmbeddings.from_config(
            config=config,
            model="openai/text-embedding-3-small",
            chunk_size=50,
            max_retries=3
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings.chunk_size == 50
        assert embeddings.max_retries == 3
        
        # Verify Credentials was created with iam_url and auth_type
        mock_credentials.assert_called_once_with(
            url="http://localhost:4321",
            api_key="test-api-key",
            iam_url="https://iam.test.com",
            auth_type="mcsp"
        )
