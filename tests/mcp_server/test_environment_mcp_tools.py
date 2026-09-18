"""
Add 'orchestrate environment' commands to MCP Server

Tests for the four MCP environment tools in environment/mcp_tools.py.
All external dependencies (Config, environment_controller) are mocked so
tests never touch the filesystem or a real WXO instance.

    TestListEnvironments    (5) — count, active flag, key shape, URLs, no-active-env
    TestAddEnvironment      (6) — controller args, activate flag, return message,
                                  insecure+verify guard, missing required params
    TestRemoveEnvironment   (3) — controller delegation, return message, missing param
    TestActivateEnvironment (5) — WXO path, local-dev path, CPD path,
                                  return message, missing param
    TestToolsExport         (2) — all four tools in __tools__, exact count
"""

import pytest
from unittest.mock import patch, MagicMock

from ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools import (
    list_environments,
    add_environment,
    remove_environment,
    activate_environment,
    __tools__,
)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

MOCK_ENVS = {
    "production": {"wxo_url": "https://prod.example.com"},
    "staging": {"wxo_url": "https://staging.example.com"},
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config():
    """Two environments, 'production' active. MagicMock avoids filesystem access."""
    cfg = MagicMock()
    cfg.read.return_value = "production"  # active env name
    cfg.get.return_value = MOCK_ENVS      # full environments section
    return cfg


# ---------------------------------------------------------------------------
# list_environments
# ---------------------------------------------------------------------------

class TestListEnvironments:
    # Patch mcp_tools.Config (not cli.config.Config): patch() replaces the name
    # at the use site. return_value ensures Config() returns the mock instance.

    def test_returns_all_environments(self, mock_config):
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.Config",
            return_value=mock_config,
        ):
            result = list_environments()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_active_environment_flagged(self, mock_config):
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.Config",
            return_value=mock_config,
        ):
            result = list_environments()

        active = [env for env in result if env["active"]]
        inactive = [env for env in result if not env["active"]]

        assert len(active) == 1
        assert active[0]["name"] == "production"
        assert len(inactive) == 1
        assert inactive[0]["name"] == "staging"

    def test_environment_contains_expected_keys(self, mock_config):
        # Key names are part of the tool's public contract with the AI.
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.Config",
            return_value=mock_config,
        ):
            result = list_environments()

        for env in result:
            assert "name" in env
            assert "url" in env
            assert "active" in env

    def test_url_populated_correctly(self, mock_config):
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.Config",
            return_value=mock_config,
        ):
            result = list_environments()

        urls = {env["name"]: env["url"] for env in result}
        assert urls["production"] == "https://prod.example.com"
        assert urls["staging"] == "https://staging.example.com"

    def test_no_active_environment(self):
        # Fixture returns "production"; this case needs None — use a local mock.
        cfg = MagicMock()
        cfg.read.return_value = None
        cfg.get.return_value = MOCK_ENVS

        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.Config",
            return_value=cfg,
        ):
            result = list_environments()

        assert not any(env["active"] for env in result)


# ---------------------------------------------------------------------------
# add_environment
# ---------------------------------------------------------------------------

class TestAddEnvironment:
    # assert_called_once_with() verifies call count AND every argument name/value,
    # catching both omissions and silent renames between MCP and controller params.

    def test_add_calls_controller(self):
        # Verifies all defaults when only required params are supplied.
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.add"
        ) as mock_add:
            add_environment(name="my-env", url="https://my.example.com")
            mock_add.assert_called_once_with(
                name="my-env",
                url="https://my.example.com",
                should_activate=False,  # MCP param 'activate' → controller param 'should_activate'
                iam_url=None,
                type=None,  # MCP param 'type_' → controller param 'type'
                insecure=False,
                verify=None,
            )

    def test_add_with_activate(self):
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.add"
        ) as mock_add:
            add_environment(name="my-env", url="https://my.example.com", activate=True)
            mock_add.assert_called_once_with(
                name="my-env",
                url="https://my.example.com",
                should_activate=True,
                iam_url=None,
                type=None,
                insecure=False,
                verify=None,
            )

    def test_add_returns_success_message(self):
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.add"
        ):
            result = add_environment(name="my-env", url="https://my.example.com")
            assert "my-env" in result

    def test_add_insecure_and_verify_raises(self):
        # CLI command calls sys.exit(1) here; MCP raises ValueError so the
        # server stays alive. Regex matches either word order.
        with pytest.raises(ValueError, match="insecure.*verify|verify.*insecure"):
            add_environment(
                name="my-env",
                url="https://my.example.com",
                insecure=True,
                verify="/path/to/cert.pem",
            )

    def test_add_missing_required_name_raises(self):
        with pytest.raises(TypeError):
            add_environment(url="https://my.example.com")  # type: ignore[call-arg]

    def test_add_missing_required_url_raises(self):
        with pytest.raises(TypeError):
            add_environment(name="my-env")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# remove_environment
# ---------------------------------------------------------------------------

class TestRemoveEnvironment:
    def test_remove_calls_controller(self):
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.remove"
        ) as mock_remove:
            remove_environment(name="my-env")
            mock_remove.assert_called_once_with(name="my-env")

    def test_remove_returns_success_message(self):
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.remove"
        ):
            result = remove_environment(name="my-env")
            assert "my-env" in result

    def test_remove_missing_required_name_raises(self):
        with pytest.raises(TypeError):
            remove_environment()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# activate_environment
# ---------------------------------------------------------------------------

class TestActivateEnvironment:
    def test_activate_calls_controller(self):
        # 'api_key' (MCP) → 'apikey' (controller): Typer maps '--api-key' to
        # 'apikey' and that name is preserved in the controller.
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.activate"
        ) as mock_activate:
            activate_environment(name="my-env", api_key="secret-key")
            mock_activate.assert_called_once_with(
                name="my-env",
                apikey="secret-key",
                username=None,
                password=None,
            )

    def test_activate_without_credentials(self):
        # All credentials None — the local dev path.
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.activate"
        ) as mock_activate:
            activate_environment(name="my-env")
            mock_activate.assert_called_once_with(
                name="my-env",
                apikey=None,
                username=None,
                password=None,
            )

    def test_activate_with_cpd_credentials(self):
        # CPD path: username + password, no api_key.
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.activate"
        ) as mock_activate:
            activate_environment(name="my-env", username="admin", password="s3cr3t")
            mock_activate.assert_called_once_with(
                name="my-env",
                apikey=None,
                username="admin",
                password="s3cr3t",
            )

    def test_activate_returns_success_message(self):
        with patch(
            "ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.environment_controller.activate"
        ):
            result = activate_environment(name="my-env")
            assert "my-env" in result

    def test_activate_missing_required_name_raises(self):
        with pytest.raises(TypeError):
            activate_environment()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# __tools__ export
# ---------------------------------------------------------------------------

class TestToolsExport:
    # Guards against a tool being defined but omitted from __tools__, which
    # would leave it silently unreachable. Also catches duplicates that would
    # corrupt the FastMCP schema.

    def test_tools_list_contains_all_four_tools(self):
        tool_names = [fn.__name__ for fn in __tools__]
        assert "list_environments" in tool_names
        assert "add_environment" in tool_names
        assert "remove_environment" in tool_names
        assert "activate_environment" in tool_names

    def test_tools_list_has_exactly_four_entries(self):
        assert len(__tools__) == 4
