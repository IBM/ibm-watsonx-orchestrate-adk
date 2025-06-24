import typer
from typing_extensions import Annotated, List
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionEnvironment, ConnectionPreference, ConnectionKind
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import (
    add_connection,
    remove_connection,
    list_connections,
    import_connection,
    configure_connection,
    set_credentials_connection,
    set_identity_provider_connection
)

connections_app = typer.Typer(no_args_is_help=True)

@connections_app.command(name="add")
def add_connection_command(
    app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id of the connection you wish to create. This value will be used to uniquely reference this connection when associating the connection with tools or agents'
        )
    ]
):
    add_connection(app_id=app_id)

@connections_app.command(name="remove")
def remove_connection_command(
    app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id of the connection you wish to remove. This will also remove the configuration and credentials associated with the provided app id.'
        )
    ]
):
    remove_connection(app_id=app_id)

@connections_app.command(name="list")
def list_connections_command(
    environment: Annotated[
        ConnectionEnvironment, typer.Option(
            '--environment', '--env',
            help='Optionally limit the connections you want to see to only those of a certain environment'
        )
    ] = None,
    verbose: Annotated[
        bool, typer.Option(
            '--verbose', '-v',
            help='List the connections in json format without table styling'
        )
    ] = None
):
    list_connections(environment=environment, verbose=verbose)

@connections_app.command(name="import")
def import_connection_command(
    file: Annotated[
        str, typer.Option(
            '--file', '-f',
            help='Path to a spec file containing the connection details'
        )
    ]
):
    import_connection(file=file)

@connections_app.command(name="configure")
def configure_connection_command(
    app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id you want to configure'
        )
    ],
    environment: Annotated[
        ConnectionEnvironment, typer.Option(
            '--environment', '--env',
            help='The environment you want to configure'
        )
    ],
    type: Annotated[
        ConnectionPreference, typer.Option(
            '--type', '-t',
            help='The type of credentials. `--type team` will mean the credentials apply to all users, `--type member` will mean each user will have to provide their own credentials'
        )
    ],
    kind: Annotated[
        ConnectionKind, typer.Option(
            '--kind', '-k',
            help='The kind of credentials the connection will use.'
        )
    ],
    server_url: Annotated[
        str, typer.Option(
            '--server-url', '--url', '-u',
            help='The url the connection is going to be used access.'
        )
    ] = None,
    sso: Annotated[
        bool, typer.Option(
            '--sso', '-s',
            help='Does the OAuth require a SAML provider. Only applicable to OAuth kinds'
        )
    ] = False,
    idp_token_use: Annotated[
        str, typer.Option(
            '--idp-token-use',
            help='The OAuth token use for the identity provider. Only applicable to OAuth kinds with sso'
        )
    ] = None,
    idp_token_type: Annotated[
        str, typer.Option(
            '--idp-token-type',
            help='The OAuth token type for the identity provider. Only applicable to OAuth kinds with sso'
        )
    ] = None,
    idp_token_header: Annotated[
        List[str], typer.Option(
            '--idp-token-header',
            help='Header values for the identity provider token request. Defaults to using `content-type: application/x-www-form-urlencoded`.  Multiple can be set using `--idp-token-header "content-type: application/x-www-form-urlencoded" --idp-token-header "encoding:..."` . Only applicable to OAuth kinds with sso'
        )
    ] = None,
    app_token_header: Annotated[
        List[str], typer.Option(
            '--app-token-header',
            help='Header values for the app token request. Defaults to using `content-type: application/x-www-form-urlencoded`.  Multiple can be set using `--app-token-header "content-type: application/x-www-form-urlencoded" --app-token-header "encoding:..."` . Only applicable to OAuth kinds with sso'
        )
    ] = None,
    
):
    configure_connection(
        app_id=app_id,
        environment=environment,
        type=type,
        kind=kind,
        server_url=server_url,
        sso=sso,
        idp_token_use=idp_token_use,
        idp_token_type=idp_token_type,
        idp_token_header=idp_token_header,
        app_token_header=app_token_header
    )

