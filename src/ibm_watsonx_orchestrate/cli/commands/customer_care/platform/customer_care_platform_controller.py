import logging
import sys
from typing import Optional

from ibm_watsonx_orchestrate.agent_builder.connections.types import (
    ConnectionEnvironment,
    ConnectionKind,
    ConnectionPreference,
    ConnectionsListResponse
)
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import (
    add_connection,
    configure_connection,
    remove_connection,
    set_credentials_connection,
    _list_connections_formatted
)
from ibm_watsonx_orchestrate.cli.commands.customer_care.platform.types import (
    ApplicationPostfix,
    GenesysPlatformConnection,
    PlatformType
)
from ibm_watsonx_orchestrate.client.connections.utils import get_connections_client
from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)

def configure_platform_customer_care(type: PlatformType, name: str, client_id: Optional[str], client_secret: Optional[str], client_secret_stdin: Optional[str], endpoint: Optional[str]) -> None:
    # Use plaintext secret if provided, otherwise use stdin
    secret_value = client_secret
    if secret_value is None and client_secret_stdin is not None:
        secret_value = sys.stdin.read().strip()

    match(type):
        case PlatformType.GENESYS:
            app_id = name + "-" + ApplicationPostfix.GENESYS
            genesys_conn_draft = GenesysPlatformConnection(
                app_id=app_id,
                client_id=client_id,
                client_secret=secret_value,
                endpoint=endpoint,
                environment=ConnectionEnvironment.DRAFT
            )
            configure_genesys(genesys_conn_draft)
            if is_local_dev() == False:
                genesys_conn_live = GenesysPlatformConnection(
                    app_id=app_id,
                    client_id=client_id,
                    client_secret=secret_value,
                    endpoint=endpoint,
                    environment=ConnectionEnvironment.LIVE
                )
                configure_genesys(genesys_conn_live)

def configure_genesys(config: GenesysPlatformConnection) -> None:
    client = get_connections_client()
    existing_app = client.get(app_id=config.app_id)
    if not existing_app:
        add_connection(app_id=config.app_id)

    configure_connection(app_id=config.app_id, environment=config.environment, type=ConnectionPreference.TEAM, kind=ConnectionKind.key_value)
    set_credentials_connection(app_id=config.app_id, environment=config.environment, entries=config.get_entries())

def list_platform_customer_care(type: Optional[PlatformType]) -> ConnectionsListResponse | None:
    client = get_connections_client()
    connections = client.list()

    match(type):
        case PlatformType.GENESYS:
            valid_postfixes = [ApplicationPostfix.GENESYS.value]
        case _:
            valid_postfixes = [postfix.value for postfix in ApplicationPostfix]


    filtered_connections = [
        conn for conn in connections
        if any(conn.app_id.endswith(postfix) for postfix in valid_postfixes)
    ]

    if (len(filtered_connections) == 0):
        logger.info(f"No customer care platform connections found. You can create connections using `orchestrate customer-care platform configure`")
    else:
        return _list_connections_formatted(connections=filtered_connections, environment=None, format=None)

def remove_platform_customer_care(type: Optional[PlatformType], name: str) -> None:
    client = get_connections_client()
    if any(name.endswith(postfix.value) for postfix in ApplicationPostfix):
        remove_connection(app_id=name)
    elif (type == PlatformType.GENESYS):
        app_id = name + "-" + ApplicationPostfix.GENESYS
        remove_connection(app_id=app_id)
    else:
        # If no type is given, check all type postfixes
        connections = client.list()
        matching_app_ids = []
        
        for postfix in ApplicationPostfix:
            app_id = name + "-" + postfix.value
            if any(conn.app_id == app_id for conn in connections):
                matching_app_ids.append(app_id)
        
        if len(matching_app_ids) == 0:
            raise BadRequest(f"No connection found with name '{name}' for any platform type")
        elif len(matching_app_ids) == 1:
            remove_connection(app_id=matching_app_ids[0])
        else:
            raise BadRequest(
                f"Multiple platform connections found with name '{name}': {', '.join(matching_app_ids)}. "
                f"Please specify the platform type to remove a specific connection."
            )
