"""
Controller and CLI routing tests for AWS Bedrock agent discovery.

All external I/O (HTTP, connections client, typer confirm) is mocked.
Pattern mirrors tests/cli/commands/agents/test_vertex_discovery.py.
"""
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery import BedrockDiscoveryService
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_CREDS = {
    "access_key_id": "AKIAIOSFODNN7EXAMPLE",  # pragma: allowlist secret
    "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # pragma: allowlist secret
    "region": "us-east-1",
}

WXO_SPEC_1 = {
    "spec_version": "v1",
    "kind": "external",
    "name": "customer_support",
    "title": "Customer Support",
    "description": "Handles customer queries",
    "provider": "bedrock_agent",
    "api_url": "https://bedrock-agent-runtime.us-east-1.amazonaws.com/agents/ABCDEF1234/agentAliases/TSTALIASID/",
    "auth_scheme": "NONE",
    "auth_config": {},
}


def _mock_connections_client(creds=None):
    """Return a mock connections client that returns ``creds`` from get_credentials()."""
    mock_client = MagicMock()
    mock_client.get_credentials.return_value = creds or FAKE_CREDS
    return mock_client


# ---------------------------------------------------------------------------
# E. Controller tests
# ---------------------------------------------------------------------------

class TestDiscoverAndRegisterBedrockAgents:

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_bedrock_agents_happy_path(
        self, mock_local_dev, mock_list_agents, mock_publish, mock_get_conn
    ):
        """list_agents called, publish_or_update_agents called with converted agents."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = [
            {
                "agentId": "ABCDEF1234",
                "agentName": "Customer Support",
                "description": "Handles customer queries",
            }
        ]

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ), patch("typer.confirm", return_value=True):
            controller = AgentsController()
            controller.discover_and_register_bedrock_agents(
                app_id="bedrock-conn",
                agents=None,
            )

        mock_list_agents.assert_called_once()
        mock_publish.assert_called_once()
        published = mock_publish.call_args[0][0]
        assert len(published) == 1
        assert published[0].name == "customer_support"

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=True)
    def test_discover_blocked_local_dev(self, mock_local_dev):
        """sys.exit(1) when is_local_dev() is True."""
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_bedrock_agents(
                    app_id="bedrock-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_blocked_cpd_env(self, mock_local_dev):
        """sys.exit(1) when is_cpd_env() is True."""
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=True,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_bedrock_agents(
                    app_id="bedrock-conn", agents=None
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
                controller.discover_and_register_bedrock_agents(
                    app_id=None, agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_missing_access_key_id_exits(self, mock_local_dev, mock_get_conn):
        """sys.exit(1) when access_key_id is missing from credentials."""
        creds_missing = {k: v for k, v in FAKE_CREDS.items() if k != "access_key_id"}
        mock_get_conn.return_value = _mock_connections_client(creds_missing)

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_bedrock_agents(
                    app_id="bedrock-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_missing_secret_access_key_exits(self, mock_local_dev, mock_get_conn):
        """sys.exit(1) when secret_access_key is missing from credentials."""
        creds_missing = {k: v for k, v in FAKE_CREDS.items() if k != "secret_access_key"}
        mock_get_conn.return_value = _mock_connections_client(creds_missing)

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_bedrock_agents(
                    app_id="bedrock-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_missing_region_exits(self, mock_local_dev, mock_get_conn):
        """sys.exit(1) when region is missing from credentials."""
        creds_missing = {k: v for k, v in FAKE_CREDS.items() if k != "region"}
        mock_get_conn.return_value = _mock_connections_client(creds_missing)

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            with pytest.raises(SystemExit):
                controller.discover_and_register_bedrock_agents(
                    app_id="bedrock-conn", agents=None
                )

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_confirm_gates_import(
        self, mock_local_dev, mock_list_agents, mock_publish, mock_get_conn
    ):
        """typer.confirm is called and gates the import (False → no publish)."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = [
            {
                "agentId": "ABCDEF1234",
                "agentName": "Customer Support",
                "description": "Handles customer queries",
            }
        ]

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ), patch("typer.confirm", return_value=False) as mock_confirm:
            controller = AgentsController()
            controller.discover_and_register_bedrock_agents(
                app_id="bedrock-conn", agents=None
            )

        mock_confirm.assert_called_once()
        mock_publish.assert_not_called()

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService.list_agents")
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
            controller.discover_and_register_bedrock_agents(
                app_id="bedrock-conn", agents=None
            )

        mock_publish.assert_not_called()

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_yes_flag_skips_confirm(
        self, mock_local_dev, mock_list_agents, mock_publish, mock_get_conn
    ):
        """yes=True bypasses typer.confirm and proceeds directly to publish."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = [
            {
                "agentId": "ABCDEF1234",
                "agentName": "Customer Support",
                "description": "Handles customer queries",
            }
        ]

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ), patch("typer.confirm") as mock_confirm:
            controller = AgentsController()
            controller.discover_and_register_bedrock_agents(
                app_id="bedrock-conn", agents=None, yes=True
            )

        mock_confirm.assert_not_called()
        mock_publish.assert_called_once()

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService.list_agents")
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False)
    def test_discover_credential_fields_passed_correctly(
        self, mock_local_dev, mock_list_agents, mock_get_conn
    ):
        """Correct region and credentials are extracted from connection and passed to the service."""
        mock_get_conn.return_value = _mock_connections_client()
        mock_list_agents.return_value = []

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_cpd_env",
            return_value=False,
        ):
            controller = AgentsController()
            controller.discover_and_register_bedrock_agents(
                app_id="bedrock-conn", agents=None
            )

        call_kwargs = mock_list_agents.call_args[1]
        assert call_kwargs["region"] == "us-east-1"
        assert call_kwargs["access_key_id"] == FAKE_CREDS["access_key_id"]
        assert call_kwargs["secret_access_key"] == FAKE_CREDS["secret_access_key"]
        assert call_kwargs["session_token"] is None


# ---------------------------------------------------------------------------
# F. CLI command routing
# ---------------------------------------------------------------------------

class TestAgentDiscoverCommandRouting:

    @patch.object(AgentsController, "discover_and_register_bedrock_agents")
    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_bedrock_agent_provider_routes_to_controller(
        self, mock_init, mock_bedrock
    ):
        """--provider bedrock_agent routes to discover_and_register_bedrock_agents."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        runner.invoke(
            agents_app,
            ["discover", "--provider", "bedrock_agent", "--app-id", "bedrock-conn"],
        )
        mock_bedrock.assert_called_once_with(
            app_id="bedrock-conn",
            agents=None,
            yes=False,
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

    @patch.object(AgentsController, "discover_and_register_bedrock_agents")
    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_name_flag_passed_through(self, mock_init, mock_bedrock):
        """--name foo --name bar passes agents=['foo','bar'] to controller."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        runner.invoke(
            agents_app,
            [
                "discover",
                "--provider", "bedrock_agent",
                "--app-id", "bedrock-conn",
                "--name", "foo",
                "--name", "bar",
            ],
        )
        call_kwargs = mock_bedrock.call_args[1]
        assert call_kwargs["agents"] == ["foo", "bar"]

    @patch.object(AgentsController, "discover_and_register_bedrock_agents")
    @patch.object(AgentsController, "__init__", return_value=None)
    def test_discover_yes_flag_passed_through(self, mock_init, mock_bedrock):
        """--yes passes yes=True to discover_and_register_bedrock_agents."""
        from typer.testing import CliRunner
        from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app

        runner = CliRunner()
        runner.invoke(
            agents_app,
            [
                "discover",
                "--provider", "bedrock_agent",
                "--app-id", "bedrock-conn",
                "--yes",
            ],
        )
        call_kwargs = mock_bedrock.call_args[1]
        assert call_kwargs["yes"] is True

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
