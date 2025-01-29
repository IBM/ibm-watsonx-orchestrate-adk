import asyncio

import typer
from typing_extensions import Annotated

from .connections_application_controller import create_application_connection, delete_application_connection
from .types import ApplicationConnectionType

connections_application_app = typer.Typer(no_args_is_help=True)



@connections_application_app.command(
    name="create",
    help='Creates a connection (credential binding) to an external application for use in, for example, an openapi tool'
)
def create_application_connection_command(
        type: Annotated[
            ApplicationConnectionType,
            typer.Option(
                "--type",
                "-t",
                help="The type of connection/ credential to create."
            )
        ],
        app_id: Annotated[
            str,
            typer.Option(
                '--app-id',
                '-a',
                help='The app_id to use to reference this connection when importing an openapi tool'
            )
        ],
        username: Annotated[
            str,
            typer.Option(
                '--username',
                '-u',
                help='For basic auth or oauth_auth_password_flow, the username to login with'
            )
        ] = None,
        password: Annotated[
            str,
            typer.Option(
                '--password',
                '-p',
                help='For basic auth or oauth_auth_password_flow, the password to login with'
            )
        ] = None,
        token: Annotated[
            str,
            typer.Option(
                '--token',
                help='For bearer auth, the bearer token to use'
            )
        ] = None,
        api_key: Annotated[
            str,
            typer.Option(
                '--api-key',
                '-k',
                help='For api_key auth, the api key to use'
            )
        ] = None,
        client_id: Annotated[
            str,
            typer.Option(
                '--client-id',
                help='For oauth_auth_code_flow, oauth_auth_implicit_flow, oauth_auth_password_flow, oauth_auth_client_credentials_flow, the client_id to authenticate with'
            )
        ] = None,
        client_secret: Annotated[
            str,
            typer.Option(
                '--client-secret',
                help='For oauth_auth_code_flow, oauth_auth_implicit_flow, oauth_auth_password_flow, oauth_auth_client_credentials_flow, the client_secret to authenticate with'
            )
        ] = None,
        scope: Annotated[
            str,
            typer.Option(
                '--scope',
                help="For oauth_auth_code_flow, oauth_auth_implicit_flow, oauth_auth_password_flow, oauth_auth_client_credentials_flow, the scopes used to authenticate against the openapi endpoint. Default to \"openid email profile\""
            )
        ] = None,
        well_known_url: Annotated[
            str,
            typer.Option(
                '--well-known-url',
                help='For oauth_auth_code_flow, oauth_auth_implicit_flow, oauth_auth_password_flow, oauth_auth_client_credentials_flow, the well_known_url to authenticate with'
            )
        ] = None,
        shared: Annotated[
            bool,
            typer.Option(
                '--shared',
                help='Should this secret be shared'
            )
        ] = False
):
    create_application_connection(
        type=type,
        app_id=app_id,
        username=username,
        password=password,
        token=token,
        api_key=api_key,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        well_known_url=well_known_url,
        shared=shared
    )


@connections_application_app.command(
    name="delete",
    help='Deletes a connection (credential binding) to an external application for use in, for example, an openapi tool'
)
def delete_application_connection_command(
        app_id: Annotated[
            str,
            typer.Option('--app-id', '-a', help='The app_id to use to reference this connection when importing an openapi tool')
        ]
):
    delete_application_connection(app_id=app_id)

