import logging
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev
from ibm_watsonx_orchestrate.client.connections.connections_client import ConnectionsClient
from ibm_watsonx_orchestrate.cli.config import Config, ENVIRONMENTS_SECTION_HEADER, CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, ENV_WXO_URL_OPT
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionType, ConnectionAuthType, ConnectionSecurityScheme

logger = logging.getLogger(__name__)

LOCAL_CONNECTION_MANAGER_PORT = 3001

def _get_connections_manager_url() -> str:
    cfg = Config()
    active_env = cfg.get(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
    url = cfg.get(ENVIRONMENTS_SECTION_HEADER, active_env, ENV_WXO_URL_OPT)

    if is_local_dev(url):
        url_parts = url.split(":")
        url_parts[-1] = str(LOCAL_CONNECTION_MANAGER_PORT)
        url = ":".join(url_parts)
        return url
    return None

def get_connections_client() -> ConnectionsClient:
    return instantiate_client(client=ConnectionsClient, url=_get_connections_manager_url())

def get_connection_type(security_scheme: ConnectionSecurityScheme, auth_type: ConnectionAuthType) -> ConnectionType | None:
    if security_scheme is None and auth_type is None:
        return None

    if security_scheme != ConnectionSecurityScheme.OAUTH2:
        return ConnectionType(security_scheme)
    return ConnectionType(auth_type)

def get_connection_id(app_id: str, supported_schemas: set | None = None) -> str:
    if not app_id:
        return
    
    connections_client = get_connections_client()

    connection_id = None
    if app_id is not None:
        connection = connections_client.get(app_id=app_id)
        if  not connection:
            logger.error(f"No connection exists with the app-id '{app_id}'")
            exit(1)
        connection_id = connection.connection_id
    
    existing_draft_configuration = None
    existing_live_configuration = None

    if supported_schemas:
        existing_draft_configuration = connections_client.get_config(app_id=app_id, env='draft')
        existing_live_configuration = connections_client.get_config(app_id=app_id, env='live')
        for config in [existing_draft_configuration, existing_live_configuration]:
            if config and config.security_scheme not in supported_schemas:
                logger.error(f"Only {', '.join(supported_schemas)} credentials are currently supported. Provided connection '{config.app_id}' is of type '{config.security_scheme}' in environment '{config.environment}'")
                exit(1)

    return connection_id