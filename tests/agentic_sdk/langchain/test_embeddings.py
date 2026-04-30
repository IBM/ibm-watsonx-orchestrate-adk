"""Unit tests for WxOEmbeddings class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
try:
    from ibm_watsonx_orchestrate_sdk.langchain.embeddings import WxOEmbeddings
    from ibm_watsonx_orchestrate_sdk.common.session import AgenticSession, RequestIdentity
except ImportError:
    pytest.skip(allow_module_level=True)

# Test fixtures for creating mock sessions
@pytest.fixture
def mock_runs_elsewhere_session():
    """Create a mock AgenticSession for runs-elsewhere mode."""
    mock_authenticator = Mock()
    mock_token_manager = Mock()
    mock_token_manager.get_token.return_value = "test-token-123"
    mock_authenticator.token_manager = mock_token_manager
    
    return AgenticSession(
        mode="runs-elsewhere",
        base_url="https://api.example.com/v1/orchestrate",
        access_token=None,
        authenticator=mock_authenticator,
        identity=RequestIdentity(
            tenant_id="test-tenant",
            user_id="test-user",
            thread_id=None,
            run_id=None,
            deployment_platform=None
        ),
        verify=True
    )


@pytest.fixture
def mock_runs_on_session():
    """Create a mock AgenticSession for runs-on mode."""
    return AgenticSession(
        mode="runs-on",
        base_url="http://proxy.internal/v1/orchestrate",
        access_token="runtime-token-456",
        authenticator=None,
        identity=RequestIdentity(
            tenant_id="runtime-tenant",
            user_id="runtime-user",
            thread_id="thread-123",
            run_id="run-456",
            deployment_platform="wxo"
        ),
        verify=True
    )


@pytest.fixture
def mock_local_session():
    """Create a mock AgenticSession for local mode."""
    return AgenticSession(
        mode="local",
        base_url="http://localhost:4321/api/v1",
        access_token="local-token-789",
        authenticator=None,
        identity=None,
        verify=False
    )


class TestWxOEmbeddingsInitialization:
    """Test WxOEmbeddings initialization with different modes."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_init_with_instance_credentials(self, mock_client_class, mock_runs_elsewhere_session):
        """Test initialization with instance credentials (runs-elsewhere mode)."""
        # Mock Client to return our session
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com"
        )
        
        # Verify Client was created with correct parameters
        mock_client_class.assert_called_once_with(
            api_key="test-api-key",
            instance_url="https://api.example.com",
            iam_url=None,
            auth_type=None,
            verify=None,
            authenticator=None,
            local=False,
            execution_context=None,
            session=None
        )
        
        # Verify embeddings configuration
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._session == mock_runs_elsewhere_session
        assert embeddings._client == mock_client_instance
        assert embeddings._user_id == "test-user"
        assert embeddings._tenant_id == "test-tenant"
        
        # Verify base URL and headers
        assert embeddings.openai_api_base == "https://api.example.com/v1/orchestrate/gateway/model"
        assert "Authorization" in embeddings.default_headers
        assert embeddings.default_headers["X-User-ID"] == "test-user"
        assert embeddings.default_headers["X-Tenant-ID"] == "test-tenant"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_init_with_execution_context(self, mock_client_class, mock_runs_on_session):
        """Test initialization with execution context (runs-on mode)."""
        # Mock Client to return our session
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_on_session
        mock_client_class.return_value = mock_client_instance
        
        execution_context = {
            "access_token": "runtime-token-456",
            "api_proxy_url": "http://proxy.internal",
            "tenant_id": "runtime-tenant",
            "user_id": "runtime-user",
            "thread_id": "thread-123",
            "run_id": "run-456"
        }
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            execution_context=execution_context
        )
        
        # Verify Client was created with execution_context
        mock_client_class.assert_called_once_with(
            api_key=None,
            instance_url=None,
            iam_url=None,
            auth_type=None,
            verify=None,
            authenticator=None,
            local=False, # technically 'runs-on' mode
            execution_context=execution_context,
            session=None
        )
        
        # Verify embeddings configuration
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._session == mock_runs_on_session
        assert embeddings._user_id == "runtime-user"
        assert embeddings._tenant_id == "runtime-tenant"
        
        # Verify base URL - runs-on mode doesn't add /orchestrate
        assert embeddings.openai_api_base == "http://proxy.internal/v1/orchestrate/gateway/model"
        # Verify headers contain runtime token
        assert embeddings.default_headers["Authorization"] == "Bearer runtime-token-456"
        assert embeddings.default_headers["X-User-ID"] == "runtime-user"
        assert embeddings.default_headers["X-Tenant-ID"] == "runtime-tenant"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_init_with_session(self, mock_client_class, mock_local_session):
        """Test initialization with pre-configured session (local mode)."""
        # Mock Client to return our session
        mock_client_instance = Mock()
        mock_client_instance.session = mock_local_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            session=mock_local_session
        )
        
        # Verify Client was created with session
        mock_client_class.assert_called_once_with(
            api_key=None,
            instance_url=None,
            iam_url=None,
            auth_type=None,
            verify=None,
            authenticator=None,
            local=False, # technically 'runs-on' mode
            execution_context=None,
            session=mock_local_session
        )
        
        # Verify embeddings configuration
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._session == mock_local_session
        assert embeddings._user_id is None  # No identity in local mode
        assert embeddings._tenant_id is None
        
        # Verify base URL for local mode
        assert embeddings.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        assert embeddings.default_headers["Authorization"] == "Bearer local-token-789"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_init_with_local_mode(self, mock_client_class, mock_local_session):
        """Test initialization with local=True."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_local_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="local-token",
            instance_url="http://localhost:4321",
            local=True
        )
        
        # Verify Client was created with local=True
        mock_client_class.assert_called_once_with(
            api_key="local-token",
            instance_url="http://localhost:4321",
            iam_url=None,
            auth_type=None,
            verify=None,
            authenticator=None,
            local=True,
            execution_context=None,
            session=None
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._session == mock_local_session
        # Verify base URL for local mode
        assert embeddings.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_init_with_verify_parameter(self, mock_client_class, mock_runs_elsewhere_session):
        """Test initialization with verify parameter."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com",
            verify=False
        )
        
        # Verify Client was created with verify=False
        mock_client_class.assert_called_once_with(
            api_key="test-api-key",
            instance_url="https://api.example.com",
            iam_url=None,
            auth_type=None,
            verify=False,
            authenticator=None,
            local=False,
            execution_context=None,
            session=None
        )
        
        assert embeddings.model == "openai/text-embedding-3-small"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_init_with_additional_kwargs(self, mock_client_class, mock_runs_elsewhere_session):
        """Test initialization with additional OpenAIEmbeddings parameters."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com",
            chunk_size=100,
            max_retries=5,
            request_timeout=60.0
        )
        
        assert embeddings.chunk_size == 100
        assert embeddings.max_retries == 5
        assert embeddings.request_timeout == 60.0
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_init_fails_without_authentication(self, mock_client_class):
        """Test initialization fails when session has no authentication."""
        # Create session without access_token or authenticator
        invalid_session = AgenticSession(
            mode="runs-elsewhere",
            base_url="https://api.example.com/v1/orchestrate",
            access_token=None,
            authenticator=None,
            identity=None,
            verify=True
        )
        
        mock_client_instance = Mock()
        mock_client_instance.session = invalid_session
        mock_client_class.return_value = mock_client_instance
        
        with pytest.raises(ValueError, match="No authentication method available"):
            WxOEmbeddings(
                model="openai/text-embedding-3-small",
                api_key="test-api-key",
                instance_url="https://api.example.com"
            )


class TestWxOEmbeddingsTokenManagement:
    """Test token refresh and management."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_get_current_token_with_authenticator(self, mock_client_class, mock_runs_elsewhere_session):
        """Test _get_current_token with authenticator (runs-elsewhere mode)."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com"
        )
        
        # Get token - should call authenticator's token_manager
        token = embeddings._get_current_token()
        assert token == "test-token-123"
        mock_runs_elsewhere_session.authenticator.token_manager.get_token.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_get_current_token_with_access_token(self, mock_client_class, mock_runs_on_session):
        """Test _get_current_token with access_token (runs-on mode)."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_on_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            execution_context={
                "access_token": "runtime-token-456",
                "api_proxy_url": "http://proxy.internal"
            }
        )
        
        # Get token - should return access_token directly
        token = embeddings._get_current_token()
        assert token == "runtime-token-456"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.embed_query')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_embed_query_refreshes_token(self, mock_client_class, mock_super_embed, mock_runs_elsewhere_session):
        """Test that embed_query() refreshes token before making request."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        # Mock the parent class method
        mock_super_embed.return_value = [0.1, 0.2, 0.3]
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com"
        )
        
        # Call embed_query - should refresh token
        result = embeddings.embed_query("test text")
        
        # Token should be refreshed in headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        mock_runs_elsewhere_session.authenticator.token_manager.get_token.assert_called_once()
        assert result == [0.1, 0.2, 0.3]
        mock_super_embed.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.embed_documents')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_embed_documents_refreshes_token(self, mock_client_class, mock_super_embed, mock_runs_elsewhere_session):
        """Test that embed_documents() refreshes token before making request."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        # Mock the parent class method
        mock_super_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com"
        )
        
        # Call embed_documents - should refresh token
        result = embeddings.embed_documents(["text1", "text2"])
        
        # Token should be refreshed in headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        mock_runs_elsewhere_session.authenticator.token_manager.get_token.assert_called_once()
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_super_embed.assert_called_once()


