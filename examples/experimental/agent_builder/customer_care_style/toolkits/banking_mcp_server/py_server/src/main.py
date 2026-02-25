"""
CustomerCare MCP Server - Main Entry Point

A Model Context Protocol server demonstrating three layers of context:
1. Context Variables - Passed by API caller (e.g., JWT token)
2. Global Store - Stored per thread_id, shared across MCP servers (e.g., customerId)
3. Local Store - Stored per thread_id, isolated per MCP server (e.g., pending transactions)

Uses the low-level MCP SDK (not FastMCP) to match the TypeScript implementation.
"""

import os
import json
import asyncio
from typing import Any

from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
import uvicorn
import anyio

from mcp.server.streamable_http import StreamableHTTPServerTransport

from .server import create_customer_server
from .global_store import get_global_variable
from . import logger

# Load environment variables from .env file
# Look in current directory first, then parent directories
from pathlib import Path

def find_dotenv() -> Path | None:
    """Find .env file in current or parent directories."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            return env_file
    return None

env_path = find_dotenv()
if env_path:
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback to default behavior


def extract_thread_id(body: dict[str, Any]) -> str | None:
    """Extract thread_id from MCP request body."""
    return (
        body.get("params", {})
        .get("_meta", {})
        .get("com.ibm.orchestrate/systemcontext", {})
        .get("thread_id")
    )


async def health_handler(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "service": "customercare-banking-mcp-server"})


async def mcp_handler(request: Request) -> Response:
    """
    Handle MCP requests.

    This creates a new server instance per request based on the customer's
    authentication state, similar to the TypeScript implementation.
    """
    try:
        # Parse the request body
        body = await request.json()

        logger.info("[SERVER] Received request:", extra={
            "method": body.get("method"),
            "body": body,
        })

        # Extract thread_id and customer_id
        thread_id = extract_thread_id(body)
        customer_id = None

        # Retrieve customerId from GLOBAL STORE if available
        # Note: customerId is set by the welcome tool after successful PIN verification
        if thread_id:
            customer_id = get_global_variable(thread_id, "customerId")

        # Create server instance with customer-specific tools
        # If customerId is None, only welcome and handoff tools will be registered
        server = create_customer_server(customer_id)

        # Create transport in STATELESS mode (no session validation)
        # This allows each request to be handled independently
        transport = StreamableHTTPServerTransport(
            mcp_session_id=None,  # Stateless mode - no session validation
            is_json_response_enabled=True,
        )

        # Storage for response
        response_started = False
        response_body = []
        response_headers = []
        response_status = 200

        # Create ASGI scope, receive, and send for the transport
        scope = {
            "type": "http",
            "method": request.method,
            "path": request.url.path,
            "query_string": request.url.query.encode() if request.url.query else b"",
            "headers": [(k.lower().encode(), v.encode()) for k, v in request.headers.items()],
        }

        async def receive():
            body_bytes = json.dumps(body).encode()
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        async def send(message):
            nonlocal response_started, response_status, response_headers
            if message["type"] == "http.response.start":
                response_started = True
                response_status = message["status"]
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                response_body.append(message.get("body", b""))

        # Connect transport and run server
        async with transport.connect() as (read_stream, write_stream):
            # Create task group to run server and handle request concurrently
            async with anyio.create_task_group() as tg:
                # Start server processing in background
                async def run_server():
                    try:
                        await server.run(
                            read_stream,
                            write_stream,
                            server.create_initialization_options(),
                            raise_exceptions=True,
                            stateless=True,
                        )
                    except Exception as e:
                        logger.error(f"Server run error: {e}")

                tg.start_soon(run_server)

                # Handle the HTTP request
                await transport.handle_request(scope, receive, send)

                # Cancel server task after request is handled
                tg.cancel_scope.cancel()

        # Build response
        final_body = b"".join(response_body)
        headers = {}
        for k, v in response_headers:
            key = k.decode() if isinstance(k, bytes) else k
            val = v.decode() if isinstance(v, bytes) else v
            headers[key] = val

        return Response(
            content=final_body,
            status_code=response_status,
            headers=headers,
        )

    except Exception as error:
        logger.error("Error handling MCP request:", extra={"error": str(error)})
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal server error",
                },
                "id": None,
            },
            status_code=500,
        )


def create_app() -> Starlette:
    """Create the Starlette application."""
    app = Starlette(
        routes=[
            Route("/health", health_handler, methods=["GET"]),
            Route("/mcp", mcp_handler, methods=["POST"]),
        ],
    )

    return app


# Create the app instance for uvicorn
app = create_app()


def main() -> None:
    """Main entry point for the server."""
    port = int(os.getenv("PORT", "3004"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"CustomerCare Banking MCP server listening on {host}:{port}")

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
