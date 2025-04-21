from ibm_watsonx_orchestrate.cli.commands.connections import connections_command
from unittest.mock import patch
import pytest

class TestConnectionsAdd:
    base_params = {
        "app_id": "Testing_App_ID"
    }

    def test_add_connection_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.add_connection") as mock:
            connections_command.add_connection_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        "missing_param",
        [
            "app_id"
        ]
    )
    def test_add_connection_command_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.add_connection") as mock:
            with pytest.raises(TypeError) as e:
                connections_command.add_connection_command(**missing_params)
            mock.assert_not_called

            assert f"add_connection_command() missing 1 required positional argument: '{missing_param}'" in str(e.value)

class TestConnectionsRemove:
    base_params = {
        "app_id": "Testing_App_ID"
    }

    def test_remove_connection_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.remove_connection") as mock:
            connections_command.remove_connection_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        "missing_param",
        [
            "app_id"
        ]
    )
    def test_remove_connection_command_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.remove_connection") as mock:
            with pytest.raises(TypeError) as e:
                connections_command.remove_connection_command(**missing_params)
            mock.assert_not_called

            assert f"remove_connection_command() missing 1 required positional argument: '{missing_param}'" in str(e.value)

class TestConnectionsList:
    base_params = {
        "environment": "draft",
        "verbose": False
    }

    def test_list_connection_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.list_connections") as mock:
            connections_command.list_connections_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        ("missing_param", "default_value"),
        [
            ("environment", None),
            ("verbose", None),
        ]
    )
    def test_list_connection_command_missing_optional_parms(self, missing_param, default_value):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        expected_params = self.base_params.copy()
        expected_params[missing_param] = default_value
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.list_connections") as mock:
            connections_command.list_connections_command(**missing_params)
            mock.assert_called_once_with(**expected_params)

class TestConnectionsImport:
    base_params = {
        "file": "fake/path/to/file.yml"
    }

    def test_import_connection_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.import_connection") as mock:
            connections_command.import_connection_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        "missing_param",
        [
            "file"
        ]
    )
    def test_import_connection_command_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.import_connection") as mock:
            with pytest.raises(TypeError) as e:
                connections_command.import_connection_command(**missing_params)
            mock.assert_not_called

            assert f"import_connection_command() missing 1 required positional argument: '{missing_param}'" in str(e.value)

class TestConnectionsConfigure:
    base_params = {
        "app_id": "Testing_App_ID",
        "environment": "draft",
        "type": "member",
        "kind": "oauth_auth_on_behalf_of_flow",
        "server_url": "example.com",
        "sso": True,
        "idp_token_use": "token_use",
        "idp_token_type": "token_type",
        "idp_token_header": "token_header",
        "app_token_header": "token_header"
    }

    def test_configure_connection_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.configure_connection") as mock:
            connections_command.configure_connection_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        ("missing_param", "default_value"),
        [
            ("server_url", None),
            ("sso", False),
            ("idp_token_use", None),
            ("idp_token_type", None),
            ("idp_token_header", None),
            ("app_token_header", None)
        ]
    )
    def test_configure_connection_command_missing_optional_parms(self, missing_param, default_value):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        expected_params = self.base_params.copy()
        expected_params[missing_param] = default_value
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.configure_connection") as mock:
            connections_command.configure_connection_command(**missing_params)
            mock.assert_called_once_with(**expected_params)

    @pytest.mark.parametrize(
        "missing_param",
        [
            "app_id",
            "environment",
            "type",
            "kind"
        ]
    )
    def test_configure_connection_command_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.configure_connection") as mock:
            with pytest.raises(TypeError) as e:
                connections_command.configure_connection_command(**missing_params)
            mock.assert_not_called

            assert f"configure_connection_command() missing 1 required positional argument: '{missing_param}'" in str(e.value)

class TestConnectionsSetCredentials:
    base_params = {
        "app_id": "Testing_App_ID",
        "environment": "draft",
        "username": "test_username",
        "password": "test_password",
        "token": "test_token",
        "api_key": "test_api_key",
        "client_id": "test_client_id",
        # "client_secret": "test_client_secret",
        "token_url": "test_token_url",
        # "auth_url": "test_auth_url",
        "grant_type": "test_grant_type",
        "entries": ["testentry1=testentry"]
    }

    def test_set_credentials_connection_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.set_credentials_connection") as mock:
            connections_command.set_credentials_connection(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        ("missing_param", "default_value"),
        [
            ("username", None),
            ("password", None),
            ("token", None),
            ("api_key", None),
            ("client_id", None),
            # ("client_secret", None),
            ("token_url", None),
            # ("auth_url", None),
            ("grant_type", None),
            ("entries", None)
        ]
    )
    def test_set_credentials_connection_command_missing_optional_parms(self, missing_param, default_value):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        expected_params = self.base_params.copy()
        expected_params[missing_param] = default_value
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.set_credentials_connection") as mock:
            connections_command.set_credentials_connection_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)

    @pytest.mark.parametrize(
        "missing_param",
        [
            "app_id",
            "environment",
        ]
    )
    def test_set_credentials_connection_command_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.set_credentials_connection") as mock:
            with pytest.raises(TypeError) as e:
                connections_command.set_credentials_connection_command(**missing_params)
            mock.assert_not_called

            assert f"set_credentials_connection_command() missing 1 required positional argument: '{missing_param}'" in str(e.value)

class TestConnectionsSetIdentityProvider:
    base_params = {
        "app_id": "Testing_App_ID",
        "environment": "draft",
        "url": "test_url",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scope": "test_scope",
        "grant_type": "test_grant_type",
    }

    def test_set_identity_provider_connection_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.set_identity_provider_connection") as mock:
            connections_command.set_identity_provider_connection_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        "missing_param",
        [
            "app_id",
            "environment",
            "url",
            "client_id",
            "client_secret",
            "scope",
            "grant_type"
        ]
    )
    def test_set_identity_provider_connection_command_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.set_identity_provider_connection") as mock:
            with pytest.raises(TypeError) as e:
                connections_command.set_identity_provider_connection_command(**missing_params)
            mock.assert_not_called

            assert f"set_identity_provider_connection_command() missing 1 required positional argument: '{missing_param}'" in str(e.value)
