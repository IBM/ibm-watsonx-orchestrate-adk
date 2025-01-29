from unittest.mock import patch

import pytest
import requests
import typer

from ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller \
    import create_application_connection, delete_application_connection
from ibm_watsonx_orchestrate.cli.commands.connections.application.types import ApplicationConnectionType
from ibm_watsonx_orchestrate.client.connections import CreateBasicAuthConnection, ConnectionType, BasicAuthCredentials, \
    BearerTokenAuthCredentials, CreateBearerTokenAuthConnection, CreateOAuth2AuthCodeConnection, \
    OAuth2AuthCodeCredentials, CreateOAuth2ImplicitConnection, OAuth2ImplicitCredentials, \
    CreateOAuth2PasswordConnection, OAuth2PasswordCredentials, OAuth2ClientCredentials, \
    CreateOAuth2ClientCredentialsConnection, CreateConnectionResponse
from mocks.mock_base_api import get_application_connections_mock as _get_application_connections_mock, \
    instantiate_client_mock
from utils.matcher import MatchesObjectContaining


def get_application_connections_mock():
    Mock, create, delete = _get_application_connections_mock()
    create.return_value = CreateConnectionResponse(status='success')
    return Mock, create, delete


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_create_basic_auth():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
        'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
        ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.basic,
            username='username',
            password='password',
            shared=True
        )
        create.assert_called_once_with(
            connection=CreateBasicAuthConnection(
                appid='app_id',
                connection_type=ConnectionType.BASIC_AUTH,
                credentials=BasicAuthCredentials(username='username', password='password'),
                shared=True
            )
        )


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_fail_basic_auth_if_username_missing():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
        'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
        ApplicationConnectionsClientMock
    ):
        try:
            create_application_connection(
                app_id='app_id',
                type=ApplicationConnectionType.basic,
                password='password',
                shared=True
            )
            assert False, 'Should have raised exception'
        except typer.BadParameter as e:
            assert e.message == 'Missing flags --username (-u) and --password (-p) are both required for type basic'


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_fail_basic_auth_if_password_missing():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        try:
            create_application_connection(
                app_id='app_id',
                type=ApplicationConnectionType.basic,
                username='password',
                shared=True
            )
            assert False, 'Should have raised exception'
        except typer.BadParameter as e:
            assert e.message == 'Missing flags --username (-u) and --password (-p) are both required for type basic'


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_create_bearer_auth():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
        'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
        ApplicationConnectionsClientMock
    ):
        ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.bearer,
            token='token',
            shared=True
        )
        create.assert_called_once_with(
            connection=CreateBearerTokenAuthConnection(
                appid='app_id',
                connection_type=ConnectionType.BEARER_TOKEN,
                credentials=BearerTokenAuthCredentials(token='token'),
                shared=True
            )
        )



@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_create_oauth_code_flow():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
        'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
        ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.oauth_auth_code_flow,
            client_id='id',
            client_secret='supersecret',
            well_known_url='https://example.com',
            shared=True
        )
        create.assert_called_once_with(
            connection=CreateOAuth2AuthCodeConnection(
                appid='app_id',
                connection_type=ConnectionType.OAUTH2_AUTH_CODE,
                credentials=OAuth2AuthCodeCredentials(client_id='id', client_secret='supersecret', well_known_url='https://example.com'),
                shared=True
            )
        )


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_create_oauth_implicit_flow():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.oauth_auth_implicit_flow,
            client_id='id',
            client_secret='supersecret',
            well_known_url='https://example.com',
            shared=True
        )
        create.assert_called_once_with(
            connection=CreateOAuth2ImplicitConnection(
                appid='app_id',
                connection_type=ConnectionType.OAUTH2_IMPLICIT,
                credentials=OAuth2ImplicitCredentials(client_id='id', client_secret='supersecret', well_known_url='https://example.com'),
                shared=True
            )
        )


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_create_oauth_password_flow():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.oauth_auth_password_flow,
            client_id='id',
            client_secret='supersecret',
            well_known_url='https://example.com',
            username='username',
            password='password',
            shared=True
        )
        create.assert_called_once_with(
            connection=CreateOAuth2PasswordConnection(
                appid='app_id',
                connection_type=ConnectionType.OAUTH2_PASSWORD,
                credentials=OAuth2PasswordCredentials(client_id='id', client_secret='supersecret', well_known_url='https://example.com', username='username', password='password'),
                shared=True
            )
        )


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_create_oauth_client_credentials_flow():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.oauth_auth_client_credentials_flow,
            client_id='id',
            client_secret='supersecret',
            well_known_url='https://example.com',
            shared=True
        )
        create.assert_called_once_with(
            connection=CreateOAuth2ClientCredentialsConnection(
                appid='app_id',
                connection_type=ConnectionType.OAUTH2_CLIENT_CREDS,
                credentials=OAuth2ClientCredentials(client_id='id', client_secret='supersecret', well_known_url='https://example.com'),
                shared=True
            )
        )


