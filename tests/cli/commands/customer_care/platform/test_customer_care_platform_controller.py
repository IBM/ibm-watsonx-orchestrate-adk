from io import StringIO
import pytest
from unittest.mock import patch
from ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller import (
    configure_platform_customer_care,
    configure_genesys,
    list_platform_customer_care,
    remove_platform_customer_care
)
from ibm_watsonx_orchestrate.cli.commands.customer_care.platform.types import (
    GenesysPlatformConnection,
    PlatformType,
    ApplicationPostfix
)
from ibm_watsonx_orchestrate.agent_builder.connections.types import (
    ConnectionEnvironment,
    ConnectionKind,
    ConnectionPreference,
    ConnectionSecurityScheme
)
from ibm_watsonx_orchestrate.client.connections.connections_client import ListConfigsResponse
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

class MockConnectionClient:
    def __init__(self, list_response=None, get_response=None):
        self.list_response = list_response or []
        self.get_response = get_response
        self.created_connections = []
        self.configured_connections = []
        self.credentials_set = []
        self.deleted_connections = []

    def list(self):
        return self.list_response

    def get(self, app_id):
        return self.get_response

    def create(self, payload):
        self.created_connections.append(payload)

    def delete(self, app_id):
        self.deleted_connections.append(app_id)

@pytest.fixture
def connection_credentials():
    return {
        "name": "test-connection",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "client_secret_stdin": None,
        "endpoint": "https://test.endpoint.com"
    }

@pytest.fixture
def connection_credentials_no_secrets():
    return {
        "name": "test-connection",
        "client_id": "test-client-id",
        "endpoint": "https://test.endpoint.com"
    }

@pytest.fixture
def mock_connections():
    return [
        ListConfigsResponse(
            connection_id="connection-1",
            app_id=f"genesys-connection-{ApplicationPostfix.GENESYS}",
            name=f"genesys-connection-{ApplicationPostfix.GENESYS}",
            security_scheme=ConnectionSecurityScheme.KEY_VALUE,
            auth_type=None,
            environment=ConnectionEnvironment.DRAFT,
            preference=ConnectionPreference.TEAM,
            credentials_entered=True
        ),
        ListConfigsResponse(
            connection_id="connection-2",
            app_id="other-connection",
            name="other-connection",
            security_scheme=ConnectionSecurityScheme.KEY_VALUE,
            auth_type=None,
            environment=ConnectionEnvironment.DRAFT,
            preference=ConnectionPreference.TEAM,
            credentials_entered=True
        )
    ]