@connections_app.command(name="set-credentials")
def set_credentials_connection_command(

   app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id you want to configure'
        )
    ],
    environment: Annotated[
        ConnectionEnvironment, typer.Option(
            '--environment', '--env',
            help='The environment you want to configure'
        )
    ],
    username: Annotated[
        str,
        typer.Option(
            '--username',
            '-u',
            help='For basic auth, the username to login with'
        )
    ] = None,
    password: Annotated[
        str,
        typer.Option(
            '--password',
            '-p',
            help='For basic auth, the password to login with'
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
            # help='For oauth_auth_on_behalf_of_flow, oauth_auth_code_flow, oauth_auth_implicit_flow, oauth_auth_password_flow and oauth_auth_client_credentials_flow, the client_id to authenticate against the application token server'
            help='For oauth_auth_on_behalf_of_flow and oauth_auth_client_credentials_flow, the client_id to authenticate against the application token server'
        )
    ] = None,
    client_secret: Annotated[
        str,
        typer.Option(
            '--client-secret',
            help='For oauth_auth_client_credentials_flow, the client_secret to authenticate with'
        )
    ] = None,
    token_url: Annotated[
        str,
        typer.Option(
            '--token-url',
            # help='For oauth_auth_on_behalf_of_flow, oauth_auth_code_flow, oauth_auth_password_flow and oauth_auth_client_credentials_flow, the url of the application token server'
            help='For oauth_auth_on_behalf_of_flow and oauth_auth_client_credentials_flow, the url of the application token server'
        )
    ] = None,
    auth_url: Annotated[
        str,
        typer.Option(
            '--auth-url',
            help='For oauth_auth_code_flow, the url of the application token server'
        )
    ] = None,
    grant_type: Annotated[
        str,
        typer.Option(
            '--grant-type',
            help='For oauth_auth_on_behalf_of_flow, the grant type used by the application token server'
        )
    ] = None,
    scopes: Annotated[
        List[str],
        typer.Option(
            '--scopes',
            help='For oauth_auth_code_flow and oauth_auth_client_credentials_flow, the optional scopes used by the application token server'
        )
    ] = None,
    entries: Annotated[
        List[str],
        typer.Option(
            '--entries', "-e",
            help="For key_value, a key value pair in the form '<key>=<value>'. Multiple values can be passed using `-e key1=value1 -e key2=value2`"
        )
    ] = None,
):
    set_credentials_connection(
        app_id=app_id,
        environment=environment,
        username=username,
        password=password,
        token=token,
        api_key=api_key,
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
        auth_url=auth_url,
        grant_type=grant_type,
        scopes=scopes,
        entries=entries
    )

@connections_app.command(name="set-identity-provider")
def set_identity_provider_connection_command(

   app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id you want to configure'
        )
    ],
    environment: Annotated[
        ConnectionEnvironment, typer.Option(
            '--environment', '--env',
            help='The environment you want to configure'
        )
    ],
    url: Annotated[
        str, typer.Option(
            '--url', '-u',
            help='The token url of the identity provider'
        )
    ],
    client_id: Annotated[
        str,
        typer.Option(
            '--client-id',
            help='The client_id to authenticate with the identity provider'
        )
    ],
    client_secret: Annotated[
        str,
        typer.Option(
            '--client-secret',
            help='The client_secret to authenticate with the identity provider'
        )
    ],
    scope: Annotated[
        str,
        typer.Option(
            '--scope',
            help='The scope of the identity provider'
        )
    ],
    grant_type: Annotated[
        str,
        typer.Option(
            '--grant-type',
            help='The grant-type of the the identity provider'
        )
    ],
):
    set_identity_provider_connection(
        app_id=app_id,
        environment=environment,
        url=url,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        grant_type=grant_type
    )