"""
Server Factory Module

Creates MCP server instances with customer-specific tools.
Uses the low-level MCP SDK (not FastMCP) to match the TypeScript implementation.
"""

import os
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
    ListResourcesResult,
    ReadResourceResult,
    Resource,
)

from .customer_database import get_customer_products
from .welcome import welcome_tools
from .personal_banking import personal_banking_tools, personal_banking_resources
from .mortgage import mortgage_tools
from .credit_card import credit_card_tools
from .handoff import handoff_tools
from .knowledge import knowledge_tools
from .global_store import get_global_variable
from . import logger


def register_tools_with_customer_id(server: Server, tools: list, thread_id_getter):
    """
    Helper function to register tools with customerId from global store.
    Similar to TypeScript's registerToolsWithCustomerId.
    """
    for tool in tools:
        # Store tool info for later lookup
        if not hasattr(server, '_tool_handlers'):
            server._tool_handlers = {}
        if not hasattr(server, '_tool_configs'):
            server._tool_configs = {}

        server._tool_handlers[tool['name']] = tool['handler']
        server._tool_configs[tool['name']] = tool['config']
        server._tool_configs[tool['name']]['_needs_customer_id'] = True


def register_tools_direct(server: Server, tools: list):
    """
    Helper function to register tools without customerId wrapper.
    Similar to TypeScript's registerToolsDirect.
    """
    for tool in tools:
        if not hasattr(server, '_tool_handlers'):
            server._tool_handlers = {}
        if not hasattr(server, '_tool_configs'):
            server._tool_configs = {}

        server._tool_handlers[tool['name']] = tool['handler']
        server._tool_configs[tool['name']] = tool['config']
        server._tool_configs[tool['name']]['_needs_customer_id'] = False


def register_resources_with_customer_id(server: Server, resources: list):
    """
    Helper function to register resources with customerId from global store.
    Similar to TypeScript's registerResourcesWithCustomerId.
    """
    for resource in resources:
        if not hasattr(server, '_resource_handlers'):
            server._resource_handlers = {}
        if not hasattr(server, '_resource_configs'):
            server._resource_configs = {}

        logger.info(f"[SERVER] Registering resource: {resource['name']} at URI {resource['uri']}")
        logger.info(f"[SERVER] Registering on server instance id: {id(server)}")
        server._resource_handlers[resource['uri']] = resource['handler']
        server._resource_configs[resource['uri']] = resource
        logger.info(f"[SERVER] After registration, handlers: {list(server._resource_handlers.keys())}")


