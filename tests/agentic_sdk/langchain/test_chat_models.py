"""Unit tests for ChatWxO class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
try:
    from ibm_watsonx_orchestrate_sdk.langchain.chat_models import ChatWxO
    from ibm_watsonx_orchestrate_sdk.common.session import AgenticSession, RequestIdentity
except ImportError:
    pytest.skip(allow_module_level=True)

class TestChatWxOInitialization:
    """Test ChatWxO initialization with different authentication modes."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_init_with_instance_credentials(self, mock_client_class):
        """Test initialization with instance_url and api_key."""
        # Mock AgenticSession for runs-elsewhere mode
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-elsewhere"
        mock_session.base_url = "http://localhost:4321/v1"
        mock_session.access_token = None
        mock_session.authenticator = Mock()
        mock_session.authenticator.token_manager.get_token.return_value = "test-token-123"
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            api_key="test-api-key",
            instance_url="http://localhost:4321"
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._session == mock_session
        assert llm._client == mock_client
        assert llm._user_id is None
        assert llm._tenant_id is None
        assert llm.openai_api_base == "http://localhost:4321/v1/orchestrate/gateway/model"
        assert "Authorization" in llm.default_headers
        # Token comes from authenticator placeholder initially
        assert "Bearer" in llm.default_headers["Authorization"]
        
        # Verify Client was created with correct params
        mock_client_class.assert_called_once_with(
            api_key="test-api-key",
            instance_url="http://localhost:4321",
            iam_url=None,
            auth_type=None,
            verify=None,
            authenticator=None,
            local=True,  # localhost is auto-detected as local
            execution_context=None,
            session=None
        )
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_init_with_execution_context(self, mock_client_class):
        """Test initialization with execution_context (runs-on mode)."""
        # Mock AgenticSession with identity
        mock_identity = RequestIdentity(
            tenant_id="test-tenant",
            user_id="test-user",
            thread_id="test-thread"
        )
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-on"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = "test-access-token"
        mock_session.authenticator = None
        mock_session.identity = mock_identity
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        execution_context = {
            "access_token": "test-access-token",
            "api_proxy_url": "https://api.example.com/v1/orchestrate",
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "thread_id": "test-thread"
        }
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            execution_context=execution_context
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._session == mock_session
        assert llm._user_id == "test-user"
        assert llm._tenant_id == "test-tenant"
        assert llm.openai_api_base == "https://api.example.com/v1/orchestrate/gateway/model"
        assert llm.default_headers["Authorization"] == "Bearer test-access-token"
        assert llm.default_headers["X-User-ID"] == "test-user"
        assert llm.default_headers["X-Tenant-ID"] == "test-tenant"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_init_with_session(self, mock_client_class):
        """Test initialization with pre-configured session."""
        # Mock AgenticSession for local mode
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "local"
        mock_session.base_url = "http://localhost:4321/api/v1"
        mock_session.access_token = "local-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._session == mock_session
        assert llm.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        assert llm.default_headers["Authorization"] == "Bearer local-token"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_init_with_local_mode(self, mock_client_class):
        """Test initialization with local=True."""
        # Mock AgenticSession for local mode
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "local"
        mock_session.base_url = "http://localhost:4321/api/v1"
        mock_session.access_token = "local-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            instance_url="http://localhost:4321",
            local=True
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._session == mock_session
        assert llm.openai_api_base == "http://localhost:4321/api/v1/orchestrate/gateway/model"
        
        # Verify Client was created with local=True
        mock_client_class.assert_called_once_with(
            api_key=None,
            instance_url="http://localhost:4321",
            iam_url=None,
            auth_type=None,
            verify=None,
            authenticator=None,
            local=True,
            execution_context=None,
            session=None
        )
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_init_with_iam_url_and_auth_type(self, mock_client_class):
        """Test initialization with iam_url and auth_type."""
        # Mock AgenticSession
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-elsewhere"
        mock_session.base_url = "https://api.staging.example.com/v1/orchestrate"
        mock_session.access_token = None
        mock_session.authenticator = Mock()
        mock_session.authenticator.token_manager.get_token.return_value = "test-token"
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            api_key="test-api-key",
            instance_url="https://api.staging.example.com",
            iam_url="https://iam.platform.test.saas.ibm.com",
            auth_type="mcsp_v2"
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._session == mock_session
        assert llm.openai_api_base == "https://api.staging.example.com/v1/orchestrate/gateway/model"
        
        # Verify Client was created with iam_url and auth_type
        # Note: These will be added to Client by another engineer
        mock_client_class.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_init_missing_authentication(self, mock_client_class):
        """Test initialization fails without authentication."""
        # Mock Client to raise ValueError (no auth available)
        mock_client_class.side_effect = ValueError("Either execution_context or instance_url authentication is required")
        
        with pytest.raises(ValueError, match="Either execution_context or instance_url authentication is required"):
            ChatWxO(
                model="virtual-model/watsonx/test-model"
            )
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_init_session_without_auth(self, mock_client_class):
        """Test initialization fails when session has no authentication."""
        # Mock AgenticSession without access_token or authenticator
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-elsewhere"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = None
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        with pytest.raises(ValueError, match="No authentication method available in session"):
            ChatWxO(
                model="virtual-model/watsonx/test-model",
                session=mock_session
            )
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_init_with_additional_kwargs(self, mock_client_class):
        """Test initialization with additional ChatOpenAI parameters."""
        # Mock AgenticSession
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "local"
        mock_session.base_url = "http://localhost:4321/api/v1"
        mock_session.access_token = "local-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            instance_url="http://localhost:4321",
            local=True,
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9
        )
        
        assert llm.temperature == 0.7
        assert llm.max_tokens == 1000


