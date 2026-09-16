import pytest
from unittest.mock import Mock, patch
from ibm_watsonx_orchestrate_clients.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException


@pytest.fixture
def mock_assistant_agent_client() -> AssistantAgentClient:
    """
    Creates an AssistantAgentClient with mocked HTTP methods.
    """
    c = AssistantAgentClient(base_url="https://test.example.com")
    c._get = Mock()
    c._post = Mock()
    c._patch = Mock()
    c._delete = Mock()
    return c


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------

class TestCreateAssistantAgent:

    def test_create_calls_post_with_correct_endpoint(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that create() sends a POST to /assistants/watsonx with the correct payload.
        """
        mock_assistant_agent_client._post.return_value = {"id": "agent-1", "name": "my-agent"}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ):
            result = mock_assistant_agent_client.create({"name": "my-agent"})

        mock_assistant_agent_client._post.assert_called_once_with("/assistants/watsonx", data={"name": "my-agent"})

    def test_create_returns_server_response(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that create() returns exactly what the server responds with.
        """
        expected = {"id": "agent-42", "name": "my-agent"}
        mock_assistant_agent_client._post.return_value = expected

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ):
            result = mock_assistant_agent_client.create({"name": "my-agent"})

        assert result == expected

    def test_create_calls_resolve_and_inject_workspace(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that create() passes the payload through resolve_and_inject_workspace.
        """
        mock_assistant_agent_client._post.return_value = {}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ) as mock_resolve:
            mock_assistant_agent_client.create({"name": "my-agent"})

        mock_resolve.assert_called_once_with({"name": "my-agent"})


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------

class TestDelete:

    def test_delete_calls_correct_endpoint(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that delete() sends a DELETE to /assistants/watsonx/{agent_id}.
        """
        mock_assistant_agent_client._delete.return_value = {}

        mock_assistant_agent_client.delete("agent-99")

        mock_assistant_agent_client._delete.assert_called_once_with("/assistants/watsonx/agent-99")

    def test_delete_returns_server_response(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that delete() passes back whatever the server returns.
        """
        mock_assistant_agent_client._delete.return_value = {"status": "deleted"}

        result = mock_assistant_agent_client.delete("agent-99")

        assert result == {"status": "deleted"}


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------

class TestUpdate:

    def test_update_calls_patch_with_correct_endpoint(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that update() sends a PATCH to /assistants/watsonx/{agent_id} with the correct payload.
        """
        mock_assistant_agent_client._patch.return_value = {"id": "agent-1"}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ):
            mock_assistant_agent_client.update("agent-1", {"name": "updated"})

        mock_assistant_agent_client._patch.assert_called_once_with("/assistants/watsonx/agent-1", data={"name": "updated"})

    def test_update_skips_workspace_injection_when_flag_set(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that update() skips resolve_and_inject_workspace when
        skip_workspace_injection=True.
        """
        mock_assistant_agent_client._patch.return_value = {}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
        ) as mock_resolve:
            mock_assistant_agent_client.update("agent-1", {"name": "updated"}, skip_workspace_injection=True)

        mock_resolve.assert_not_called()

    def test_update_injects_workspace_by_default(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that update() calls resolve_and_inject_workspace by default
        (skip_workspace_injection=False).
        """
        mock_assistant_agent_client._patch.return_value = {}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ) as mock_resolve:
            mock_assistant_agent_client.update("agent-1", {"name": "updated"})

        mock_resolve.assert_called_once()


# ---------------------------------------------------------------------------
# get_draft_by_id()
# ---------------------------------------------------------------------------

class TestGetDraftById:

    def test_returns_empty_string_when_agent_id_is_none(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that get_draft_by_id() returns "" when agent_id is None.
        """
        result = mock_assistant_agent_client.get_draft_by_id(None)

        assert result == ""
        mock_assistant_agent_client._get.assert_not_called()

    def test_returns_agent_on_success(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that get_draft_by_id() returns the agent dict on a successful GET.
        """
        mock_assistant_agent_client._get.return_value = {"id": "agent-5", "name": "test"}

        result = mock_assistant_agent_client.get_draft_by_id("agent-5")

        assert result == {"id": "agent-5", "name": "test"}

    def test_returns_empty_string_on_404_assistant_not_found(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that get_draft_by_id() returns "" when the server responds with
        404 and the message "Assistant not found".
        """
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Assistant not found"
        mock_assistant_agent_client._get.side_effect = ClientAPIException(response=mock_response)

        result = mock_assistant_agent_client.get_draft_by_id("nonexistent-agent")

        assert result == ""

    def test_reraises_404_when_message_is_not_assistant_not_found(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that get_draft_by_id() re-raises a 404 ClientAPIException when
        the response body does NOT contain "Assistant not found".
        """
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_assistant_agent_client._get.side_effect = ClientAPIException(response=mock_response)

        with pytest.raises(ClientAPIException):
            mock_assistant_agent_client.get_draft_by_id("agent-5")

    def test_reraises_non_404_exception(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that get_draft_by_id() re-raises ClientAPIException for errors
        other than 404 "Assistant not found".
        """
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_assistant_agent_client._get.side_effect = ClientAPIException(response=mock_response)

        with pytest.raises(ClientAPIException):
            mock_assistant_agent_client.get_draft_by_id("agent-5")

    def test_uses_workspace_id_param_when_provided_without_global(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that get_draft_by_id() adds workspace_id to the query string
        when workspace_id is provided and include_global=False.
        """
        mock_assistant_agent_client._get.return_value = {"id": "agent-5"}

        mock_assistant_agent_client.get_draft_by_id("agent-5", workspace_id="ws-123", include_global=False)

        call_url = mock_assistant_agent_client._get.call_args[0][0]
        assert "workspace_id=ws-123" in call_url

    def test_omits_workspace_param_when_include_global_is_true(self, mock_assistant_agent_client: AssistantAgentClient) -> None:
        """
        Verifies that get_draft_by_id() uses the plain endpoint (no workspace_id
        query param) when include_global=True, regardless of workspace_id.
        """
        mock_assistant_agent_client._get.return_value = {"id": "agent-5"}

        mock_assistant_agent_client.get_draft_by_id("agent-5", workspace_id="ws-123", include_global=True)

        call_url = mock_assistant_agent_client._get.call_args[0][0]
        assert "workspace_id" not in call_url
