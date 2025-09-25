from ibm_watsonx_orchestrate_mcp_server.utils.config import config

def check_version() -> str:
    """
    Check the version of the Orchestrate MCP server
    """
    return f"{config.server_name} v{config.version}"