def create_customer_server(customer_id: str | None = None) -> Server:
    """
    Create a new server instance with customer-specific tools.

    Tools retrieve customerId from global store.
    If customerId is None (not authenticated yet), only welcome and handoff tools are registered.

    Args:
        customer_id: The authenticated customer's ID, or None if not authenticated

    Returns:
        Configured Server instance
    """
    server = Server(
        name="customercare-banking-server",
        version="1.0.0",
    )

    # Initialize tool/resource storage
    server._tool_handlers = {}
    server._tool_configs = {}
    server._resource_handlers = {}
    server._resource_configs = {}

    # Register welcome tools (available before authentication)
    register_tools_direct(server, welcome_tools)

    # Register handoff tools (available at all times - customerId is optional)
    register_tools_with_customer_id(server, handoff_tools, None)

    # Register knowledge tool if OpenSearch is configured
    if os.getenv("OPENSEARCH_PASSWORD"):
        register_tools_direct(server, knowledge_tools)

    # If no customerId, only welcome and handoff tools are available (pre-authentication)
    if not customer_id:
        logger.info("[SERVER] Created pre-auth server with welcome and handoff tools only")
    else:
        # Customer is authenticated - register product-specific tools
        products = get_customer_products(customer_id)

        # Register personal banking tools if customer has personal banking
        if products.has_personal_banking:
            register_tools_with_customer_id(server, personal_banking_tools, None)
            register_resources_with_customer_id(server, personal_banking_resources)
            logger.info(f"[SERVER] Registered personal banking tools for {customer_id}")

        # Register mortgage tools if customer has mortgage
        if products.has_mortgage:
            register_tools_with_customer_id(server, mortgage_tools, None)
            logger.info(f"[SERVER] Registered mortgage tools for {customer_id}")

        # Register credit card tools if customer has credit card
        if products.has_credit_card:
            # Credit card tools use JWT from CONTEXT VARIABLES, no customer_id wrapper needed
            register_tools_direct(server, credit_card_tools)
            logger.info(f"[SERVER] Registered credit card tools for {customer_id}")

        logger.info(
            f"[SERVER] Created authenticated server for {customer_id} with products: "
            f"banking={products.has_personal_banking}, "
            f"mortgage={products.has_mortgage}, "
            f"credit_card={products.has_credit_card}"
        )

    # Set up request handlers
    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """Return list of available tools."""
        logger.info(f"[SERVER] list_tools called, available tools: {list(server._tool_configs.keys())}")
        tools = []
        for name, config in server._tool_configs.items():
            # Pass _meta in the constructor for proper serialization
            tool = Tool(
                name=name,
                title=config.get('title'),
                description=config.get('description', ''),
                inputSchema=config.get('inputSchema', {}),
                _meta=config.get('_meta'),  # Include IBM Orchestrate extensions
            )
            tools.append(tool)
        return tools

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> CallToolResult:
        """Handle tool calls."""
        logger.info(f"[SERVER] handle_call_tool called: name={name}, arguments={arguments}")
        
        if name not in server._tool_handlers:
            logger.error(f"[SERVER] Unknown tool: {name}")
            raise ValueError(f"Unknown tool: {name}")

        handler = server._tool_handlers[name]
        config = server._tool_configs[name]

        # Get the request context for _meta
        # The Meta object is a pydantic model with extra fields stored in model_extra
        ctx = server.request_context
        extra = {}
        if ctx and ctx.meta:
            # Convert Meta object to dict, including extra fields
            extra['_meta'] = ctx.meta.model_dump()

        # If tool needs customerId, inject it from global store
        args = arguments or {}
        if config.get('_needs_customer_id'):
            thread_id = None
            meta_dict = extra.get('_meta', {})
            if meta_dict:
                thread_id = meta_dict.get('com.ibm.orchestrate/systemcontext', {}).get('thread_id')
            if thread_id:
                customer_id_from_global = get_global_variable(thread_id, 'customerId')
                args = {**args, 'customerId': customer_id_from_global}

        # Call the handler
        try:
            result = await handler(args, extra)
        except Exception as e:
            logger.error(f"[SERVER] Error calling tool {name}: {e}", exc_info=True)
            raise

        # Build CallToolResult from handler result
        if isinstance(result, dict):
            # Convert content items to proper TextContent objects
            content = []
            for item in result.get('content', []):
                if isinstance(item, dict):
                    content.append(TextContent(
                        type=item.get('type', 'text'),
                        text=item.get('text', ''),
                        annotations=item.get('annotations'),
                    ))
                else:
                    content.append(item)

            # If no content but has _meta (widget response), use empty content
            if not content and result.get('_meta'):
                content = []
            elif not content:
                # Only add default text if there's no _meta either
                content = [TextContent(type="text", text=str(result))]

            # Return full CallToolResult with _meta for IBM Orchestrate extensions
            return CallToolResult(
                content=content,
                _meta=result.get('_meta'),
                structuredContent=result.get('structuredContent'),
                isError=result.get('isError', False),
            )

        # If result is already a list of content, wrap it
        return CallToolResult(content=result)

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        """Return list of available resources."""
        resources = []
        for uri, config in server._resource_configs.items():
            resources.append(Resource(
                uri=uri,
                name=config.get('name', ''),
                description=config.get('description', ''),
                mimeType=config.get('mimeType', 'application/json'),
            ))
        return resources

    @server.read_resource()
    async def handle_read_resource(uri: str) -> str:
        """Handle resource reads."""
        logger.info(f"[SERVER] Resource read requested for URI: {uri} (type: {type(uri)})")
        logger.info(f"[SERVER] Available resource handlers: {list(server._resource_handlers.keys())}")
        logger.info(f"[SERVER] Handler keys types: {[type(k) for k in server._resource_handlers.keys()]}")
        logger.info(f"[SERVER] Server instance id: {id(server)}")
        
        # Convert uri to string if it's not already
        uri_str = str(uri)
        logger.info(f"[SERVER] Checking for uri_str: {uri_str} (type: {type(uri_str)})")
        
        if uri_str not in server._resource_handlers:
            logger.error(f"[SERVER] Unknown resource: {uri_str}")
            logger.error(f"[SERVER] Available handlers: {list(server._resource_handlers.keys())}")
            raise ValueError(f"Unknown resource: {uri_str}")

        handler = server._resource_handlers[uri_str]

        # Get the request context for _meta
        ctx = server.request_context
        extra = {}
        if ctx and ctx.meta:
            extra['_meta'] = ctx.meta.model_dump()

        # Get customerId from global store
        thread_id = None
        if extra.get('_meta'):
            thread_id = extra['_meta'].get('com.ibm.orchestrate/systemcontext', {}).get('thread_id')

        customer_id_from_global = None
        if thread_id:
            customer_id_from_global = get_global_variable(thread_id, 'customerId')

        logger.info(f"[SERVER] Calling resource handler for URI: {uri_str} with customerId: {customer_id_from_global}")
        
        # Call the handler with customerId
        try:
            result = await handler({'customerId': customer_id_from_global}, extra)
            logger.info(f"[SERVER] Resource handler returned result of type: {type(result)}, length: {len(result) if isinstance(result, str) else 'N/A'}")
            return result
        except Exception as e:
            logger.error(f"[SERVER] Error in resource handler: {e}", exc_info=True)
            raise

    return server