class TestWxOEmbeddingsAsyncMethods:
    """Test async embedding methods."""
    
    @pytest.mark.asyncio
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.aembed_query')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    async def test_aembed_query_refreshes_token(self, mock_client_class, mock_super_aembed, mock_runs_elsewhere_session):
        """Test that aembed_query() refreshes token before making request."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        # Mock the parent class async method
        mock_super_aembed.return_value = [0.1, 0.2, 0.3]
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com"
        )
        
        # Call aembed_query - should refresh token
        result = await embeddings.aembed_query("test text")
        
        # Token should be refreshed in headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        mock_runs_elsewhere_session.authenticator.token_manager.get_token.assert_called_once()
        assert result == [0.1, 0.2, 0.3]
        mock_super_aembed.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.OpenAIEmbeddings.aembed_documents')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    async def test_aembed_documents_refreshes_token(self, mock_client_class, mock_super_aembed, mock_runs_elsewhere_session):
        """Test that aembed_documents() refreshes token before making request."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        # Mock the parent class async method
        mock_super_aembed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com"
        )
        
        # Call aembed_documents - should refresh token
        result = await embeddings.aembed_documents(["text1", "text2"])
        
        # Token should be refreshed in headers
        assert embeddings.default_headers["Authorization"] == "Bearer test-token-123"
        mock_runs_elsewhere_session.authenticator.token_manager.get_token.assert_called_once()
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_super_aembed.assert_called_once()


