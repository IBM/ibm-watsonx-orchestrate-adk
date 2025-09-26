import logging
import sys
import os
from ibm_watsonx_orchestrate_mcp_server.utils.logging import setup_logging
from ibm_watsonx_orchestrate_mcp_server.utils.config import config, MCPTransportTypes
from fastmcp import FastMCP
from ibm_watsonx_orchestrate_mcp_server.src import __all_tools__

mcp: FastMCP = FastMCP(name=config.server_name)

def _configure_logging() -> logging.Logger:
    setup_logging(debug=config.debug)
    return logging.getLogger(config.server_name)

def _load_tools() -> None:
    for tool in __all_tools__:
        mcp.tool()(tool)

def start_server() -> None:
    logger: logging.Logger = _configure_logging()

    if config.working_directory:
        os.chdir(config.working_directory)

    _load_tools()
    
    # Start server
    logger.debug(f"🚀 Starting {config.server_name} v{config.version}")
    logger.debug(f"📡 Transport: {config.transport}, Host: {config.host}, Port: {config.port}")
    
    try:
        if config.transport in (MCPTransportTypes.HTTP_STREAMABLE, MCPTransportTypes.SSE):
            logger.info(f"🌐 Starting HTTP server on {config.host}:{config.port}")
            mcp.run(transport=config.transport, host=config.host, port=config.port)
        else:
            logger.info("📡 Starting STDIO transport")
            mcp.run()
            
    except KeyboardInterrupt:
        logger.info("🛑 Server interrupted by user")
    except Exception as e:
        logger.error(f"💥 Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    start_server()