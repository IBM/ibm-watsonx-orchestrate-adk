"""
Controller and CLI routing tests for Vertex AI agent discovery.

All external I/O (HTTP, connections client, typer confirm) is mocked.
Pattern mirrors tests/cli/commands/agents/test_a2a_discovery.py.
"""
import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from ibm_watsonx_orchestrate.agent_builder.agents.vertex_discovery import VertexDiscoveryService
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_CREDS = {
    "service_account_json": json.dumps({
        "type": "service_account",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nFAKE\n-----END RSA PRIVATE KEY-----",  # pragma: allowlist secret
        "client_email": "svc@proj.iam.gserviceaccount.com",
        "project_id": "my-gcp-project",
    }),
    "project_id": "my-gcp-project",
    "location": "us-central1",
}

WXO_SPEC_1 = {
    "spec_version": "v1",
    "kind": "external",
    "name": "customer_support",
    "title": "Customer Support",
    "description": "Handles customer queries",
    "provider": "vertex_agent",
    "api_url": "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/p/locations/l/agents/a",
    "auth_scheme": "NONE",
    "auth_config": {},
}


def _mock_connections_client(creds=None):
    """Return a mock connections client that returns ``creds`` from get_credentials()."""
    mock_client = MagicMock()
    mock_client.get_credentials.return_value = creds or FAKE_CREDS
    return mock_client


# ---------------------------------------------------------------------------
# D. Unit tests for convert_to_wxo_external_agent_dict
# ---------------------------------------------------------------------------

class TestConvertToWxoExternalAgentDict:

    def test_empty_display_name_falls_back_to_resource_path(self):
        """displayName='' produces name='vertex_agent_<last-segment>'."""
        agent = {
            "name": "projects/p/locations/l/agents/abc123",
            "displayName": "",
        }
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(agent, "us-central1")
        assert result["name"] == "vertex_agent_abc123"

    def test_all_hyphen_display_name_falls_back_to_resource_path(self):
        """displayName='---' → sanitized='___' → falls back to resource path."""
        agent = {
            "name": "projects/p/locations/l/agents/xyz789",
            "displayName": "---",
        }
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(agent, "us-central1")
        assert result["name"] == "vertex_agent_xyz789"

    def test_valid_display_name_is_unchanged(self):
        """A normal displayName is snake-cased and NOT replaced by the fallback."""
        agent = {
            "name": "projects/p/locations/l/agents/a",
            "displayName": "Customer Support",
        }
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(agent, "us-central1")
        assert result["name"] == "customer_support"


# ---------------------------------------------------------------------------
# E. Controller tests
# ---------------------------------------------------------------------------