class TestConfigurePlatformCustomerCare:
    def test_configure_platform_customer_care_using_genesys_draft(self, connection_credentials):
        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.configure_genesys') as mock_configure_genesys, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.is_local_dev') as mock_is_local_dev:
            mock_is_local_dev.return_value = True
            
            configure_platform_customer_care(
                type=PlatformType.GENESYS,
                **connection_credentials
            )
            
            # Verify only draft environment was used
            assert mock_configure_genesys.call_count == 1

            mock_configure_genesys.assert_called_once_with(
                GenesysPlatformConnection(
                    app_id=f"{connection_credentials['name']}-{ApplicationPostfix.GENESYS}",
                    client_id=connection_credentials['client_id'],
                    client_secret=connection_credentials['client_secret'],
                    endpoint=connection_credentials['endpoint'],
                    environment=ConnectionEnvironment.DRAFT
                )
            )

    def test_configure_platform_customer_care_using_genesys_live(self, connection_credentials):
        app_id = f"{connection_credentials['name']}-{ApplicationPostfix.GENESYS}"

        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.configure_genesys') as mock_configure_genesys, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.is_local_dev') as mock_is_local_dev:
            mock_is_local_dev.return_value = False

            configure_platform_customer_care(
                type=PlatformType.GENESYS,
                **connection_credentials
            )

            # Verify both draft and live environments were used
            assert mock_configure_genesys.call_count == 2
            
            mock_configure_genesys.assert_any_call(
                GenesysPlatformConnection(
                    app_id=app_id,
                    client_id=connection_credentials['client_id'],
                    client_secret=connection_credentials['client_secret'],
                    endpoint=connection_credentials['endpoint'],
                    environment=ConnectionEnvironment.DRAFT
                )
            )

            mock_configure_genesys.assert_any_call(
                GenesysPlatformConnection(
                    app_id=app_id,
                    client_id=connection_credentials['client_id'],
                    client_secret=connection_credentials['client_secret'],
                    endpoint=connection_credentials['endpoint'],
                    environment=ConnectionEnvironment.LIVE
                )
            )

    def test_configure_platform_customer_care_using_genesys_using_stdin_secret(self, connection_credentials_no_secrets):
        stdin_pass = "test-client-secret-stdin"

        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.configure_genesys') as mock_configure_genesys, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.is_local_dev') as mock_is_local_dev, \
            patch ('sys.stdin', new=StringIO(stdin_pass)):

            mock_is_local_dev.return_value = True
            configure_platform_customer_care(
                type=PlatformType.GENESYS,
                client_secret=None,
                client_secret_stdin="test-client-secret-stdin",
                **connection_credentials_no_secrets
            )

            mock_configure_genesys.assert_called_once_with(
                GenesysPlatformConnection(
                    app_id=f"{connection_credentials_no_secrets['name']}-{ApplicationPostfix.GENESYS}",
                    client_id=connection_credentials_no_secrets['client_id'],
                    client_secret=stdin_pass, # uses stdin secret value since plaintext secret not passed
                    endpoint=connection_credentials_no_secrets['endpoint'],
                    environment=ConnectionEnvironment.DRAFT
                )
            )

    def test_configure_platform_customer_care_using_genesys_using_both_secret_types(self, connection_credentials_no_secrets):
        stdin_pass = "test-client-secret-stdin"
        plaintext_pass = "test-client-secret"

        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.configure_genesys') as mock_configure_genesys, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.is_local_dev') as mock_is_local_dev, \
            patch ('sys.stdin', new=StringIO(stdin_pass)):

            mock_is_local_dev.return_value = True
            configure_platform_customer_care(
                type=PlatformType.GENESYS,
                client_secret=plaintext_pass,
                client_secret_stdin="test-client-secret-stdin",
                **connection_credentials_no_secrets
            )

            mock_configure_genesys.assert_called_once_with(
                GenesysPlatformConnection(
                    app_id=f"{connection_credentials_no_secrets['name']}-{ApplicationPostfix.GENESYS}",
                    client_id=connection_credentials_no_secrets['client_id'],
                    client_secret=plaintext_pass, # defaults to use plaintext secret even if stdin provided
                    endpoint=connection_credentials_no_secrets['endpoint'],
                    environment=ConnectionEnvironment.DRAFT
                )
            )

