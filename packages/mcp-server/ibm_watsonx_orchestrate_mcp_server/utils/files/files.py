from pathlib import Path
from ibm_watsonx_orchestrate_mcp_server.utils.config.config import config

def get_working_directory_path(path_string: str) -> str:
    if config.working_directory is None:
        raise Exception("No working directory defined. Access to file system is blocked. To configure working directory expose the environment variable 'WXO_MCP_WORKING_DIRECTORY'")
    
    path: Path = Path(path_string).resolve()
    working_directory: Path = Path(config.working_directory).resolve()

    try:
        return str(path.relative_to(working_directory))
    except ValueError:
        raise Exception("Attempting to access resources outside the working directory is forbidden.")
