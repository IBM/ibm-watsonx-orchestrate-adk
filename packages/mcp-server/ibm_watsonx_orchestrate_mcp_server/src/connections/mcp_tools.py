
from typing import Any, Literal, List

from ibm_watsonx_orchestrate.cli.commands.connections import connections_controller
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionsListResponse
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call
from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path
from ibm_watsonx_orchestrate_mcp_server.src.connections.types import ConfigureConnectionsOptions, SetCredentialsConnectionOptions, SetIdentityProviderOptions


def list_connections(verbose: bool=False) -> ConnectionsListResponse | List[dict[str, Any]]:
    """
    Lists the avalible connections available on the watsonx Orchestrate platform.

    Args:
        verbose (bool): If True then the connections will be returned in a verbose format. Defaults to False.
    
    Returns:
        dict[str, Any]: A dictionary containing the connections.
    """

    format: Literal[ListFormats.JSON] | None = ListFormats.JSON if not verbose else None
    connections: ConnectionsListResponse | List[dict] = silent_call(fn=connections_controller.list_connections, environment=None, verbose=verbose, format=format)
    return connections

def create_connection(app_id: str) -> str:
    """
    Creates a connection in the watsonx Orchestrate platform.

    Args:
        app_id (str): An arbitrary string that will be used to identify the connection.

    Returns:
        str: A success message indicating the connection was created successfully.
    """

    silent_call(fn=connections_controller.add_connection, app_id=app_id)
    return f"Connection '{app_id}' created successfully."

def remove_connection(app_id: str) -> str:
    """
    Removes a connection from the watsonx Orchestrate platform. 

    Args:
        app_id (str): The app id of the connection to remove.

    Returns:
        str: A success message indicating the connection was removed successfully.
    """
    silent_call(fn=connections_controller.remove_connection, app_id=app_id)
    return f"Connection '{app_id}' removed successfully."

def import_connection(file_path: str) -> str:
    """
    Imports connections from a spec file into the watsonx Orchestrate platform.

    Args:
        file_path (str): The path to the connections spec file.

    Returns:
        str: A success message indicating the connections were imported successfully.
    """
    working_directory_file_path: str = get_working_directory_path(file_path)
    silent_call(fn=connections_controller.import_connection, file=working_directory_file_path)
    return f"Connection imported successfully from '{file_path}'."

def configure_connection(options: ConfigureConnectionsOptions) -> str:
    """
    Configures a connection for a certain environment in the watsonx Orchestrate platform.

    Args:
        options (ConfigureConnectionsOptions): The options for configuring the connection.

    Returns:
        str: A success message indicating the connection was configured successfully.
    """
    silent_call(
        fn=connections_controller.configure_connection,
        app_id=options.app_id,
        environment=options.environment,
        type=options.type,
        kind=options.kind,
        server_url=options.server_url,
        sso=options.sso,
        idp_token_use=options.idp_token_use,
        idp_token_type=options.idp_token_type,
        idp_token_header=options.idp_token_header,
        app_token_header=options.app_token_header,
    )
    return f"Connection '{options.app_id}' configured successfully."

def set_credentials_connection(options: SetCredentialsConnectionOptions) -> str:
    """
    Sets the credentials for a connection in the watsonx Orchestrate platform.
    Args:
        options (SetCredentialsConnectionOptions): The options for setting the credentials for the connection.
    Returns:
        str: A success message indicating the credentials were correctly set.
    """
    scope: str | None = " ".join(options.scope) if options.scope else None
    entries: List[str] | None = [f"{k}={v}" for k, v in options.entries.items()] if options.entries else None

    silent_call(
        fn=connections_controller.set_credentials_connection,
        app_id=options.app_id,
        environment=options.environment,
        username=options.username,
        password=options.password,
        token=options.token,
        api_key=options.api_key,
        client_id=options.client_id,
        client_secret=options.client_secret,
        send_via=options.send_via,
        token_url=options.token_url,
        auth_url=options.auth_url,
        grant_type=options.grant_type,
        scope=scope,
        entries=entries,
        token_entries=options.token_entries,
        auth_entries=options.auth_entries
    )
    return f"Credentials set for connection '{options.app_id}'"

def set_identity_provider(options: SetIdentityProviderOptions) -> str:
    """
    Set the identity provider for a connection for sso enabled auth flow.

    Args:
        options (SetIdentityProviderOptions): The options for setting an identity provider for a connection
    
    Returns:
        str: A success message indicating the identity provider was correctly set.
    """
    silent_call(
        fn=connections_controller.set_identity_provider_connection,
        app_id=options.app_id,
        environment=options.environment,
        url=options.url,
        client_id=options.client_id,
        client_secret=options.client_secret,
        scope=options.scope,
        grant_type=options.grant_type,
        token_entries=options.token_entries
    )

    return f"Identity Provider set for connection '{options.app_id}'"

__tools__ = [list_connections, create_connection, remove_connection, import_connection, configure_connection, set_credentials_connection, set_identity_provider]