class TestWxOEmbeddingsHelperMethods:
    """Test helper class methods for creating WxOEmbeddings instances."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_from_instance_credentials(self, mock_client_class, mock_runs_elsewhere_session):
        """Test from_instance_credentials helper method."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings.from_instance_credentials(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com"
        )
        
        # Verify Client was created correctly
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["api_key"] == "test-api-key"
        assert call_kwargs["instance_url"] == "https://api.example.com"
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._session == mock_runs_elsewhere_session
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_from_execution_context(self, mock_client_class, mock_runs_on_session):
        """Test from_execution_context helper method."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_on_session
        mock_client_class.return_value = mock_client_instance
        
        execution_context = {
            "access_token": "runtime-token-456",
            "api_proxy_url": "http://proxy.internal"
        }
        
        embeddings = WxOEmbeddings.from_execution_context(
            model="openai/text-embedding-3-small",
            execution_context=execution_context
        )
        
        # Verify Client was created with execution_context
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["execution_context"] == execution_context
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._session == mock_runs_on_session
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_from_session(self, mock_client_class, mock_local_session):
        """Test from_session helper method."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_local_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings.from_session(
            model="openai/text-embedding-3-small",
            session=mock_local_session
        )
        
        # Verify session was passed to constructor
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["session"] == mock_local_session
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._session == mock_local_session
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client.from_runnable_config')
    def test_from_runnable_config(self, mock_from_runnable_config, mock_runs_on_session):
        """Test from_runnable_config helper method."""
        # Mock Client.from_runnable_config to return a client with session
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_on_session
        mock_from_runnable_config.return_value = mock_client_instance
        
        config = {
            "configurable": {
                "execution_context": {
                    "access_token": "runtime-token-456",
                    "api_proxy_url": "http://proxy.internal"
                }
            }
        }
        
        embeddings = WxOEmbeddings.from_runnable_config(
            model="openai/text-embedding-3-small",
            config=config
        )
        
        # Verify Client.from_runnable_config was called
        mock_from_runnable_config.assert_called_once_with(config, verify=None)
        
        assert embeddings.model == "openai/text-embedding-3-small"
        assert embeddings._session == mock_runs_on_session
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_from_instance_credentials_with_verify(self, mock_client_class, mock_runs_elsewhere_session):
        """Test from_instance_credentials with verify parameter."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_elsewhere_session
        mock_client_class.return_value = mock_client_instance
        
        embeddings = WxOEmbeddings.from_instance_credentials(
            model="openai/text-embedding-3-small",
            api_key="test-api-key",
            instance_url="https://api.example.com",
            verify=False
        )
        
        # Verify Client was created with verify=False
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["verify"] == False
        
        assert embeddings.model == "openai/text-embedding-3-small"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client')
    def test_from_execution_context_with_verify(self, mock_client_class, mock_runs_on_session):
        """Test from_execution_context with verify parameter."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_on_session
        mock_client_class.return_value = mock_client_instance
        
        execution_context = {
            "access_token": "runtime-token-456",
            "api_proxy_url": "http://proxy.internal"
        }
        
        embeddings = WxOEmbeddings.from_execution_context(
            model="openai/text-embedding-3-small",
            execution_context=execution_context,
            verify=False
        )
        
        # Verify verify parameter was passed
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["verify"] == False
        
        assert embeddings.model == "openai/text-embedding-3-small"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.embeddings.Client.from_runnable_config')
    def test_from_runnable_config_with_verify(self, mock_from_runnable_config, mock_runs_on_session):
        """Test from_runnable_config with verify parameter."""
        mock_client_instance = Mock()
        mock_client_instance.session = mock_runs_on_session
        mock_from_runnable_config.return_value = mock_client_instance
        
        config = {
            "configurable": {
                "execution_context": {
                    "access_token": "runtime-token-456",
                    "api_proxy_url": "http://proxy.internal"
                }
            }
        }
        
        embeddings = WxOEmbeddings.from_runnable_config(
            model="openai/text-embedding-3-small",
            config=config,
            verify=False
        )
        
        # Verify Client.from_runnable_config was called with verify
        mock_from_runnable_config.assert_called_once_with(config, verify=False)
        
        assert embeddings.model == "openai/text-embedding-3-small"