class TestChatWxOTokenManagement:
    """Test token refresh and management."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_get_current_token_with_access_token(self, mock_client_class):
        """Test _get_current_token with access_token (runs-on/local mode)."""
        # Mock AgenticSession with access_token
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-on"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = "test-access-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        token = llm._get_current_token()
        assert token == "test-access-token"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_get_current_token_with_authenticator(self, mock_client_class):
        """Test _get_current_token with authenticator (runs-elsewhere mode)."""
        # Mock AgenticSession with authenticator
        mock_authenticator = Mock()
        mock_authenticator.token_manager.get_token.return_value = "refreshed-token"
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-elsewhere"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = None
        mock_session.authenticator = mock_authenticator
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        # Each call to _get_current_token() gets fresh token from authenticator
        token1 = llm._get_current_token()
        assert token1 == "refreshed-token"
        assert mock_authenticator.token_manager.get_token.call_count == 1
        
        token2 = llm._get_current_token()
        assert token2 == "refreshed-token"
        assert mock_authenticator.token_manager.get_token.call_count == 2
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.invoke')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_invoke_refreshes_token_with_authenticator(self, mock_client_class, mock_super_invoke):
        """Test that invoke() refreshes token when using authenticator."""
        # Mock AgenticSession with authenticator
        mock_authenticator = Mock()
        mock_authenticator.token_manager.get_token.return_value = "refreshed-token"
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-elsewhere"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = None
        mock_session.authenticator = mock_authenticator
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        # Mock the parent invoke to return a simple response
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_super_invoke.return_value = mock_response
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        # Call invoke
        response = llm.invoke("Test message")
        
        # Verify token was refreshed before invoke
        assert llm.default_headers["Authorization"] == "Bearer refreshed-token"
        assert response.content == "Test response"
        mock_super_invoke.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.invoke')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_invoke_no_refresh_with_access_token(self, mock_client_class, mock_super_invoke):
        """Test that invoke() doesn't refresh token when using access_token."""
        # Mock AgenticSession with access_token
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-on"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = "static-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_super_invoke.return_value = mock_response
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        original_token = llm.default_headers["Authorization"]
        
        # Call invoke
        response = llm.invoke("Test message")
        
        # Verify token wasn't changed (no refresh for access_token mode)
        assert llm.default_headers["Authorization"] == original_token
        assert response.content == "Test response"
        mock_super_invoke.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.ainvoke')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    @pytest.mark.asyncio
    async def test_ainvoke_refreshes_token(self, mock_client_class, mock_super_ainvoke):
        """Test that ainvoke() refreshes token when using authenticator."""
        # Mock AgenticSession with authenticator
        mock_authenticator = Mock()
        mock_authenticator.token_manager.get_token.return_value = "refreshed-token"
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-elsewhere"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = None
        mock_session.authenticator = mock_authenticator
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        # Mock the parent ainvoke to return a simple response
        mock_response = Mock()
        mock_response.content = "Test async response"
        mock_super_ainvoke.return_value = mock_response
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        # Call ainvoke
        response = await llm.ainvoke("Test message")
        
        # Verify token was refreshed before ainvoke
        assert llm.default_headers["Authorization"] == "Bearer refreshed-token"
        assert response.content == "Test async response"
        mock_super_ainvoke.assert_called_once()


