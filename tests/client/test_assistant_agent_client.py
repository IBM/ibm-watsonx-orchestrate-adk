import pytest
from unittest.mock import Mock, patch, MagicMock
from ibm_watsonx_orchestrate_clients.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException


@pytest.fixture
def client():
    """
    Creates an AssistantAgentClient with mocked HTTP methods.

    Why: Every test needs a client instance. By mocking _get, _post, _patch,
    and _delete we avoid real HTTP calls and control what the server would return.
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

class TestCreate:

    def test_create_calls_post_with_correct_endpoint(self, client):
        """
        Verifies that create() sends a POST to /assistants/watsonx.

        Why: The endpoint path is the contract with the server. If it changes
        accidentally, all agent creation will silently break.
        """
        client._post.return_value = {"id": "agent-1", "name": "my-agent"}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ):
            result = client.create({"name": "my-agent"})

        client._post.assert_called_once()
        endpoint = client._post.call_args[0][0]
        assert endpoint == "/assistants/watsonx"

    def test_create_returns_server_response(self, client):
        """
        Verifies that create() returns exactly what the server responds with.

        Why: Callers depend on the returned dict to get the new agent's ID and
        properties. Any transformation would break downstream code.
        """
        expected = {"id": "agent-42", "name": "my-agent"}
        client._post.return_value = expected

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ):
            result = client.create({"name": "my-agent"})

        assert result == expected

    def test_create_calls_resolve_and_inject_workspace(self, client):
        """
        Verifies that create() passes the payload through resolve_and_inject_workspace.

        Why: Workspace injection ensures the new agent is created in the correct
        workspace. Skipping it would create agents in the wrong scope.
        """
        client._post.return_value = {}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ) as mock_resolve:
            client.create({"name": "my-agent"})

        mock_resolve.assert_called_once_with({"name": "my-agent"})


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------

class TestDelete:

    def test_delete_calls_correct_endpoint(self, client):
        """
        Verifies that delete() sends a DELETE to /assistants/watsonx/{agent_id}.

        Why: Deleting the wrong endpoint would either do nothing or delete the
        wrong resource. The agent ID must be embedded in the URL.
        """
        client._delete.return_value = {}

        client.delete("agent-99")

        client._delete.assert_called_once_with("/assistants/watsonx/agent-99")

    def test_delete_returns_server_response(self, client):
        """
        Verifies that delete() passes back whatever the server returns.

        Why: Some callers inspect the delete response (e.g. to confirm deletion).
        """
        client._delete.return_value = {"status": "deleted"}

        result = client.delete("agent-99")

        assert result == {"status": "deleted"}


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------

class TestUpdate:

    def test_update_calls_patch_with_correct_endpoint(self, client):
        """
        Verifies that update() sends a PATCH to /assistants/watsonx/{agent_id}.

        Why: The agent ID must be in the URL so the server knows which agent to update.
        """
        client._patch.return_value = {"id": "agent-1"}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ):
            client.update("agent-1", {"name": "updated"})

        endpoint = client._patch.call_args[0][0]
        assert endpoint == "/assistants/watsonx/agent-1"

    def test_update_skips_workspace_injection_when_flag_set(self, client):
        """
        Verifies that update() skips resolve_and_inject_workspace when
        skip_workspace_injection=True.

        Why: Cross-workspace update operations must not overwrite the workspace_id
        that is already set in the payload. The flag exists exactly for this case.
        """
        client._patch.return_value = {}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
        ) as mock_resolve:
            client.update("agent-1", {"name": "updated"}, skip_workspace_injection=True)

        mock_resolve.assert_not_called()

    def test_update_injects_workspace_by_default(self, client):
        """
        Verifies that update() calls resolve_and_inject_workspace by default
        (skip_workspace_injection=False).

        Why: Without workspace injection the agent could be moved to the wrong
        workspace on update.
        """
        client._patch.return_value = {}

        with patch(
            "ibm_watsonx_orchestrate_clients.agents.assistant_agent_client.resolve_and_inject_workspace",
            side_effect=lambda p: p,
        ) as mock_resolve:
            client.update("agent-1", {"name": "updated"})

        mock_resolve.assert_called_once()


# ---------------------------------------------------------------------------
# get_draft_by_id()
# ---------------------------------------------------------------------------

class TestGetDraftById:

    def test_returns_empty_string_when_agent_id_is_none(self, client):
        """
        Verifies that get_draft_by_id() returns "" when agent_id is None.

        Why: Callers use the empty-string sentinel to detect "agent not found"
        without raising an exception. None is a valid caller mistake that must
        be handled gracefully.
        """
        result = client.get_draft_by_id(None)

        assert result == ""
        client._get.assert_not_called()

    def test_returns_agent_on_success(self, client):
        """
        Verifies that get_draft_by_id() returns the agent dict on a successful GET.

        Why: This is the happy path — callers expect to receive the full agent
        object when it exists.
        """
        client._get.return_value = {"id": "agent-5", "name": "test"}

        result = client.get_draft_by_id("agent-5")

        assert result == {"id": "agent-5", "name": "test"}

    def test_returns_empty_string_on_404_assistant_not_found(self, client):
        """
        Verifies that get_draft_by_id() returns "" when the server responds with
        404 and the message "Assistant not found".

        Why: A 404 for a missing agent is expected in many workflows (e.g. checking
        whether an agent exists before creating it). Raising an exception here would
        force callers to catch it everywhere.
        """
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Assistant not found"
        client._get.side_effect = ClientAPIException(response=mock_response)

        result = client.get_draft_by_id("nonexistent-agent")

        assert result == ""

    def test_reraises_non_404_exception(self, client):
        """
        Verifies that get_draft_by_id() re-raises ClientAPIException for errors
        other than 404 "Assistant not found".

        Why: Only the "not found" case is handled silently. All other errors
        (500, 403, etc.) are real problems that callers must see.
        """
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        client._get.side_effect = ClientAPIException(response=mock_response)

        with pytest.raises(ClientAPIException):
            client.get_draft_by_id("agent-5")

    def test_uses_workspace_id_param_when_provided_without_global(self, client):
        """
        Verifies that get_draft_by_id() adds workspace_id to the query string
        when workspace_id is provided and include_global=False.

        Why: Scoping a GET to a specific workspace ensures callers get back only
        agents in that workspace and not agents from other workspaces.
        """
        client._get.return_value = {"id": "agent-5"}

        client.get_draft_by_id("agent-5", workspace_id="ws-123", include_global=False)

        call_url = client._get.call_args[0][0]
        assert "workspace_id=ws-123" in call_url

    def test_omits_workspace_param_when_include_global_is_true(self, client):
        """
        Verifies that get_draft_by_id() uses the plain endpoint (no workspace_id
        query param) when include_global=True, regardless of workspace_id.

        Why: When global inclusion is requested, the server returns all agents
        across workspaces — scoping by workspace_id would contradict that.
        """
        client._get.return_value = {"id": "agent-5"}

        client.get_draft_by_id("agent-5", workspace_id="ws-123", include_global=True)

        call_url = client._get.call_args[0][0]
        assert "workspace_id" not in call_url
