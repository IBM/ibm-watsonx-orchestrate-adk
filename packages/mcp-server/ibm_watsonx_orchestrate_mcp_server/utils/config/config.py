import os
import tomllib
from typing import Any
from importlib.metadata import version

DEFAULT_SERVER_NAME: str = "WXO-MCP"
DEFAULT_VERSION: str = "Unknown"
DEFAULT_DESCRIPTION: str = "MCP Server used to interact with watsonx Orchestrate"

DEFAULT_HOST = "127.0.0.1"  # Secure default - localhost only
DEFAULT_PORT = 8080
DEFAULT_TRANSPORT = "stdio"  # Options: "stdio", "http", "sse" TODO: Make enum

def _find_pyproject_toml() -> str | None:
    """
    Locate the pyproject.toml file by traversing the directory tree upwards until found.

    Returns:
        The path to the pyproject.toml file if found, otherwise None.
    """

    current: str = os.path.abspath(os.path.dirname(__file__))
    while True:
        current_toml = os.path.join(current, "pyproject.toml")
        if os.path.isfile(current_toml):
            return current_toml
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError("pyproject.toml not found")
        current = parent

def _get_pyproject_configuration() -> dict:
    """
    Load configuration from the pyproject.toml file.

    Returns:
        A dictionary containing the configuration values from the pyproject.toml file.
        If no configuration is found, an empty dictionary is returned.
    """
    toml_path: str | None = _find_pyproject_toml()
    if not toml_path:
        return {}
    try:
        with open(toml_path, "rb") as f:
            return tomllib.load(f).get("project", {})
    except FileNotFoundError:
        return {}

class Config:
    """Centralized configuration manager."""
    
    def __init__(self):
        pyproject_config: dict[Any, Any] = _get_pyproject_configuration()

        self.server_name: str = pyproject_config.get("name", DEFAULT_SERVER_NAME)
        try:
            self.version: str = version("ibm-watsonx-orchestrate-mcp-server")
        except:
            self.version: str = DEFAULT_VERSION
        self.description: str = pyproject_config.get("description", DEFAULT_DESCRIPTION)
        
        # Network
        self.host: str = os.getenv("WXO_MCP_HOST", DEFAULT_HOST)
        self.port: int = int(os.getenv("WXO_MCP_PORT", str(DEFAULT_PORT)))
        self.transport: str = os.getenv("WXO_MCP_TRANSPORT", DEFAULT_TRANSPORT).lower()
        
        # Development
        self.debug:bool = os.getenv("WXO_MCP_DEBUG", "false").lower() == "true"

        # Application
        self.working_directory = os.getenv("WXO_MCP_WORKING_DIRECTORY")
    
    def __repr__(self) -> str:
        return f"""
        ========================================================
        Server Name: {self.server_name}
        Version: {self.version}
        Description: {self.description}
        ========================================================
        Transport: {self.transport}
        Network:
            Host: {self.host}
            Port: {self.port}
        ========================================================
        Debug: {self.debug}
        ========================================================
        DEFAULT_WORKING_DIRECTORY: {self.working_directory}
        ========================================================
        """

config: Config = Config()