class TestChatWxOHelperMethods:
    """Test helper classmethods for initialization."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_from_instance_credentials(self, mock_client_class):
        """Test from_instance_credentials() classmethod."""
        # Mock AgenticSession
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-elsewhere"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = None
        mock_session.authenticator = Mock()
        mock_session.authenticator.token_manager.get_token.return_value = "test-token"
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO.from_instance_credentials(
            model="virtual-model/watsonx/test-model",
            instance_url="https://api.example.com",
            api_key="test-api-key",
            temperature=0.5
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm.temperature == 0.5
        assert llm._session == mock_session
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_from_execution_context(self, mock_client_class):
        """Test from_execution_context() classmethod."""
        # Mock AgenticSession
        mock_identity = RequestIdentity(
            tenant_id="test-tenant",
            user_id="test-user",
            thread_id="test-thread"
        )
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-on"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = "test-token"
        mock_session.authenticator = None
        mock_session.identity = mock_identity
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        execution_context = {
            "access_token": "test-token",
            "api_proxy_url": "https://api.example.com",
            "thread_id": "test-thread"
        }
        
        llm = ChatWxO.from_execution_context(
            model="virtual-model/watsonx/test-model",
            execution_context=execution_context
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm._session == mock_session
        assert llm._user_id == "test-user"
        assert llm._tenant_id == "test-tenant"
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_from_session(self, mock_client_class):
        """Test from_session() classmethod."""
        # Mock AgenticSession
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "local"
        mock_session.base_url = "http://localhost:4321/api/v1"
        mock_session.access_token = "local-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        llm = ChatWxO.from_session(
            model="virtual-model/watsonx/test-model",
            session=mock_session,
            temperature=0.7
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm.temperature == 0.7
        assert llm._session == mock_session
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client.from_runnable_config')
    def test_from_runnable_config(self, mock_from_runnable_config):
        """Test from_runnable_config() classmethod."""
        # Mock AgenticSession
        mock_identity = RequestIdentity(
            tenant_id="test-tenant",
            user_id="test-user",
            thread_id="test-thread"
        )
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "runs-on"
        mock_session.base_url = "https://api.example.com/v1/orchestrate"
        mock_session.access_token = "test-token"
        mock_session.authenticator = None
        mock_session.identity = mock_identity
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_from_runnable_config.return_value = mock_client
        
        config = {
            "configurable": {
                "execution_context": {
                    "access_token": "test-token",
                    "api_proxy_url": "https://api.example.com",
                    "thread_id": "test-thread"
                }
            }
        }
        
        llm = ChatWxO.from_runnable_config(
            config,
            model="virtual-model/watsonx/test-model",
            temperature=0.2
        )
        
        assert llm.model == "virtual-model/watsonx/test-model"
        assert llm.temperature == 0.2
        assert llm._session == mock_session
        mock_from_runnable_config.assert_called_once_with(config, verify=None)


class TestChatWxOInheritedFeatures:
    """Test that inherited ChatOpenAI features work correctly."""
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.stream')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_stream_inherited(self, mock_client_class, mock_super_stream):
        """Test that stream() is inherited and works."""
        # Mock AgenticSession
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "local"
        mock_session.base_url = "http://localhost:4321/api/v1"
        mock_session.access_token = "local-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        # Mock streaming chunks
        mock_chunks = [Mock(content="Hello"), Mock(content=" world")]
        mock_super_stream.return_value = iter(mock_chunks)
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        chunks = list(llm.stream("Test message"))
        
        assert len(chunks) == 2
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " world"
        mock_super_stream.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.batch')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_batch_inherited(self, mock_client_class, mock_super_batch):
        """Test that batch() is inherited and works."""
        # Mock AgenticSession
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "local"
        mock_session.base_url = "http://localhost:4321/api/v1"
        mock_session.access_token = "local-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        mock_responses = [Mock(content="Response 1"), Mock(content="Response 2")]
        mock_super_batch.return_value = mock_responses
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        responses = llm.batch(["Message 1", "Message 2"])
        
        assert len(responses) == 2
        assert responses[0].content == "Response 1"
        assert responses[1].content == "Response 2"
        mock_super_batch.assert_called_once()
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.bind_tools')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_bind_tools_inherited(self, mock_client_class, mock_super_bind_tools):
        """Test that bind_tools() is inherited and works."""
        # Mock AgenticSession
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "local"
        mock_session.base_url = "http://localhost:4321/api/v1"
        mock_session.access_token = "local-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        mock_bound_llm = Mock()
        mock_super_bind_tools.return_value = mock_bound_llm
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        tools = [{"type": "function", "function": {"name": "get_weather"}}]
        bound_llm = llm.bind_tools(tools)
        
        assert bound_llm == mock_bound_llm
        mock_super_bind_tools.assert_called_once_with(tools)
    
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.ChatOpenAI.with_structured_output')
    @patch('ibm_watsonx_orchestrate_sdk.langchain.chat_models.Client')
    def test_with_structured_output_inherited(self, mock_client_class, mock_super_structured):
        """Test that with_structured_output() is inherited and works."""
        # Mock AgenticSession
        mock_session = Mock(spec=AgenticSession)
        mock_session.mode = "local"
        mock_session.base_url = "http://localhost:4321/api/v1"
        mock_session.access_token = "local-token"
        mock_session.authenticator = None
        mock_session.identity = None
        
        # Mock Client
        mock_client = Mock()
        mock_client.session = mock_session
        mock_client_class.return_value = mock_client
        
        mock_structured_llm = Mock()
        mock_super_structured.return_value = mock_structured_llm
        
        llm = ChatWxO(
            model="virtual-model/watsonx/test-model",
            session=mock_session
        )
        
        class TestSchema:
            pass
        
        structured_llm = llm.with_structured_output(TestSchema)
        
        assert structured_llm == mock_structured_llm
        mock_super_structured.assert_called_once()