class TestDiscoverAndRegisterVertexAgents:

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.vertex_discovery.VertexDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_vertex_agents_happy_path(
        self, mock_local_dev, mock_list_agents, mock_publish, mock_get_conn
    ):
        """list_agents called, publish_or_update_agents called with converted agents."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = [
            {
                "name": "projects/p/locations/l/agents/a",
                "displayName": "Customer Support",
                "description": "Handles customer queries",
            }
        ]

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ), patch("typer.confirm", return_value=True):
            controller = AgentsController()
            controller.discover_and_register_vertex_agents(
                app_id="vertex-conn",
                agents=None,
            )

        mock_list_agents.assert_called_once()
        mock_publish.assert_called_once()
        published = mock_publish.call_args[0][0]
        assert len(published) == 1
        assert published[0].name == "customer_support"

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=True)
    def test_discover_cpd_env_blocked_local_dev(self, mock_local_dev):
        """sys.exit(1) when is_local_dev() is True."""
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_vertex_agents(
                    app_id="vertex-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_cpd_env_blocked_cpd(self, mock_local_dev):
        """sys.exit(1) when is_cpd_env() is True."""
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=True,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_vertex_agents(
                    app_id="vertex-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_missing_app_id_exits(self, mock_local_dev):
        """sys.exit(1) when app_id is None or empty."""
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_vertex_agents(
                    app_id=None, agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_missing_project_id_exits(self, mock_local_dev, mock_get_conn):
        """sys.exit(1) when project_id is missing from credentials."""
        creds_no_project = {k: v for k, v in FAKE_CREDS.items() if k != "project_id"}
        mock_get_conn.return_value = _mock_connections_client(creds_no_project)

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_vertex_agents(
                    app_id="vertex-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_missing_location_exits(self, mock_local_dev, mock_get_conn):
        """sys.exit(1) when location is missing from credentials."""
        creds_no_location = {k: v for k, v in FAKE_CREDS.items() if k != "location"}
        mock_get_conn.return_value = _mock_connections_client(creds_no_location)

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_vertex_agents(
                    app_id="vertex-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.vertex_discovery.VertexDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_confirm_called(
        self, mock_local_dev, mock_list_agents, mock_publish, mock_get_conn
    ):
        """typer.confirm is called and gates the import."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = [
            {
                "name": "projects/p/locations/l/agents/a",
                "displayName": "Customer Support",
                "description": "Handles customer queries",
            }
        ]

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ), patch("typer.confirm", return_value=False) as mock_confirm:
            controller = AgentsController()
            controller.discover_and_register_vertex_agents(
                app_id="vertex-conn", agents=None
            )

        mock_confirm.assert_called_once()
        mock_publish.assert_not_called()

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.vertex_discovery.VertexDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_no_agents_found_skips_publish(
        self, mock_local_dev, mock_list_agents, mock_publish, mock_get_conn
    ):
        """When no agents are discovered, publish_or_update_agents is never called."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = []

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            controller.discover_and_register_vertex_agents(
                app_id="vertex-conn", agents=None
            )

        mock_publish.assert_not_called()

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.vertex_discovery.VertexDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_resolves_connection_creds(
        self, mock_local_dev, mock_list_agents, mock_get_conn
    ):
        """Correct project_id and location are extracted from credentials and passed to the service."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = []

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            controller.discover_and_register_vertex_agents(
                app_id="vertex-conn", agents=None
            )

        call_kwargs = mock_list_agents.call_args
        assert call_kwargs[0][0] == "my-gcp-project"   # project_id
        assert call_kwargs[0][1] == "us-central1"       # location


# ---------------------------------------------------------------------------
# F. CLI command routing
# ---------------------------------------------------------------------------

class TestAgentDiscoverCommandRouting:
    """
    Test that the typer command routes correctly between A2A and Vertex paths.
    Uses the CliRunner / direct controller mock pattern.
    """

    @patch.object(AgentsController, "discover_and_register_vertex_agents")
    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_vertex_agent_provider_routes_to_controller(
        self, mock_init, mock_vertex
    ):
        """--provider vertex_agent routes to discover_and_register_vertex_agents."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        runner.invoke(
            agents_app,
            ["discover", "--provider", "vertex_agent", "--app-id", "vertex-conn"],
        )
        mock_vertex.assert_called_once_with(
            app_id="vertex-conn",
            agents=None,
        )

    @patch.object(AgentsController, "discover_and_import_agent")
    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_a2a_still_works(self, mock_init, mock_a2a):
        """Existing A2A -u path is unchanged when --provider is absent."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        runner.invoke(
            agents_app,
            ["discover", "--url", "https://example.com"],
        )
        mock_a2a.assert_called_once_with(
            base_url="https://example.com",
            endpoint=".well-known/agent-card.json",
            agent_name=None,
            app_id=None,
        )

    @patch.object(AgentsController, "discover_and_register_vertex_agents")
    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_name_flag_passed_through(self, mock_init, mock_vertex):
        """--name foo --name bar passes agents=['foo','bar'] to controller."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        runner.invoke(
            agents_app,
            [
                "discover",
                "--provider", "vertex_agent",
                "--app-id", "vertex-conn",
                "--name", "foo",
                "--name", "bar",
            ],
        )
        call_kwargs = mock_vertex.call_args[1]
        assert call_kwargs["agents"] == ["foo", "bar"]

    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_unknown_provider_exits_with_error(self, mock_init):
        """An unrecognised --provider value exits with code 1 and a helpful message."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        result = runner.invoke(
            agents_app,
            ["discover", "--provider", "salesforce"],
        )
        assert result.exit_code == 1
        assert "unknown --provider" in result.output