@pytest.fixture(params=[
    ApplicationConnectionType.oauth_auth_code_flow,
    ApplicationConnectionType.oauth_auth_implicit_flow,
    ApplicationConnectionType.oauth_auth_password_flow,
    ApplicationConnectionType.oauth_auth_client_credentials_flow
])
def oauth_type(request):
    return request.param, {
        'username': 'username',
        'password': 'password'
    } if request.param == ApplicationConnectionType.oauth_auth_password_flow else {}


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_fail_oauth_flow_with_missing_client_id(oauth_type):
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    auth_type, additional_credentials = oauth_type
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        try:

            create_application_connection(
                app_id='app_id',
                type=auth_type,
                client_secret='supersecret',
                well_known_url='https://example.com',
                shared=True,
                **additional_credentials
            )
            assert False, 'Should have thrown'
        except typer.BadParameter as e:
            assert e.message == f"Missing flags --client-id is required for type {str(auth_type)}"


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_fail_oauth_flow_with_missing_client_secret(oauth_type):
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    auth_type, additional_credentials = oauth_type
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        try:

            create_application_connection(
                app_id='app_id',
                type=auth_type,
                client_id='id',
                well_known_url='https://example.com',
                shared=True,
                **additional_credentials
            )
            assert False, 'Should have thrown'
        except typer.BadParameter as e:
            assert e.message == f"Missing flags --client-secret is required for type {str(auth_type)}"



@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_fail_oauth_flow_with_missing_well_known_url(oauth_type):
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    auth_type, additional_credentials = oauth_type
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        try:

            create_application_connection(
                app_id='app_id',
                type=auth_type,
                client_id='id',
                client_secret='supersecret',
                shared=True,
                **additional_credentials
            )
            assert False, 'Should have thrown'
        except typer.BadParameter as e:
            assert e.message == f"Missing flags --well-known-url is required for type {str(auth_type)}"


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_fail_oauth_auth_password_flow_with_missing_username():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        try:

            create_application_connection(
                app_id='app_id',
                type=ApplicationConnectionType.oauth_auth_password_flow,
                client_id='id',
                client_secret='supersecret',
                well_known_url='https://example.com',
                password='password',
                shared=True
            )
            assert False, 'Should have thrown'
        except typer.BadParameter as e:
            assert e.message == f"Missing flags --username (-u) and --password (-p) are both required for type {str(ApplicationConnectionType.oauth_auth_password_flow)}"


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_fail_oauth_auth_password_flow_with_missing_password():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        try:

            create_application_connection(
                app_id='app_id',
                type=ApplicationConnectionType.oauth_auth_password_flow,
                client_id='id',
                client_secret='supersecret',
                well_known_url='https://example.com',
                username='username',
                shared=True
            )
            assert False, 'Should have thrown'
        except typer.BadParameter as e:
            assert e.message == f"Missing flags --username (-u) and --password (-p) are both required for type {str(ApplicationConnectionType.oauth_auth_password_flow)}"


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_create_shared_connection():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.basic,
            username='username',
            password='password',
            shared=True
        )
        create.assert_called_once_with(
            connection=MatchesObjectContaining(
                shared=True
            )
        )




@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_should_create_private_connection():
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.basic,
            username='username',
            password='password',
            shared=False
        )
        create.assert_called_once_with(
            connection=MatchesObjectContaining(
                shared=False
            )
        )


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_create_message_should_print_success_message(capsys):
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.basic,
            username='username',
            password='password',
            shared=True
        )
        captured = capsys.readouterr()
        assert captured.out == "Successfully created application connection with app_id: app_id\n"


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_create_message_should_print_redirect_url(capsys):
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    create.return_value = CreateConnectionResponse(status='redirect', authorization_url='https://auth-url')
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        create_application_connection(
            app_id='app_id',
            type=ApplicationConnectionType.basic,
            username='username',
            password='password',
            shared=True
        )
        captured = capsys.readouterr()
        assert captured.out == "Please go to the following url to complete the OAuth2 flow:\nhttps://auth-url\n"


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_create_connection_should_fail_if_create_connection_call_fails(capsys):
    ApplicationConnectionsClientMock, create, _ = get_application_connections_mock()
    resp = requests.Response()
    resp.status_code = 400
    setattr(resp, '_content', '{"detail": "boom"}'.encode('utf-8'))
    create.side_effect = requests.HTTPError(response=resp)
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        with pytest.raises(SystemExit) as e:
            create_application_connection(
                app_id='app_id',
                type=ApplicationConnectionType.basic,
                username='username',
                password='password',
                shared=True
            )
            create.assert_called_once_with(
                connection=CreateBasicAuthConnection(
                    appid='app_id',
                    connection_type=ConnectionType.BASIC_AUTH,
                    credentials=BasicAuthCredentials(username='username', password='password'),
                    shared=True
                )
            )
        captured = capsys.readouterr()
        assert captured.err == "boom\n"
        assert e.value.code == 1




@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_delete_connection_should_delete_connection():
    ApplicationConnectionsClientMock, _, delete = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        delete_application_connection(
            app_id='app_id'
        )
        delete.assert_called_once_with(app_id='app_id')


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_delete_connection_should_print_success_message(capsys):
    ApplicationConnectionsClientMock, _, delete = get_application_connections_mock()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        delete_application_connection(
            app_id='app_id'
        )
        captured = capsys.readouterr()
        assert captured.out == "Successfully deleted application connection with app_id: app_id\n"


@patch(
    'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.instantiate_client',
    instantiate_client_mock
)
def test_delete_connection_should_fail_if_delete_connection_call_fails(capsys):
    ApplicationConnectionsClientMock, _, delete = get_application_connections_mock()
    resp = requests.Response()
    resp.status_code = 400
    setattr(resp, '_content', '{"detail": "boom"}'.encode('utf-8'))
    delete.side_effect = requests.HTTPError(response=resp)
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_controller.ApplicationConnectionsClient',
            ApplicationConnectionsClientMock
    ):
        with pytest.raises(SystemExit) as e:
            delete_application_connection(
                app_id='app_id'
            )
            captured = capsys.readouterr()
            assert captured.out == "boom\n"
        assert e.value.code == 1


