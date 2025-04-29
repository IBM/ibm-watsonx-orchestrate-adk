import pytest
from typer import BadParameter
import requests
from unittest.mock import patch, mock_open
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import (
    _validate_connections_spec_content,
    _create_connection_from_spec,
    _parse_file,
    _format_token_headers,
    _validate_connection_params,
    _parse_entry,
    _get_credentials,
    add_configuration,
    add_credentials,
    add_identity_provider,
    add_connection,
    remove_connection,
    list_connections,
    import_connection,
    configure_connection,
    set_credentials_connection,
    set_identity_provider_connection
)
from ibm_watsonx_orchestrate.agent_builder.connections.types import (
    ConnectionType,
    ConnectionKind,
    ConnectionEnvironment,
    ConnectionPreference,
    ConnectionSecurityScheme,
    ConnectionAuthType,
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    # OAuth2AuthCodeCredentials,
    # OAuth2ImplicitCredentials,
    # OAuth2PasswordCredentials,
    # OAuth2ClientCredentials,
    OAuthOnBehalfOfCredentials,
    KeyValueConnectionCredentials,
    ConnectionConfiguration,
    IdentityProviderCredentials
)
from ibm_watsonx_orchestrate.client.connections.connections_client import ListConfigsResponse, GetConfigResponse

@pytest.fixture
def connections_spec_content() -> dict:
    return {
        "spec_version": "v1",
        "kind": "connection",
        "app_id": "test_app_id",
        "environments": {
            "draft": {
                "preference": ConnectionPreference.MEMBER,
                "security_scheme": ConnectionType.BASIC_AUTH
            },
            "live": {
                "preference": "member",
                "security_scheme": ConnectionType.BEARER_TOKEN
            }
        }
    }

class MockConnectionClient:
    def __init__(self, get_response=None, get_config_response=None, get_credentials_response=None, expected_application_write=None, expected_config_write=None, expected_credentials_write=None, list_response=None):
        self.get_response = get_response
        self.get_config_response = get_config_response
        self.get_credentials_response = get_credentials_response
        self.expected_application_write = expected_application_write
        self.expected_config_write = expected_config_write
        self.expected_credentials_write = expected_credentials_write
        self.list_response = list_response
    
    def get(self, app_id):
        return self.get_response
    
    def get_config(self, app_id, env):
        return self.get_config_response
    
    def get_credentials(self, app_id, env, use_sso):
        return self.get_credentials_response

    def create(self, payload):
        if self.expected_application_write:
            for key in self.expected_application_write:
                assert payload.get(key) == self.expected_application_write.get(key)
        
    def create_config(self, app_id, payload):
        if self.expected_config_write:
            for key in self.expected_config_write:
                assert payload.get(key) == self.expected_config_write.get(key)
    
    def create_credentials(self, app_id, env, use_sso, payload):
        if self.expected_credentials_write:
            for key in self.expected_credentials_write:
                assert payload.get(key) == self.expected_credentials_write.get(key)
    
    def update_config(self, app_id, payload, env):
        if self.expected_config_write:
            for key in self.expected_config_write:
                assert payload.get(key) == self.expected_config_write.get(key)
    
    def update_credentials(self, app_id, env, use_sso, payload):
        if self.expected_credentials_write:
            for key in self.expected_credentials_write:
                assert payload.get(key) == self.expected_credentials_write.get(key)
    
    def delete(self, app_id):
        pass

    def delete_credentials(self, app_id, env, use_sso):
        pass

    def list(self):
        return self.list_response

def _throw_mock_reponse(error):
    raise error        

class TestValidateConnectionsSpecContent:
    def test_validate_connections_spec_content(self, connections_spec_content):
        _validate_connections_spec_content(connections_spec_content)
    
    @pytest.mark.parametrize(
        "missing_req",
        [
            "spec_version",
            "kind",
            "app_id",
            "environments"
        ]
    )
    def test_validate_connections_spec_content_missing_requirement(self, missing_req, caplog, connections_spec_content):
        content = connections_spec_content.copy()
        content.pop(missing_req, None)

        with pytest.raises(SystemExit) as e:
            _validate_connections_spec_content(content)
        
        message = f"No '{missing_req}' found in provided spec file. Please ensure the spec file is in the correct format"

        captured = caplog.text
        assert message in captured
        

    @pytest.mark.parametrize(
        "invalid_kind",
        [
            "testing",
            "agent",
            "tool"
        ]
    )
    def test_validate_connections_spec_content_invalid_kind(self, invalid_kind, caplog, connections_spec_content):
        content = connections_spec_content.copy()
        content["kind"] = invalid_kind

        with pytest.raises(SystemExit) as e:
            _validate_connections_spec_content(content)
        
        message = "Field 'kind' must have a value of 'connection'. Please ensure the spec file is a valid connection spec."

        captured = caplog.text
        assert message in captured
    
    def test_validate_connections_spec_content_no_environments(self, caplog, connections_spec_content):
        content = connections_spec_content.copy()
        content["environments"] = []

        with pytest.raises(SystemExit) as e:
            _validate_connections_spec_content(content)
        
        message = f"No 'environments' found in provided spec file. Please ensure the spec file is in the correct format"

        captured = caplog.text
        assert message in captured

