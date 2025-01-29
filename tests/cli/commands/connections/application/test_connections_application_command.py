from unittest.mock import patch
from ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_command \
    import create_application_connection_command, delete_application_connection_command


def test_create_application_connection_command(capsys):
    with patch("ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_command.create_application_connection") as mock:
        create_application_connection_command(
            type='basic',
            app_id='app_id',
            username='username',
            password='password',
            token='token',
            api_key='api_key',
            client_id='client_id',
            scope='email',
            client_secret='client_secret',
            well_known_url='well_known_url',
            shared=True
        )
        mock.assert_called_once_with(
            type='basic',
            app_id='app_id',
            username='username',
            password='password',
            token='token',
            scope='email',
            api_key='api_key',
            client_id='client_id',
            client_secret='client_secret',
            well_known_url='well_known_url',
            shared=True
        )


def test_delete_application_connection_command(capsys):
    with patch("ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_command.delete_application_connection") as mock:
        delete_application_connection_command(
            app_id='app_id'
        )
        mock.assert_called_once_with(
            app_id='app_id',
        )