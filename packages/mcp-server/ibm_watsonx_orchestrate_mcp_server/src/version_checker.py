from ibm_watsonx_orchestrate_mcp_server.utils.config import config

def check_version() -> str:
    return f"{config.server_name} v{config.version}"