class TestCreateConnectionFromSpec:
    def test_create_connection_from_spec(self, connections_spec_content):
        mock_connection_client = MockConnectionClient(
            expected_application_write={
                "app_id": connections_spec_content.get("app_id")
            }
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client, \
            patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.is_local_dev') as mock_is_local_dev:
            mock_client.return_value = mock_connection_client
            mock_is_local_dev.return_value = True

            _create_connection_from_spec(connections_spec_content)
    
    def test_create_connection_from_spec_missing_content(self, caplog):
        with pytest.raises(SystemExit) as e:
            _create_connection_from_spec(content={})
        
        message = "No spec content provided. Please verify the input file is not empty"

        captured = caplog.text
        assert message in captured

class TestParseFile:
    def test_parse_file_yaml(self, connections_spec_content):
        with patch("builtins.open", mock_open()) as mock_file, \
            patch ("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller._create_connection_from_spec") as mock_from_spec, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.yaml.load") as mock_loader:
            
            mock_loader.return_value = connections_spec_content

            _parse_file("test.yaml")

            mock_from_spec.assert_called_once_with(content=connections_spec_content)
            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()
    
    def test_parse_file_json(self, connections_spec_content):
        with patch("builtins.open", mock_open()) as mock_file, \
            patch ("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller._create_connection_from_spec") as mock_from_spec, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.json.load") as mock_loader:
            
            mock_loader.return_value = connections_spec_content

            _parse_file("test.json")

            mock_from_spec.assert_called_once_with(content=connections_spec_content)
            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()
    
    def test_parse_file_invalid(self):
        with pytest.raises(ValueError) as e:
            _parse_file("test")

        message = "file must end in .json, .yaml or .yml"
        assert message in str(e)

class TestFormatTokenHeader:
    def test_format_token_headers(self):
        header_list = [
            "content-type: testing",
            "   Authorization     :  testing    "
        ]

        result = _format_token_headers(header_list=header_list)

        assert "content-type" in result
        assert "Authorization" in result
        assert result["content-type"] == "testing"
        assert result["Authorization"] == "testing"
    
    def test_format_token_headers_no_headers(self):
        header_list = []

        result = _format_token_headers(header_list=header_list)

        assert result is None
    
    def test_format_token_headers_invalid_headers(self, caplog):
        header_list = [
            "invalid"
        ]

        with pytest.raises(SystemExit) as e:
            result = _format_token_headers(header_list=header_list)

        message = f"Provided header '{header_list[0]}' is not in the correct format. Please format headers as 'key: value'"

        captured = caplog.text
        assert message in captured

class TestValidateConnectionParams:
    @pytest.mark.parametrize(
        ("conn_type", "required_args"),
        [
            (ConnectionType.BASIC_AUTH, ["username", "password"]),
            (ConnectionType.BEARER_TOKEN, ["token"]),
            (ConnectionType.API_KEY_AUTH, ["api_key"]),
            # (ConnectionType.OAUTH2_AUTH_CODE, ["client_id", "client_secret", "token_url", "auth_url"]),
            # (ConnectionType.OAUTH2_IMPLICIT, ["client_id", "auth_url"]),
            # (ConnectionType.OAUTH2_PASSWORD, ["client_id", "client_secret", "token_url", "auth_url"]),
            # (ConnectionType.OAUTH2_CLIENT_CREDS, ["client_id", "client_secret", "token_url"]),
            (ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, ["client_id", "token_url", "grant_type"]),
            (ConnectionType.KEY_VALUE, []),
        ]
    )
    def test_validate_connection_params(self, conn_type, required_args):
        args = {}
        for arg in required_args:
            args[arg] = "test"
        _validate_connection_params(conn_type, **args)
    
    @pytest.mark.parametrize(
        ("conn_type", "required_args"),
        [
            (ConnectionType.BASIC_AUTH, ["username", "password"]),
            (ConnectionType.BEARER_TOKEN, ["token"]),
            (ConnectionType.API_KEY_AUTH, ["api_key"]),
            # (ConnectionType.OAUTH2_AUTH_CODE, ["client_id", "client_secret", "token_url", "auth_url"]),
            # (ConnectionType.OAUTH2_IMPLICIT, ["client_id", "auth_url"]),
            # (ConnectionType.OAUTH2_PASSWORD, ["client_id", "client_secret", "token_url", "auth_url"]),
            # (ConnectionType.OAUTH2_CLIENT_CREDS, ["client_id", "client_secret", "token_url"]),
            (ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, ["client_id", "token_url", "grant_type"]),
            (ConnectionType.KEY_VALUE, []),
        ]
    )
    def test_validate_connection_params_missing_params(self, conn_type, required_args):
        args = {}
        for arg in required_args:
            args[arg] = "test"
        
        for arg in required_args: 
            args_copy = args.copy()
            args_copy.pop(arg)

            with pytest.raises(BadParameter) as e:
                _validate_connection_params(conn_type, **args_copy)
            
            if conn_type == ConnectionType.BASIC_AUTH:
                message = f"Missing flags --username (-u) and --password (-p) are both required for type {conn_type}"
            else:
                message = f"Missing flags --{arg.replace('_', '-')} is required for type {conn_type}"

            assert message in str(e)

class TestParseEntry:
    @pytest.mark.parametrize(
        ("entry_string", "expected"),
        [
            ("test=test", {"test": "test"}),
            ("test=", {"test": ""}),
        ]
    )
    def test_parse_entry(self, entry_string, expected):
        result = _parse_entry(entry_string)
        assert result == expected
    
    @pytest.mark.parametrize(
        "entry_string",
        [
            "test",
            "test=test=test",
        ]
    )
    def test_parse_entry_invalid_entries(self, entry_string, caplog):
        with pytest.raises(SystemExit) as e:
            _parse_entry(entry_string)
        
        message = f"The entry '{entry_string}' is not in the expected form '<key>=<value>'"

        captured = caplog.text
        assert message in captured

class TestGetCredentials:
    @pytest.mark.parametrize(
        ("conn_type", "required_args", "expected_cred_type"),
        [
            (ConnectionType.BASIC_AUTH, ["username", "password"], BasicAuthCredentials),
            (ConnectionType.BEARER_TOKEN, ["token"], BearerTokenAuthCredentials),
            (ConnectionType.API_KEY_AUTH, ["api_key"], APIKeyAuthCredentials),
            # (ConnectionType.OAUTH2_AUTH_CODE, ["client_id", "client_secret", "token_url", "auth_url"], OAuth2AuthCodeCredentials),
            # (ConnectionType.OAUTH2_IMPLICIT, ["client_id", "auth_url"], OAuth2ImplicitCredentials),
            # (ConnectionType.OAUTH2_PASSWORD, ["client_id", "client_secret", "token_url", "auth_url"], OAuth2PasswordCredentials),
            # (ConnectionType.OAUTH2_CLIENT_CREDS, ["client_id", "client_secret", "token_url"], OAuth2ClientCredentials),
            (ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, ["client_id", "token_url", "grant_type"], OAuthOnBehalfOfCredentials),
        ]
    )
    def test_get_credentials(self, conn_type, required_args, expected_cred_type):
        args = {}
        for arg in required_args:
            args[arg] = "test"
        
        if args.get("auth_url"):
            args["authorization_url"] = args.get("auth_url")

        credentials = _get_credentials(conn_type, **args)

        args["access_token_url"] = args.get("token_url")
        expected_creds = expected_cred_type(**args)

        assert type(credentials) == expected_cred_type
        assert credentials == expected_creds
    
    @pytest.mark.parametrize(
        ("entries", "expected"),
        [
            (["foo=bar", "test1=test2"], {"foo": "bar", "test1": "test2"}),
            ([], {})
        ]
    )
    def test_get_credentials_key_value(self, entries, expected):
        args = {
            "entries": entries
        }


        expected_creds = KeyValueConnectionCredentials(**expected)

        credentials = _get_credentials(ConnectionType.KEY_VALUE, **args)

        assert type(credentials) == KeyValueConnectionCredentials
        assert credentials == expected_creds
    
    @pytest.mark.parametrize(
        "conn_type",
        [
            "fake",
            "basic",
            ""
        ]
    )
    def test_get_credentials_invalid_type(self, conn_type):
        with pytest.raises(ValueError) as e:
            _get_credentials(conn_type)
        
        message = f"Invalid type '{conn_type}' selected"
        assert message in str(e)

class TestAddConfiguration:
    def test_add_configuration_create_config(self, connections_spec_content, caplog):
        expected_config = connections_spec_content.get("environments", {}).get("draft", {})
        mock_connection_client = MockConnectionClient(
            expected_config_write=expected_config
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            app_id = connections_spec_content.get("app_id")
            environment = ConnectionEnvironment.DRAFT
            config = ConnectionConfiguration(app_id=app_id, environment=environment, **expected_config)
            add_configuration(config)

            captured = caplog.text

            assert f"Creating configuration for connection '{app_id}' in the '{environment}' environment" in captured
            assert f"Configuration successfully created for '{environment}' environment of connection '{app_id}'." in captured

    def test_add_configuration_create_http_error(self, connections_spec_content, caplog):
        expected_config = connections_spec_content.get("environments", {}).get("draft", {})
        mock_connection_client = MockConnectionClient()

        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_repsonse = requests.models.Response()
            mock_repsonse._content = str.encode("Expected Message")
            mock_error = requests.HTTPError(response=mock_repsonse)

            mock_connection_client.create_config = lambda app_id,payload : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client


            app_id = connections_spec_content.get("app_id")
            environment = ConnectionEnvironment.DRAFT
            config = ConnectionConfiguration(app_id=app_id, environment=environment, **expected_config)
            with pytest.raises(SystemExit) as e:
                add_configuration(config)

            captured = caplog.text

            assert f"Creating configuration for connection '{app_id}' in the '{environment}' environment" in captured
            assert f"Expected Message" in captured
            assert f"Configuration successfully created for '{environment}' environment of connection '{app_id}'." not in captured

    def test_add_configuration_update_config(self, connections_spec_content, caplog):
        expected_config = connections_spec_content.get("environments", {}).get("draft", {})
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        config = ConnectionConfiguration(app_id=app_id, environment=environment, **expected_config)
        mock_connection_client = MockConnectionClient(
            expected_config_write=expected_config,
            get_config_response=config
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            add_configuration(config)

            captured = caplog.text

            assert f"Existing connection '{app_id}' with environment '{environment}' found. Updating configuration" in captured
            assert f"Configuration successfully updated for '{environment}' environment of connection '{app_id}'." in captured
            assert "Detected a change in" not in captured
    
    @pytest.mark.parametrize(
        ("updated_field", "message"),
        [
            ("preference", "Detected a change in preference/type from 'member' to 'team'. The associated credentials will be removed."),
            ("security_scheme", "Detected a change in auth type from 'basic_auth' to 'bearer_token'. The associated credentials will be removed."),
            # ("auth_type", "Detected a change in oauth flow from 'oauth2_implicit' to 'oauth2_password'. The associated credentials will be removed."),
        ]
    )
    def test_add_configuration_update_config_delete_credentials(self, connections_spec_content, updated_field, message, caplog):
        config_spec = connections_spec_content.get("environments", {}).get("draft", {})
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        mock_idp_data = {
            "body": {
                "requested_token_use": "",
                "requested_token_type": "",
            }
        }

        new_config_spec = config_spec.copy()
        match updated_field:
            case "preference":
                new_config_spec[updated_field] = ConnectionPreference.TEAM
            case "security_scheme":
                new_config_spec[updated_field] = ConnectionSecurityScheme.BEARER_TOKEN
            # case "auth_type":
            #     config_spec["security_scheme"] = ConnectionSecurityScheme.OAUTH2
            #     new_config_spec["security_scheme"] = ConnectionSecurityScheme.OAUTH2
            #     config_spec["sso"] = True
            #     new_config_spec["sso"] = True
            #     config_spec["idp_config_data"] = mock_idp_data
            #     new_config_spec["idp_config_data"] = mock_idp_data
            #     config_spec[updated_field] = ConnectionAuthType.OAUTH2_IMPLICIT
            #     new_config_spec[updated_field] = ConnectionAuthType.OAUTH2_PASSWORD

        config = ConnectionConfiguration(app_id=app_id, environment=environment, **config_spec)
        new_config = ConnectionConfiguration(app_id=app_id, environment=environment, **new_config_spec)

        mock_connection_client = MockConnectionClient(
            get_config_response=config,
            get_credentials_response=True
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            add_configuration(new_config)

            captured = caplog.text

            assert f"Existing connection '{app_id}' with environment '{environment}' found. Updating configuration" in captured
            assert message in captured
            assert f"Configuration successfully updated for '{environment}' environment of connection '{app_id}'." in captured
    
    def test_add_configuration_update_http_error(self, connections_spec_content, caplog):
        expected_config = connections_spec_content.get("environments", {}).get("draft", {})
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        config = ConnectionConfiguration(app_id=app_id, environment=environment, **expected_config)
        mock_connection_client = MockConnectionClient(
            expected_config_write=expected_config,
            get_config_response=config
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_repsonse = requests.models.Response()
            mock_repsonse._content = str.encode("Expected Message")
            mock_error = requests.HTTPError(response=mock_repsonse)

            mock_connection_client.update_config = lambda app_id,env,payload : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                add_configuration(config)

            captured = caplog.text

            assert f"Existing connection '{app_id}' with environment '{environment}' found. Updating configuration" in captured
            assert f"Expected Message" in captured
            assert f"Configuration successfully updated for '{environment}' environment of connection '{app_id}'." not in captured
            assert "Detected a change in" not in captured
    
    def test_add_configuration_delete_http_error(self, connections_spec_content, caplog):
        config_spec = connections_spec_content.get("environments", {}).get("draft", {})
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        config = ConnectionConfiguration(app_id=app_id, environment=environment, **config_spec)
        new_config_spec = config_spec.copy()
        new_config_spec["preference"] = ConnectionPreference.TEAM
        new_config = ConnectionConfiguration(app_id=app_id, environment=environment, **new_config_spec)

        mock_connection_client = MockConnectionClient(
            get_config_response=config,
            get_credentials_response=True
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_error = requests.HTTPError()

            mock_connection_client.delete_credentials = lambda app_id,env,use_sso : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                add_configuration(new_config)

            captured = caplog.text

            assert f"Existing connection '{app_id}' with environment '{environment}' found. Updating configuration" in captured
            assert f"Detected a change in preference/type from '{config.preference}' to '{new_config.preference}'. The associated credentials will be removed." in captured
            assert f"Configuration successfully updated for '{environment}' environment of connection '{app_id}'." not in captured

class TestAddCredentials:
    mock_oauth_credentials = OAuthOnBehalfOfCredentials(
        client_id="Test Client ID",
        access_token_url="Test Token URL",
        grant_type="Test Grant Type"
    )

    mock_bearer_credentials = BearerTokenAuthCredentials(
        token="Test Token"
    )

    def test_add_credentials_create_app_credentials(self, connections_spec_content, caplog):
        mock_connection_client = MockConnectionClient(
            expected_credentials_write = {"app_credentials": self.mock_oauth_credentials.model_dump()}
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            app_id = connections_spec_content.get("app_id")
            environment = ConnectionEnvironment.DRAFT
            add_credentials(app_id=app_id, environment=environment, use_sso=True, credentials=self.mock_oauth_credentials)

            captured = caplog.text

            assert f"Setting credentials for environment '{environment}' on connection '{app_id}'" in captured
            assert f"Credentials successfully set for '{environment}' environment of connection '{app_id}'" in captured
    
    def test_add_credentials_update_app_credentials(self, connections_spec_content, caplog):
        mock_connection_client = MockConnectionClient(
            get_credentials_response=True,
            expected_credentials_write = {"app_credentials": self.mock_oauth_credentials.model_dump()}
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            app_id = connections_spec_content.get("app_id")
            environment = ConnectionEnvironment.DRAFT
            add_credentials(app_id=app_id, environment=environment, use_sso=True, credentials=self.mock_oauth_credentials)

            captured = caplog.text

            assert f"Setting credentials for environment '{environment}' on connection '{app_id}'" in captured
            assert f"Credentials successfully set for '{environment}' environment of connection '{app_id}'" in captured
    

    def test_add_credentials_create_runtime_credentials(self, connections_spec_content, caplog):
        mock_connection_client = MockConnectionClient(
            expected_credentials_write = {"runtime_credentials": self.mock_bearer_credentials.model_dump(exclude_none=True)}
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            app_id = connections_spec_content.get("app_id")
            environment = ConnectionEnvironment.DRAFT
            add_credentials(app_id=app_id, environment=environment, use_sso=False, credentials=self.mock_bearer_credentials)

            captured = caplog.text

            assert f"Setting credentials for environment '{environment}' on connection '{app_id}'" in captured
            assert f"Credentials successfully set for '{environment}' environment of connection '{app_id}'" in captured
    
    def test_add_credentials_update_runtime_credentials(self, connections_spec_content, caplog):
        mock_connection_client = MockConnectionClient(
            get_credentials_response=True,
            expected_credentials_write = {"runtime_credentials": self.mock_bearer_credentials.model_dump(exclude_none=True)}
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            app_id = connections_spec_content.get("app_id")
            environment = ConnectionEnvironment.DRAFT
            add_credentials(app_id=app_id, environment=environment, use_sso=False, credentials=self.mock_bearer_credentials)

            captured = caplog.text

            assert f"Setting credentials for environment '{environment}' on connection '{app_id}'" in captured
            assert f"Credentials successfully set for '{environment}' environment of connection '{app_id}'" in captured
    

    def test_add_credentials_http_error(self, connections_spec_content, caplog):
        mock_connection_client = MockConnectionClient()
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_repsonse = requests.models.Response()
            mock_repsonse._content = str.encode("Expected Message")
            mock_error = requests.HTTPError(response=mock_repsonse)

            mock_connection_client.create_credentials = lambda app_id,env,use_sso,payload : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                app_id = connections_spec_content.get("app_id")
                environment = ConnectionEnvironment.DRAFT
                add_credentials(app_id=app_id, environment=environment, use_sso=False, credentials=self.mock_bearer_credentials)

            captured = caplog.text
            assert "Expected Message" in captured
            assert f"Setting credentials for environment '{environment}' on connection '{app_id}'" in captured
            assert f"Credentials successfully set for '{environment}' environment of connection '{app_id}'" not in captured
    
class TestAddIdentityProvider:
    mock_idp_credentials = IdentityProviderCredentials(
        idp_url="Test IDP URL",
        client_id="Test Client ID",
        client_secret="Test Client Secret",
        scope="Test Scope",
        grant_type="Test Grant Type"
    )
    def test_add_identity_provider_create(self, connections_spec_content, caplog):
        mock_connection_client = MockConnectionClient(
            expected_credentials_write= {"idp_credentials": self.mock_idp_credentials.model_dump()}
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            app_id = connections_spec_content.get("app_id")
            environment = ConnectionEnvironment.DRAFT
            add_identity_provider(app_id=app_id, environment=environment, idp=self.mock_idp_credentials)

            captured = caplog.text
            
            assert f"Setting identity provider for environment '{environment}' on connection '{app_id}'" in captured
            assert f"Identity provider successfully set for '{environment}' environment of connection '{app_id}'" in captured
    
    def test_add_identity_provider_update(self, connections_spec_content, caplog):
        mock_connection_client = MockConnectionClient(
            get_credentials_response=True,
            expected_credentials_write= {"idp_credentials": self.mock_idp_credentials.model_dump()}
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            app_id = connections_spec_content.get("app_id")
            environment = ConnectionEnvironment.DRAFT
            add_identity_provider(app_id=app_id, environment=environment, idp=self.mock_idp_credentials)

            captured = caplog.text
            
            assert f"Setting identity provider for environment '{environment}' on connection '{app_id}'" in captured
            assert f"Identity provider successfully set for '{environment}' environment of connection '{app_id}'" in captured
    
    def test_add_identity_provider_http_error(self, connections_spec_content, caplog):
        mock_connection_client = MockConnectionClient()
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_repsonse = requests.models.Response()
            mock_repsonse._content = str.encode("Expected Message")
            mock_error = requests.HTTPError(response=mock_repsonse)

            mock_connection_client.create_credentials = lambda app_id,env,use_sso,payload : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                app_id = connections_spec_content.get("app_id")
                environment = ConnectionEnvironment.DRAFT
                add_identity_provider(app_id=app_id, environment=environment, idp=self.mock_idp_credentials)

            captured = caplog.text
            assert "Expected Message" in captured
            assert f"Setting identity provider for environment '{environment}' on connection '{app_id}'" in captured
            assert f"Identity provider successfully set for '{environment}' environment of connectio {app_id}'" not in captured

class TestAddConnection:
    def test_add_connetion(self, connections_spec_content, caplog):
        app_id = connections_spec_content.get("app_id")
        mock_connection_client = MockConnectionClient(
            expected_application_write={"app_id": app_id}
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            add_connection(app_id=app_id)

            captured = caplog.text

            assert f"Creating connection '{app_id}'" in captured
            assert f"Successfully created connection '{app_id}'" in captured
    
    def test_add_connetion_http_error(self, connections_spec_content, caplog):
        app_id = connections_spec_content.get("app_id")
        mock_connection_client = MockConnectionClient()
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_repsonse = requests.models.Response()
            mock_repsonse._content = str.encode("{\"detail\": \"Expected Message\"}")
            mock_error = requests.HTTPError(response=mock_repsonse)
            mock_connection_client.create = lambda payload : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                add_connection(app_id=app_id)

            captured = caplog.text

            assert f"Creating connection '{app_id}'" in captured
            assert "Expected Message" in captured
            assert f"Successfully created connection '{app_id}'" not in captured
    
    def test_add_connetion_http_error_non_json(self, connections_spec_content, caplog):
        app_id = connections_spec_content.get("app_id")
        mock_connection_client = MockConnectionClient()
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_repsonse = requests.models.Response()
            mock_repsonse._content = str.encode("Expected Message")
            mock_error = requests.HTTPError(response=mock_repsonse)
            mock_connection_client.create = lambda payload : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                add_connection(app_id=app_id)

            captured = caplog.text

            assert f"Creating connection '{app_id}'" in captured
            assert "Expected Message" in captured
            assert f"Successfully created connection '{app_id}'" not in captured
    
    def test_add_connetion_http_error_409(self, connections_spec_content, caplog):
        app_id = connections_spec_content.get("app_id")
        mock_connection_client = MockConnectionClient()
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_repsonse = requests.models.Response()
            mock_repsonse.status_code = 409
            mock_repsonse._content = str.encode("{\"detail\": \"Expected Message\"}")
            mock_error = requests.HTTPError(response=mock_repsonse)
            mock_connection_client.create = lambda payload : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                add_connection(app_id=app_id)

            captured = caplog.text

            assert f"Creating connection '{app_id}'" in captured
            assert f"Failed to create connection. A connection with the App ID '{app_id}' already exists. Please select a diffrent App ID or delete the existing resource." in captured
            assert f"Successfully created connection '{app_id}'" not in captured

class TestRemoveConnection:
    def test_remove_connetion(self, connections_spec_content, caplog):
        app_id = connections_spec_content.get("app_id")
        mock_connection_client = MockConnectionClient()
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            remove_connection(app_id=app_id)

            captured = caplog.text

            assert f"Removing connection '{app_id}'" in captured
            assert f"Connection '{app_id}' successfully removed" in captured
    
    def test_remove_connetion_http_error(self, connections_spec_content, caplog):
        app_id = connections_spec_content.get("app_id")
        mock_connection_client = MockConnectionClient()
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_repsonse = requests.models.Response()
            mock_repsonse._content = str.encode("Expected Message")
            mock_error = requests.HTTPError(response=mock_repsonse)
            mock_connection_client.delete = lambda app_id : _throw_mock_reponse(mock_error)
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                remove_connection(app_id=app_id)

            captured = caplog.text

            assert f"Removing connection '{app_id}'" in captured
            assert "Expected Message" in captured
            assert f"Connection '{app_id}' successfully removed" not in captured

class TestListConnections:
    mock_list_response = [
        ListConfigsResponse(
            connection_id="UUID_1",
            app_id="test_app_id_1",
            name="test_app_id_1",
            security_scheme=ConnectionSecurityScheme.BASIC_AUTH,
            auth_type=None,
            environment=ConnectionEnvironment.DRAFT,
            preference=ConnectionPreference.MEMBER,
            credentials_entered=False
        ),
        ListConfigsResponse(
            connection_id="UUID_1",
            app_id="test_app_id_1",
            name="test_app_id_1",
            security_scheme=ConnectionSecurityScheme.OAUTH2,
            auth_type=ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW,
            environment=ConnectionEnvironment.LIVE,
            preference=ConnectionPreference.TEAM,
            credentials_entered=True
        ),
        ListConfigsResponse(
            connection_id="UUID_2",
            app_id="test_app_id_2",
            name="test_app_id_2",
            security_scheme=ConnectionSecurityScheme.KEY_VALUE,
            auth_type=None,
            environment=ConnectionEnvironment.LIVE,
            preference=ConnectionPreference.TEAM,
            credentials_entered=True
        )
    ]

    def test_list_connections(self):
        mock_connection_client = MockConnectionClient(
            list_response=self.mock_list_response
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            list_connections(environment=None)
    
    def test_list_connections_verbose(self):
        mock_connection_client = MockConnectionClient(
            list_response=self.mock_list_response
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            list_connections(environment=None, verbose=True)
    
    def test_list_connections_no_connections(self, caplog):
        mock_connection_client = MockConnectionClient(
            list_response=[]
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            list_connections(environment=None)

            captured = caplog.text

            assert "No connections found. You can create connections using `orchestrate connections add`" in captured
    
    def test_list_connections_no_connections_verbose(self, capsys):
        mock_connection_client = MockConnectionClient(
            list_response=[]
        )
        with patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            list_connections(environment=None, verbose=True)

            captured = capsys.readouterr()

            assert "[]" in captured.out

class TestImportConnection:
    def test_import_connection_yaml(self, connections_spec_content):
        with patch("builtins.open", mock_open()) as mock_file, \
            patch ("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller._create_connection_from_spec") as mock_from_spec, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.yaml.load") as mock_loader:
            
            mock_loader.return_value = connections_spec_content

            import_connection("test.yaml")

            mock_from_spec.assert_called_once_with(content=connections_spec_content)
            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()
    
    def test_import_connection_json(self, connections_spec_content):
        with patch("builtins.open", mock_open()) as mock_file, \
            patch ("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller._create_connection_from_spec") as mock_from_spec, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.json.load") as mock_loader:
            
            mock_loader.return_value = connections_spec_content

            import_connection("test.json")

            mock_from_spec.assert_called_once_with(content=connections_spec_content)
            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()

class TestConfigureConnection:
    mock_configure_args = {
        "app_id": "Test App ID",
        "environment": ConnectionEnvironment.DRAFT,
        "type": ConnectionPreference.MEMBER,
        "kind": ConnectionKind.oauth_auth_on_behalf_of_flow,
        "server_url": "Test Server URL",
        "sso": True,
        "idp_token_use": "Test Token Use",
        "idp_token_type": "Test Token Type",
        "idp_token_header": ["content-type: testing"],
        "app_token_header": ["content-type: testing"]
    }

    def test_configure_connection(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.add_configuration") as mock_add_configuration, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.is_local_dev") as mock_is_local_dev:
            mock_is_local_dev.return_value = False
            configure_connection(**self.mock_configure_args)

            mock_add_configuration.assert_called_once()
    
    def test_configure_connection_live_local_error(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.add_configuration") as mock_add_configuration, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.is_local_dev") as mock_is_local_dev:

            mock_is_local_dev.return_value = True
            args = self.mock_configure_args.copy()
            args["environment"] = ConnectionEnvironment.LIVE

            with pytest.raises(SystemExit) as e:
                configure_connection(**args)

            mock_add_configuration.assert_not_called()

            captured = caplog.text
            assert f"Cannot create configuration for environment '{args.get('environment')}'. Local development does not support any environments other than 'draft'." in captured

class TestSetCredentialsConnection:
# ["client_id", "client_secret", "token_url", "auth_url"]),
#             (ConnectionType.OAUTH2_IMPLICIT, ["client_id", "auth_url"]),
#             (ConnectionType.OAUTH2_PASSWORD, ["client_id", "client_secret", "token_url", "auth_url"]),
#             (ConnectionType.OAUTH2_CLIENT_CREDS, ["client_id", "client_secret", "token_url"]),
#             (ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, ["client_id", "token_url", "auth_url", "grant_type"]),
    @pytest.mark.parametrize(
        ("config", "func_args"),
        [
            (GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.BASIC_AUTH, auth_type=None), ["username", "password"]),
            (GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.BEARER_TOKEN, auth_type=None), ["token"]),
            (GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.API_KEY_AUTH, auth_type=None), ["api_key"]),
            # (GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_AUTH_CODE), ["client_id", "client_secret", "token_url", "auth_url"]),
            # (GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_IMPLICIT), ["client_id", "auth_url"]),
            # (GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_PASSWORD), ["client_id", "client_secret", "token_url", "auth_url"]),
            # (GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_CLIENT_CREDS), ["client_id", "client_secret", "token_url"]),
            (GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW), ["client_id", "token_url", "grant_type"]),
            (GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.KEY_VALUE, auth_type=None), ["foo", "bar"]),
        ]
    )
    def test_set_credentials_connection(self, connections_spec_content, config, func_args):
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        mock_connection_client = MockConnectionClient(
            get_config_response=config
        )

        args = {}
        for arg in func_args:
            args[arg] = "testing"
         
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.add_credentials") as mock_add_credentials, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_client:
                
            mock_client.return_value = mock_connection_client

            set_credentials_connection(app_id=app_id, environment=environment, **args)

            mock_add_credentials.assert_called_once()
    
    def test_set_credentials_connection_no_config(self, connections_spec_content, caplog):
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        mock_connection_client = MockConnectionClient()
         
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.add_credentials") as mock_add_credentials, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_client:
                
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                set_credentials_connection(app_id=app_id, environment=environment)

            mock_add_credentials.assert_not_called()

            captured = caplog.text

            assert f"No configuration '{environment}' found for connection '{app_id}'. Please create the connection using `orchestrate connections add --app-id {app_id}` then add a configuration `orchestrate connections configure --app-id {app_id} --environment {environment} ...`" in captured

class TestSetIdentityProviderConnection:
    mock_idp_args = {
        "url": "Test URL",
        "client_id": "Test Client ID",
        "client_secret": "Test Client Secret",
        "scope": "Test Scope",
        "grant_type": "Test Grant Type"
    }

    @pytest.mark.parametrize(
        "config",
        [
            # GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_AUTH_CODE),
            # GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_IMPLICIT),
            # GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_PASSWORD),
            # GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_CLIENT_CREDS),
            GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW)
        ]
    )
    def test_set_identity_provider_connection(self, connections_spec_content, config):
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        mock_connection_client = MockConnectionClient(
            get_config_response=config
        )
         
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.add_identity_provider") as mock_add_identity_provider, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_client:
                
            mock_client.return_value = mock_connection_client
            set_identity_provider_connection(app_id=app_id, environment=environment, **self.mock_idp_args)

        mock_add_identity_provider.assert_called_once()

    @pytest.mark.parametrize(
        "config",
        [
            GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.BASIC_AUTH, auth_type=None),
            GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.BEARER_TOKEN, auth_type=None),
            GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.API_KEY_AUTH, auth_type=None),
            GetConfigResponse(sso=True, security_scheme=ConnectionSecurityScheme.KEY_VALUE, auth_type=None),
        ]
    )
    def test_set_identity_provider_connection_non_oauth(self, connections_spec_content, config, caplog):
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        mock_connection_client = MockConnectionClient(
            get_config_response=config
        )
         
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.add_identity_provider") as mock_add_identity_provider, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_client:
                
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                set_identity_provider_connection(app_id=app_id, environment=environment, **self.mock_idp_args)

            mock_add_identity_provider.assert_not_called()

            captured = caplog.text
            
            assert f"Identity providers cannot be set for non-OAuth connection types. The connections specified is of type '{config.security_scheme}'" in captured
    
    @pytest.mark.parametrize(
        "config",
        [
            # GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_AUTH_CODE),
            # GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_IMPLICIT),
            # GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_PASSWORD),
            # GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH2_CLIENT_CREDS),
            GetConfigResponse(sso=False, security_scheme=ConnectionSecurityScheme.OAUTH2, auth_type=ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW)
        ]
    )
    def test_set_identity_provider_connection_non_sso(self, connections_spec_content, config, caplog):
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        mock_connection_client = MockConnectionClient(
            get_config_response=config
        )
         
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.add_identity_provider") as mock_add_identity_provider, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_client:
                
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                set_identity_provider_connection(app_id=app_id, environment=environment, **self.mock_idp_args)

            mock_add_identity_provider.assert_not_called()

            captured = caplog.text
            
            assert f"Cannot set Identity Provider when 'sso' is false in configuration. Please enable sso for connection '{app_id}' in environment '{environment}' and try again." in captured

    def test_set_identity_provider_connection_no_config(self, connections_spec_content, caplog):
        app_id = connections_spec_content.get("app_id")
        environment = ConnectionEnvironment.DRAFT

        mock_connection_client = MockConnectionClient()
         
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.add_identity_provider") as mock_add_identity_provider, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_client:
                
            mock_client.return_value = mock_connection_client

            with pytest.raises(SystemExit) as e:
                set_identity_provider_connection(app_id=app_id, environment=environment, **self.mock_idp_args)

            mock_add_identity_provider.assert_not_called()

            captured = caplog.text
            
            assert f"No configuration '{environment}' found for connection '{app_id}'. Please create the connection using `orchestrate connections add --app-id {app_id}` then add a configuration `orchestrate connections configure --app-id {app_id} --environment {environment} ...`" in captured