"""
Controller and CLI routing tests for Azure AI Foundry agent discovery.

All external I/O (HTTP, connections client, typer confirm) is mocked.
"""
from unittest.mock import MagicMock, patch

import pytest

from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_CREDS = {
    "tenant_id": "00000000-0000-0000-0000-000000000000",
    "client_id": "11111111-1111-1111-1111-111111111111",
    "client_secret": "my-secret-key",  # pragma: allowlist secret
    "endpoint": "https://my-resource.services.ai.azure.com",
    "project_name": "my-project",
}


def _mock_connections_client(creds=None):
    """Return a mock connections client that returns ``creds`` from get_credentials()."""
    mock_client = MagicMock()
    mock_client.get_credentials.return_value = creds or FAKE_CREDS
    return mock_client


# ---------------------------------------------------------------------------
# Controller tests
# ---------------------------------------------------------------------------

class TestDiscoverAndRegisterAzureAIFoundryAgents:

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.azure_ai_foundry_discovery.AzureAIFoundryDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_azure_agents_happy_path(
        self, mock_local_dev, mock_list_agents, mock_publish, mock_get_conn
    ):
        """list_agents called, publish_or_update_agents called with converted agents."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = [
            {
                "id": "agent-abc",
                "name": "Customer Support",
                "description": "Handles customer queries",
            }
        ]

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ), patch("typer.confirm", return_value=True):
            controller = AgentsController()
            controller.discover_and_register_azure_ai_foundry_agents(
                app_id="azure-conn",
                agents=None,
            )

        mock_list_agents.assert_called_once()
        mock_publish.assert_called_once()
        published = mock_publish.call_args[0][0]
        assert len(published) == 1
        assert published[0].name == "customer_support"
        assert published[0].provider.value == "azure_ai_foundry"

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=True)
    def test_discover_cpd_env_blocked_local_dev(self, mock_local_dev):
        """sys.exit(1) when is_local_dev() is True."""
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_azure_ai_foundry_agents(
                    app_id="azure-conn", agents=None
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
                controller.discover_and_register_azure_ai_foundry_agents(
                    app_id="azure-conn", agents=None
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
                controller.discover_and_register_azure_ai_foundry_agents(
                    app_id=None, agents=None
                )

    @pytest.mark.parametrize("missing_field", ["tenant_id", "client_id", "client_secret", "endpoint", "project_name"])
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_missing_credential_field_exits(self, mock_local_dev, mock_get_conn, missing_field):
        """sys.exit(1) when any required credential field is missing."""
        creds = {k: v for k, v in FAKE_CREDS.items() if k != missing_field}
        mock_get_conn.return_value = _mock_connections_client(creds)

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_azure_ai_foundry_agents(
                    app_id="azure-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.azure_ai_foundry_discovery.AzureAIFoundryDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_confirm_called(
        self, mock_local_dev, mock_list_agents, mock_publish, mock_get_conn
    ):
        """typer.confirm is called and gates the import."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = [
            {
                "id": "agent-abc",
                "name": "Customer Support",
                "description": "Handles customer queries",
            }
        ]

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ), patch("typer.confirm", return_value=False) as mock_confirm:
            controller = AgentsController()
            controller.discover_and_register_azure_ai_foundry_agents(
                app_id="azure-conn", agents=None
            )

        mock_confirm.assert_called_once()
        mock_publish.assert_not_called()

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.azure_ai_foundry_discovery.AzureAIFoundryDiscoveryService.list_agents")
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
            controller.discover_and_register_azure_ai_foundry_agents(
                app_id="azure-conn", agents=None
            )

        mock_publish.assert_not_called()


# ---------------------------------------------------------------------------
# CLI command routing tests
# ---------------------------------------------------------------------------

class TestAgentDiscoverCommandRouting:
    @patch.object(AgentsController, "discover_and_register_azure_ai_foundry_agents")
    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_azure_ai_foundry_provider_routes_to_controller(
        self, mock_init, mock_azure
    ):
        """--provider azure_ai_foundry routes to discover_and_register_azure_ai_foundry_agents."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        runner.invoke(
            agents_app,
            ["discover", "--provider", "azure_ai_foundry", "--app-id", "azure-conn"],
        )
        mock_azure.assert_called_once_with(
            app_id="azure-conn",
            agents=None,
        )

    @patch.object(AgentsController, "discover_and_register_azure_ai_foundry_agents")
    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_azure_name_flag_passed_through(self, mock_init, mock_azure):
        """--name foo --name bar passes agents=['foo','bar'] to controller."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        runner.invoke(
            agents_app,
            [
                "discover",
                "--provider", "azure_ai_foundry",
                "--app-id", "azure-conn",
                "--name", "foo",
                "--name", "bar",
            ],
        )
        call_kwargs = mock_azure.call_args[1]
        assert call_kwargs["agents"] == ["foo", "bar"]
