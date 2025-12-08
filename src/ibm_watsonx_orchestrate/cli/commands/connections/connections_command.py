import typer
from typing_extensions import Annotated, List
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionEnvironment, ConnectionPreference, ConnectionKind, ConnectionCredentialsEntry, ConnectionSendVia
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import (
    add_connection,
    remove_connection,
    list_connections,
    import_connection,
    export_connection,
    configure_connection,
    set_credentials_connection,
    set_identity_provider_connection,
    token_entry_connection_credentials_parse,
    auth_entry_connection_credentials_parse
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

@connections_app.command(name="export")
def export_connection_command(
    app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id of the connection you wish to export.'
        )
    ],
    output_file: Annotated[
        str, typer.Option(
            '--output', '-o',
            help='Path to where the exported connection should be saved.'
        )
    ]
):
    export_connection(app_id=app_id, output_file=output_file)

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
            help='For basic auth and oauth_auth_password_flow, the username to login with'
        )
    ] = None,
    password: Annotated[
        str,
        typer.Option(
            '--password',
            '-p',
            help='For basic auth and oauth_auth_password_flow, the password to login with'
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
            help='For oauth_auth_on_behalf_of_flow, oauth_auth_password_flow, oauth_auth_token_exchange_flow and oauth_auth_client_credentials_flow, the client_id to authenticate against the application token server'
        )
    ] = None,
    client_secret: Annotated[
        str,
        typer.Option(
            '--client-secret',
            help='For oauth_auth_client_credentials_flow and oauth_auth_password_flow, the client_secret to authenticate with'
        )
    ] = None,
    send_via: Annotated[
        ConnectionSendVia,
        typer.Option(
            '--send-via',
            help='For oauth_auth_client_credentials_flow, how the token will be sent to the server. Defaults to using `header`'
        )
    ] = None,
    token_url: Annotated[
        str,
        typer.Option(
            '--token-url',
            # help='For oauth_auth_on_behalf_of_flow, oauth_auth_code_flow, oauth_auth_password_flow and oauth_auth_client_credentials_flow, the url of the application token server'
            help='For oauth_auth_on_behalf_of_flow, oauth_auth_password_flow, oauth_auth_token_exchange_flow and oauth_auth_client_credentials_flow, the url of the application token server'
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
            help='For oauth_auth_on_behalf_of_flow, oauth_auth_password_flow, oauth_auth_token_exchange_flow and oauth_auth_client_credentials_flow, the grant type used by the application token server'
        )
    ] = None,
    scope: Annotated[
        str,
        typer.Option(
            '--scope',
            help='For oauth_auth_code_flow, oauth_auth_password_flow and oauth_auth_client_credentials_flow, the optional scopes used by the application token server. Should be in the form of a space seperated string.'
        )
    ] = None,
    entries: Annotated[
        List[str],
        typer.Option(
            '--entries', "-e",
            help="For key_value, a key value pair in the form '<key>=<value>'. Multiple values can be passed using `-e key1=value1 -e key2=value2`"
        )
    ] = None,
    token_entries: Annotated[
        List[ConnectionCredentialsEntry],
        typer.Option(
            '--token-entries', "-t",
            parser=token_entry_connection_credentials_parse,
            help="Custom field options for oauth types token request, a key value location option in the form 'location:<key>=<value>' or '<key>=<value>' with location defaulting to 'header'. Multiple values can be passed using `-t key1=value1 -t location:key2=value2`"
        )
    ] = None,
    auth_entries: Annotated[
        List[ConnectionCredentialsEntry],
        typer.Option(
            '--auth-entries',
            parser=auth_entry_connection_credentials_parse,
            help="Custom field options for oauth_auth_code_flow auth server request, a key value location option in the form 'location:<key>=<value>' or '<key>=<value>' with location defaulting to 'query'. Note only 'query' is a valid location. Multiple values can be passed using `--auth-entries key1=value1 --auth-entries location:key2=value2`"
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
        send_via=send_via,
        token_url=token_url,
        auth_url=auth_url,
        grant_type=grant_type,
        scope=scope,
        entries=entries,
        token_entries=token_entries,
        auth_entries=auth_entries
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
    token_entries: Annotated[
        List[ConnectionCredentialsEntry],
        typer.Option(
            '--token-entries', "-t",
            parser=token_entry_connection_credentials_parse,
            help="Custom field options for oauth types token request, a key value location option in the form 'location:<key>=<value>' or '<key>=<value>' with location defaulting to 'header'. Multiple values can be passed using `-t key1=value1 -t location:key2=value2`"
        )
    ] = None,
):
    set_identity_provider_connection(
        app_id=app_id,
        environment=environment,
        url=url,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        grant_type=grant_type,
        token_entries=token_entries
    )