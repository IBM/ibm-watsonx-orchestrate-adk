from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev
from ibm_watsonx_orchestrate.client.connections.connections_client import ConnectionsClient
from ibm_watsonx_orchestrate.cli.config import Config, ENVIRONMENTS_SECTION_HEADER, CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, ENV_WXO_URL_OPT
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionType, ConnectionAuthType, ConnectionSecurityScheme

LOCAL_CONNECTION_MANAGER_PORT = 3001

def _get_connections_manager_url() -> str:
    cfg = Config()
    active_env = cfg.get(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
    url = cfg.get(ENVIRONMENTS_SECTION_HEADER, active_env, ENV_WXO_URL_OPT)

    if is_local_dev(url):
        url_parts = url.split(":")
        url_parts[-1] = str(LOCAL_CONNECTION_MANAGER_PORT)
        url = ":".join(url_parts)
        url = url + "/api/v1"
        return url
    return None

def get_connections_client() -> ConnectionsClient:
    return instantiate_client(client=ConnectionsClient, url=_get_connections_manager_url())

def get_connection_type(security_scheme: ConnectionSecurityScheme, auth_type: ConnectionAuthType) -> ConnectionType:
    if security_scheme != ConnectionSecurityScheme.OAUTH2:
        return ConnectionType(security_scheme)
    return ConnectionType(auth_type)