class TestConfigureGenesys:
    def test_configure_genesys_draft(self, connection_credentials):
        app_id = f"{connection_credentials['name']}-{ApplicationPostfix.GENESYS}"
        
        mock_connection_client = MockConnectionClient(get_response=None)

        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_get_client, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.add_connection') as mock_add, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.configure_connection') as mock_configure, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.set_credentials_connection') as mock_set_creds, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.is_local_dev') as mock_is_local_dev:

            mock_get_client.return_value = mock_connection_client
            mock_is_local_dev.return_value = False
            genesys_config = GenesysPlatformConnection(
                app_id=app_id,
                client_id=connection_credentials['client_id'],
                client_secret=connection_credentials['client_secret'],
                endpoint=connection_credentials['endpoint'],
                environment=ConnectionEnvironment.DRAFT
            )

            configure_genesys(genesys_config)

            mock_add.assert_called_once_with(app_id=app_id)
            mock_configure.assert_called_once_with(
                app_id=app_id,
                environment=ConnectionEnvironment.DRAFT,
                type=ConnectionPreference.TEAM,
                kind=ConnectionKind.key_value
            )
            mock_set_creds.assert_called_once_with(
                app_id=app_id,
                environment=ConnectionEnvironment.DRAFT,
                endpoint=connection_credentials['endpoint'],
                client_id=connection_credentials['client_id'],
                client_secret=connection_credentials['client_secret']
            )

    def test_configure_genesys_live(self, connection_credentials):
        app_id = f"{connection_credentials['name']}-{ApplicationPostfix.GENESYS}"
        
        mock_connection_client = MockConnectionClient(get_response=None)

        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_get_client, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.add_connection') as mock_add, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.configure_connection') as mock_configure, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.set_credentials_connection') as mock_set_creds, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.is_local_dev') as mock_is_local_dev:

            mock_get_client.return_value = mock_connection_client
            mock_is_local_dev.return_value = True
            genesys_config = GenesysPlatformConnection(
                app_id=app_id,
                client_id=connection_credentials['client_id'],
                client_secret=connection_credentials['client_secret'],
                endpoint=connection_credentials['endpoint'],
                environment=ConnectionEnvironment.LIVE
            )
            
            configure_genesys(genesys_config)

            mock_add.assert_called_once_with(app_id=app_id)
            mock_configure.assert_called_once_with(
                app_id=app_id,
                environment=ConnectionEnvironment.LIVE,
                type=ConnectionPreference.TEAM,
                kind=ConnectionKind.key_value
            )
            mock_set_creds.assert_called_once_with(
                app_id=app_id,
                environment=ConnectionEnvironment.LIVE,
                endpoint=connection_credentials['endpoint'],
                client_id=connection_credentials['client_id'],
                client_secret=connection_credentials['client_secret']
            )

    def test_configure_genesys_existing_connection(self, connection_credentials):
        app_id = f"{connection_credentials['name']}-{ApplicationPostfix.GENESYS}"

        mock_existing_connection = ListConfigsResponse(
            connection_id="connection-1",
            app_id=app_id,
            name=app_id,
            security_scheme=ConnectionSecurityScheme.KEY_VALUE,
            auth_type=None,
            environment=ConnectionEnvironment.DRAFT,
            preference=ConnectionPreference.TEAM,
            credentials_entered=True
        )

        mock_connection_client = MockConnectionClient(get_response=mock_existing_connection)

        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_get_client, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.add_connection') as mock_add, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.configure_connection') as mock_configure, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.set_credentials_connection') as mock_set_creds:

            mock_get_client.return_value = mock_connection_client
            genesys_config = GenesysPlatformConnection(
                app_id=app_id,
                client_id=connection_credentials['client_id'],
                client_secret=connection_credentials['client_secret'],
                endpoint=connection_credentials['endpoint'],
                environment=ConnectionEnvironment.DRAFT
            )

            configure_genesys(genesys_config)

            # Verify add_connection was NOT called since connection already exists
            mock_add.assert_not_called()

            # Verify configure_connection and set_credentials_connection were still called
            mock_configure.assert_called_once_with(
                app_id=app_id,
                environment=ConnectionEnvironment.DRAFT,
                type=ConnectionPreference.TEAM,
                kind=ConnectionKind.key_value
            )
            mock_set_creds.assert_called_once_with(
                app_id=app_id,
                environment=ConnectionEnvironment.DRAFT,
                endpoint=connection_credentials['endpoint'],
                client_id=connection_credentials['client_id'],
                client_secret=connection_credentials['client_secret']
            )

class TestListPlatformCustomerCare:
    def test_list_connections(self, mock_connections):
        mock_connection_client = MockConnectionClient(
            list_response=mock_connections
        )
        
        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_client, \
             patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller._list_connections_formatted') as mock_format:
            
            mock_client.return_value = mock_connection_client
            
            list_platform_customer_care(type=None)
            
            mock_format.assert_called_once()
            call_args = mock_format.call_args
            filtered_connections = call_args[1]['connections']
            
            # Connections without a valid postfix should be filtered out
            assert len(filtered_connections) == 1
            valid_postfixes = {postfix.value for postfix in ApplicationPostfix}
            for conn in filtered_connections:
                assert any(conn.app_id.endswith(postfix) for postfix in valid_postfixes)
    
    def test_list_genesys_connections_filters_non_genesys(self, mock_connections):
        mock_connection_client = MockConnectionClient(
            list_response=mock_connections
        )
        
        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_client, \
             patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller._list_connections_formatted') as mock_format:
            
            mock_client.return_value = mock_connection_client
            
            list_platform_customer_care(type=PlatformType.GENESYS)
            
            mock_format.assert_called_once()
            call_args = mock_format.call_args
            filtered_connections = call_args[1]['connections']
            
            assert len(filtered_connections) == 1
            assert filtered_connections[0].app_id.endswith(ApplicationPostfix.GENESYS)
    
    def test_list_no_connections(self, caplog):
        mock_connection_client = MockConnectionClient(
            list_response=[]
        )
        
        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client
            
            result = list_platform_customer_care(type=PlatformType.GENESYS)
            
            captured = caplog.text
            
            assert result is None
            assert "No customer care platform connections found" in captured
            assert "orchestrate customer-care platform configure" in captured
    
    def test_list_no_platform_connections(self, caplog):
        non_platform_connections = [
            ListConfigsResponse(
                connection_id="connection-1",
                app_id="other-connection",
                name="other-connection",
                security_scheme=ConnectionSecurityScheme.KEY_VALUE,
                auth_type=None,
                environment=ConnectionEnvironment.DRAFT,
                preference=ConnectionPreference.TEAM,
                credentials_entered=True
            )
        ]
        
        mock_connection_client = MockConnectionClient(
            list_response=non_platform_connections
        )
        
        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client
            
            result = list_platform_customer_care(type=PlatformType.GENESYS)
            
            captured = caplog.text
            
            assert result is None
            assert "No customer care platform connections found" in captured
            assert "orchestrate customer-care platform configure" in captured

class TestRemovePlatformCustomerCare:
    
    def test_remove_connection_no_type_single_match(self, connection_credentials):
        app_id = f"{connection_credentials['name']}-{ApplicationPostfix.GENESYS}"
        
        mock_connections = [
            ListConfigsResponse(
                connection_id="connection-1",
                app_id=app_id,
                name=app_id,
                security_scheme=ConnectionSecurityScheme.KEY_VALUE,
                auth_type=None,
                environment=ConnectionEnvironment.DRAFT,
                preference=ConnectionPreference.TEAM,
                credentials_entered=True
            )
        ]

        mock_connection_client = MockConnectionClient(list_response=mock_connections)
        
        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.remove_connection') as mock_remove, \
             patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_client:
            
            mock_client.return_value = mock_connection_client
            
            remove_platform_customer_care(
                type=None,
                name=connection_credentials['name']
            )
            
            mock_remove.assert_called_once_with(app_id=app_id)

    def test_remove_connection_no_type_no_match(self, connection_credentials):
        mock_connection_client = MockConnectionClient(list_response=[])

        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_client:
            mock_client.return_value = mock_connection_client

            with pytest.raises(BadRequest) as e:
                remove_platform_customer_care(
                    type=None,
                    name=connection_credentials['name']
                )

            assert f"No connection found with name '{connection_credentials['name']}'" in str(e.value)

    def test_remove_genesys_connection(self, connection_credentials):
        app_id = f"{connection_credentials['name']}-{ApplicationPostfix.GENESYS}"

        mock_connection_client = MockConnectionClient(list_response=mock_connections)

        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_client, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.remove_connection') as mock_remove:

            mock_client.return_value = mock_connection_client

            remove_platform_customer_care(
                type=PlatformType.GENESYS,
                name=connection_credentials['name']
            )

            mock_remove.assert_called_once_with(app_id=app_id)
    
    def test_remove_connection_genesys_live_and_draft(self, connection_credentials):
        app_id = f"{connection_credentials['name']}-{ApplicationPostfix.GENESYS}"

        mock_connections = [
            ListConfigsResponse(
                connection_id="connection-1",
                app_id=app_id,
                name=app_id,
                security_scheme=ConnectionSecurityScheme.KEY_VALUE,
                auth_type=None,
                environment=ConnectionEnvironment.DRAFT,
                preference=ConnectionPreference.TEAM,
                credentials_entered=True
            ),
            ListConfigsResponse(
                connection_id="connection-2",
                app_id=app_id,
                name=app_id,
                security_scheme=ConnectionSecurityScheme.KEY_VALUE,
                auth_type=None,
                environment=ConnectionEnvironment.LIVE,
                preference=ConnectionPreference.TEAM,
                credentials_entered=True
            )
        ]

        mock_connection_client = MockConnectionClient(list_response=mock_connections)
        with patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.get_connections_client') as mock_client, \
            patch('ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller.remove_connection') as mock_remove:
                mock_client.return_value = mock_connection_client

                remove_platform_customer_care(
                    type=PlatformType.GENESYS,
                    name=connection_credentials['name']
                )
                
                # Should not throw an error since these are the live and draft of the same connection
                mock_remove.assert_called_once_with(app_id=app_id)
    