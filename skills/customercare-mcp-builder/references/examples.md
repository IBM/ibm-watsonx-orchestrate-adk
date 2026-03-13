# CustomerCare MCP Server - Reference Implementation Examples

This file contains complete reference implementations for building customer care MCP servers in both TypeScript and Python. Copy infrastructure code exactly; adapt tool implementations for your domain.

## Table of Contents

1. [Project Configuration](#1-project-configuration)
2. [Server Core Infrastructure](#2-server-core-infrastructure)
3. [Context Management](#3-context-management)
4. [Data Layer Pattern](#4-data-layer-pattern)
5. [Welcome & Authentication Tools](#5-welcome--authentication-tools)
6. [Personal Banking Tools (Pattern Catalog)](#6-personal-banking-tools)
7. [Agent Handoff Tools](#7-agent-handoff-tools)
8. [Knowledge/RAG Tools](#8-knowledgerag-tools)
9. [Service Layer Patterns](#9-service-layer-patterns)

---

## 1. Project Configuration

### TypeScript - package.json

```json
{
  "name": "customercare",
  "version": "1.0.0",
  "description": "Customer Care MCP-powered TypeScript project",
  "main": "dist/index.js",
  "scripts": {
    "dev": "ts-node src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "keywords": ["typescript", "mcp", "customer-care"],
  "license": "ISC",
  "devDependencies": {
    "@types/node": "^20.9.2",
    "ts-node": "^10.9.1",
    "typescript": "^5.7.3"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.25.1",
    "@types/express": "^5.0.6",
    "express": "^5.2.1",
    "pino": "^10.1.0",
    "pino-pretty": "^13.1.3",
    "undici": "^7.18.2"
  }
}
```

### TypeScript - tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### Python - pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "customercare-mcp-server"
version = "1.0.0"
description = "Customer Care MCP Server - Python Implementation"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    "structlog>=24.0.0",
    "starlette>=0.40.0",
    "uvicorn>=0.30.0",
]

[project.scripts]
customercare-server = "src.main:main"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

### Environment Variables (.env.example)

```bash
# Server Configuration
PORT=3000
HOST=0.0.0.0
LOG_LEVEL=info

# OpenSearch Configuration (Optional - for Knowledge feature)
# If OPENSEARCH_PASSWORD is not set, knowledge tools will not be registered
OPENSEARCH_PASSWORD=
OPENSEARCH_ENDPOINT=https://localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin
INDEX_NAME=knowledge_vector_index
OPENSEARCH_FIELD_TITLE=title
OPENSEARCH_FIELD_BODY=passage_text
OPENSEARCH_FIELD_URL=url
# Optional: custom OpenSearch query body (JSON string with $QUERY placeholder)
# OPENSEARCH_QUERY_BODY='{"query":{"neural":{"passage_embedding":{"query_text":"$QUERY","k":10}}}}'
```

---

## 2. Server Core Infrastructure

The server entry point creates per-request MCP server instances with customer-specific tools. This is the Unique Tools Per User pattern -- unauthenticated users only get welcome + handoff tools.

### TypeScript - index.ts

```typescript
#!/usr/bin/env node

/**
 * CustomerCare MCP Server
 *
 * A Model Context Protocol server demonstrating three layers of context:
 * 1. Context Variables - Passed by API caller (e.g., JWT token)
 * 2. Global Store - Stored per thread_id, shared across MCP servers (e.g., customerId)
 * 3. Local Store - Stored per thread_id, isolated per MCP server (e.g., pending transactions)
 */
import { Request, Response } from 'express';
import { createMcpExpressApp } from '@modelcontextprotocol/sdk/server/express.js';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { getCustomerProducts } from './customerDatabase';
import {
  personalBankingResources,
  personalBankingTools,
} from './personalBanking';
import { mortgageTools } from './mortgage';
import { creditCardTools } from './creditCard';
import { handoffTools } from './handoff';
import { welcomeTools } from './welcome';
import { knowledgeTools } from './knowledge';
import { getGlobalVariable, setGlobalVariable } from './globalStore';
import * as logger from './logger';
import {
  ListResourcesRequestSchema
} from '@modelcontextprotocol/sdk/types.js';

const app = createMcpExpressApp({
    host: '0.0.0.0'
});

/**
 * Helper function to register tools with customerId from global store
 */
function registerToolsWithCustomerId(server: McpServer, tools: any[]) {
  for (const tool of tools) {
    const wrappedHandler = async (args: any, extra: any) => {
      const threadId =
        extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
      const customerIdFromGlobal = threadId
        ? getGlobalVariable(threadId, 'customerId')
        : undefined;
      return tool.handler(
        {
          ...args,
          customerId: customerIdFromGlobal,
        },
        extra,
      );
    };
    server.registerTool(tool.name, tool.config, wrappedHandler as any);
  }
}

/**
 * Helper function to register tools without customerId wrapper
 * but still passes _meta from extra parameter
 */
function registerToolsDirect(server: McpServer, tools: any[]) {
  for (const tool of tools) {
    const wrappedHandler = async (args: any, extra: any) => {
      return tool.handler(args, extra);
    };
    server.registerTool(tool.name, tool.config, wrappedHandler as any);
  }
}

/**
 * Helper function to register resources with customerId from global store
 */
function registerResourcesWithCustomerId(server: McpServer, resources: any[]) {
  for (const resource of resources) {
    const wrappedHandler = async (args: any, extra: any) => {
      const threadId =
        extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
      const customerIdFromGlobal = threadId
        ? getGlobalVariable(threadId, 'customerId')
        : undefined;

      logger.info(`[SERVER] Resource handler called for: ${resource.uri} with customerId: ${customerIdFromGlobal}`);
      return resource.handler(
        {
          ...args,
          customerId: customerIdFromGlobal,
        },
        extra,
      );
    };

    logger.info(`[SERVER] Registering resource: ${resource.name} at URI ${resource.uri}`);
    server.registerResource(
      resource.name,
      resource.uri,
      {
        description: resource.description,
        mimeType: resource.mimeType,
      },
      wrappedHandler as any,
    );
  }
}

/**
 * Create a new server instance with customer-specific tools
 * Tools retrieve customerId from global store
 * If customerId is undefined (not authenticated yet), only welcome and handoff tools are registered
 */
function createCustomerServer(customerId: string | undefined): McpServer {
  const server = new McpServer({
    name: 'customercare-banking-server',
    version: '1.0.0',
  },
    {
      capabilities: {
        resources: {},
        tools: {},
      },
    });

  // Register welcome tools (available before authentication)
  registerToolsDirect(server, welcomeTools);

  // Register handoff tools (available at all times (customerid is optional))
  registerToolsWithCustomerId(server, handoffTools);

  if (process.env.OPENSEARCH_PASSWORD) {
    // Register knowledge tool (available at all times)
    registerToolsDirect(server, knowledgeTools);
  }

  // If no customerId, only welcome and handoff tools are available (pre-authentication)
  // If no customerId, register empty placeholder resource to advertise resources capability
  if (!customerId) {
    server.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return { resources: [] };
    });
    return server;
  }

  // Customer is authenticated - register product-specific tools
  const products = getCustomerProducts(customerId);

  const hasResources = products.hasPersonalBanking;

  if (!hasResources) {
    server.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return { resources: [] };
    });
  }

  if (products.hasPersonalBanking) {
    registerToolsWithCustomerId(server, personalBankingTools);
    registerResourcesWithCustomerId(server, personalBankingResources);
  }

  if (products.hasMortgage) {
    registerToolsWithCustomerId(server, mortgageTools);
  }

  if (products.hasCreditCard) {
    // Credit card tools use JWT from CONTEXT VARIABLES, no wrapper needed
    registerToolsDirect(server, creditCardTools);
  }

  return server;
}

// MCP endpoint
app.post('/mcp', async (req: Request, res: Response) => {
  try {
    logger.info('[SERVER] Received request:', {
      method: req.body?.method,
      body: req.body,
    });

    let customerId: string | undefined;
    let threadId: string | undefined;

    // Extract thread_id from request if available
    if (
      req.body?.params?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id
    ) {
      threadId =
        req.body.params._meta['com.ibm.orchestrate/systemcontext'].thread_id;
    }

    // Retrieve customerId from GLOBAL STORE if available
    if (threadId) {
      customerId = getGlobalVariable(threadId, 'customerId');
    }

    // Create server instance with customer-specific tools
    const server = createCustomerServer(customerId);

    // Create transport in STATELESS mode (no session validation)
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true,
    });

    res.on('close', async () => {
      await transport.close();
      await server.close();
    });

    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    logger.error('Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal server error',
        },
        id: null,
      });
    }
  }
});

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', service: 'customercare-banking-mcp-server' });
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  logger.info(`CustomerCare Banking MCP server listening on port ${PORT}`);
});
```

### Python - main.py

```python
"""
CustomerCare MCP Server - Main Entry Point

Uses Starlette/Uvicorn with the low-level MCP SDK.
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

load_dotenv()


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
    """Handle MCP requests -- creates a new server instance per request."""
    try:
        body = await request.json()
        logger.info("[SERVER] Received request:", extra={"method": body.get("method"), "body": body})

        thread_id = extract_thread_id(body)
        customer_id = None

        if thread_id:
            customer_id = get_global_variable(thread_id, "customerId")

        server = create_customer_server(customer_id)

        transport = StreamableHTTPServerTransport(
            mcp_session_id=None,
            is_json_response_enabled=True,
        )

        response_body = []
        response_headers = []
        response_status = 200

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
            nonlocal response_status, response_headers
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                response_body.append(message.get("body", b""))

        async with transport.connect() as (read_stream, write_stream):
            async with anyio.create_task_group() as tg:
                async def run_server():
                    try:
                        await server.run(
                            read_stream, write_stream,
                            server.create_initialization_options(),
                            raise_exceptions=True, stateless=True,
                        )
                    except Exception as e:
                        logger.error(f"Server run error: {e}")

                tg.start_soon(run_server)
                await transport.handle_request(scope, receive, send)
                tg.cancel_scope.cancel()

        final_body = b"".join(response_body)
        headers = {}
        for k, v in response_headers:
            key = k.decode() if isinstance(k, bytes) else k
            val = v.decode() if isinstance(v, bytes) else v
            headers[key] = val

        return Response(content=final_body, status_code=response_status, headers=headers)

    except Exception as error:
        logger.error("Error handling MCP request:", extra={"error": str(error)})
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal server error"}, "id": None},
            status_code=500,
        )


def create_app() -> Starlette:
    return Starlette(routes=[
        Route("/health", health_handler, methods=["GET"]),
        Route("/mcp", mcp_handler, methods=["POST"]),
    ])


app = create_app()


def main() -> None:
    port = int(os.getenv("PORT", "3000"))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"CustomerCare Banking MCP server listening on {host}:{port}")
    uvicorn.run("src.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
```

### Python - server.py (Server Factory)

```python
"""
Server Factory Module -- creates MCP server instances with customer-specific tools.
Uses the low-level MCP SDK (not FastMCP).
"""

import os
from mcp.server import Server
from mcp.types import (
    Tool, TextContent, CallToolResult, ListToolsResult,
    ListResourcesResult, ReadResourceResult, Resource,
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
    """Register tools with customerId injection from global store."""
    for tool in tools:
        if not hasattr(server, '_tool_handlers'):
            server._tool_handlers = {}
        if not hasattr(server, '_tool_configs'):
            server._tool_configs = {}
        server._tool_handlers[tool['name']] = tool['handler']
        server._tool_configs[tool['name']] = tool['config']
        server._tool_configs[tool['name']]['_needs_customer_id'] = True


def register_tools_direct(server: Server, tools: list):
    """Register tools without customerId wrapper."""
    for tool in tools:
        if not hasattr(server, '_tool_handlers'):
            server._tool_handlers = {}
        if not hasattr(server, '_tool_configs'):
            server._tool_configs = {}
        server._tool_handlers[tool['name']] = tool['handler']
        server._tool_configs[tool['name']] = tool['config']
        server._tool_configs[tool['name']]['_needs_customer_id'] = False


def register_resources_with_customer_id(server: Server, resources: list):
    """Register resources with customerId injection from global store."""
    for resource in resources:
        if not hasattr(server, '_resource_handlers'):
            server._resource_handlers = {}
        if not hasattr(server, '_resource_configs'):
            server._resource_configs = {}
        server._resource_handlers[resource['uri']] = resource['handler']
        server._resource_configs[resource['uri']] = resource


def create_customer_server(customer_id: str | None = None) -> Server:
    """Create a new server instance with customer-specific tools."""
    server = Server(name="customercare-banking-server", version="1.0.0")

    server._tool_handlers = {}
    server._tool_configs = {}
    server._resource_handlers = {}
    server._resource_configs = {}

    # Always register welcome + handoff
    register_tools_direct(server, welcome_tools)
    register_tools_with_customer_id(server, handoff_tools, None)

    if os.getenv("OPENSEARCH_PASSWORD"):
        register_tools_direct(server, knowledge_tools)

    if customer_id:
        products = get_customer_products(customer_id)
        if products.has_personal_banking:
            register_tools_with_customer_id(server, personal_banking_tools, None)
            register_resources_with_customer_id(server, personal_banking_resources)
        if products.has_mortgage:
            register_tools_with_customer_id(server, mortgage_tools, None)
        if products.has_credit_card:
            register_tools_direct(server, credit_card_tools)

    # Set up request handlers
    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        tools = []
        for name, config in server._tool_configs.items():
            tool = Tool(
                name=name,
                title=config.get('title'),
                description=config.get('description', ''),
                inputSchema=config.get('inputSchema', {}),
                _meta=config.get('_meta'),
            )
            tools.append(tool)
        return tools

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> CallToolResult:
        if name not in server._tool_handlers:
            raise ValueError(f"Unknown tool: {name}")

        handler = server._tool_handlers[name]
        config = server._tool_configs[name]

        ctx = server.request_context
        extra = {}
        if ctx and ctx.meta:
            extra['_meta'] = ctx.meta.model_dump()

        args = arguments or {}
        if config.get('_needs_customer_id'):
            thread_id = None
            meta_dict = extra.get('_meta', {})
            if meta_dict:
                thread_id = meta_dict.get('com.ibm.orchestrate/systemcontext', {}).get('thread_id')
            if thread_id:
                customer_id_from_global = get_global_variable(thread_id, 'customerId')
                args = {**args, 'customerId': customer_id_from_global}

        result = await handler(args, extra)

        if isinstance(result, dict):
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

            if not content and result.get('_meta'):
                content = []
            elif not content:
                content = [TextContent(type="text", text=str(result))]

            return CallToolResult(
                content=content,
                _meta=result.get('_meta'),
                structuredContent=result.get('structuredContent'),
                isError=result.get('isError', False),
            )

        return CallToolResult(content=result)

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        resources = []
        for uri, config in server._resource_configs.items():
            resources.append(Resource(
                uri=uri, name=config.get('name', ''),
                description=config.get('description', ''),
                mimeType=config.get('mimeType', 'application/json'),
            ))
        return resources

    @server.read_resource()
    async def handle_read_resource(uri: str) -> str:
        uri_str = str(uri)
        if uri_str not in server._resource_handlers:
            raise ValueError(f"Unknown resource: {uri_str}")

        handler = server._resource_handlers[uri_str]
        ctx = server.request_context
        extra = {}
        if ctx and ctx.meta:
            extra['_meta'] = ctx.meta.model_dump()

        thread_id = None
        if extra.get('_meta'):
            thread_id = extra['_meta'].get('com.ibm.orchestrate/systemcontext', {}).get('thread_id')

        customer_id_from_global = None
        if thread_id:
            customer_id_from_global = get_global_variable(thread_id, 'customerId')

        return await handler({'customerId': customer_id_from_global}, extra)

    return server
```

---

## 3. Context Management

### TypeScript - globalStore.ts

Shared across all MCP servers within the same conversation thread.

```typescript
/**
 * Global Store Module
 *
 * NOTE: This is a sample implementation using in-memory storage.
 * In production, use a persistent store (Redis, database, etc.).
 */

const globalStore = new Map<string, Map<string, any>>();

export function setGlobalVariable(threadId: string, variableName: string, value: any): void {
  if (!globalStore.has(threadId)) {
    globalStore.set(threadId, new Map());
  }
  const threadData = globalStore.get(threadId);
  if (threadData) {
    threadData.set(variableName, value);
  }
}

export function getGlobalVariable(threadId: string, variableName: string): any {
  return globalStore.get(threadId)?.get(variableName);
}

export function deleteGlobalVariable(threadId: string, variableName: string): boolean {
  return globalStore.get(threadId)?.delete(variableName) ?? false;
}
```

### TypeScript - localStore.ts

Isolated to a single MCP server within a thread. Used for pending transactions.

```typescript
const localStore = new Map<string, Map<string, any>>();

export function setLocalVariable(threadId: string, variableName: string, value: any): void {
  if (!localStore.has(threadId)) {
    localStore.set(threadId, new Map());
  }
  const threadData = localStore.get(threadId);
  if (threadData) {
    threadData.set(variableName, value);
  }
}

export function getLocalVariable(threadId: string, variableName: string): any {
  return localStore.get(threadId)?.get(variableName);
}

export function deleteLocalVariable(threadId: string, variableName: string): boolean {
  return localStore.get(threadId)?.delete(variableName) ?? false;
}
```

### Python - global_store.py

```python
from typing import Any

_global_store: dict[str, dict[str, Any]] = {}

def set_global_variable(thread_id: str, variable_name: str, value: Any) -> None:
    if thread_id not in _global_store:
        _global_store[thread_id] = {}
    _global_store[thread_id][variable_name] = value

def get_global_variable(thread_id: str, variable_name: str) -> Any | None:
    return _global_store.get(thread_id, {}).get(variable_name)

def delete_global_variable(thread_id: str, variable_name: str) -> bool:
    if thread_id in _global_store and variable_name in _global_store[thread_id]:
        del _global_store[thread_id][variable_name]
        return True
    return False
```

### Python - local_store.py

```python
from typing import Any

_local_store: dict[str, dict[str, Any]] = {}

def set_local_variable(thread_id: str, variable_name: str, value: Any) -> None:
    if thread_id not in _local_store:
        _local_store[thread_id] = {}
    _local_store[thread_id][variable_name] = value

def get_local_variable(thread_id: str, variable_name: str) -> Any | None:
    return _local_store.get(thread_id, {}).get(variable_name)

def delete_local_variable(thread_id: str, variable_name: str) -> bool:
    if thread_id in _local_store and variable_name in _local_store[thread_id]:
        del _local_store[thread_id][variable_name]
        return True
    return False
```

---

## 4. Data Layer Pattern

Shows the customer database with product lookup driving dynamic tool registration.

### TypeScript - customerDatabase.ts

```typescript
export interface CustomerProducts {
  hasPersonalBanking: boolean;
  hasMortgage: boolean;
  hasCreditCard: boolean;
}

export interface CustomerProfile {
  customerId: string;
  firstName: string;
  lastName: string;
  telephoneNumber: string;
  pin: string;
  products: CustomerProducts;
}

// Mock customer database -- replace with your actual data source
const customerDatabase: Record<string, CustomerProfile> = {
  CUST001: {
    customerId: 'CUST001', firstName: 'John', lastName: 'Smith',
    telephoneNumber: '+15551234567', pin: '1234',
    products: { hasPersonalBanking: true, hasMortgage: false, hasCreditCard: true },
  },
  CUST002: {
    customerId: 'CUST002', firstName: 'Jane', lastName: 'Doe',
    telephoneNumber: '+15559876543', pin: '5678',
    products: { hasPersonalBanking: true, hasMortgage: true, hasCreditCard: false },
  },
};

const telephoneToCustomerId: Record<string, string> = {
  '+15551234567': 'CUST001',
  '+15559876543': 'CUST002',
};

export function getCustomerProducts(customerId: string): CustomerProducts {
  return customerDatabase[customerId]?.products ?? {
    hasPersonalBanking: false, hasMortgage: false, hasCreditCard: false,
  };
}

export function getCustomerProfile(customerId: string): CustomerProfile | undefined {
  return customerDatabase[customerId];
}

export function getCustomerProfileByPhone(telephoneNumber: string): CustomerProfile | undefined {
  const customerId = telephoneToCustomerId[telephoneNumber];
  return customerId ? customerDatabase[customerId] : undefined;
}

export function verifyCustomerPin(telephoneNumber: string, pin: string): boolean {
  const profile = getCustomerProfileByPhone(telephoneNumber);
  return profile ? profile.pin === pin : false;
}
```

### Python - customer_database.py

```python
from dataclasses import dataclass

@dataclass
class CustomerProducts:
    has_personal_banking: bool
    has_mortgage: bool
    has_credit_card: bool

@dataclass
class CustomerProfile:
    customer_id: str
    first_name: str
    last_name: str
    telephone_number: str
    pin: str
    products: CustomerProducts

# Mock customer database -- replace with your actual data source
_customer_database: dict[str, CustomerProfile] = {
    "CUST001": CustomerProfile(
        customer_id="CUST001", first_name="John", last_name="Smith",
        telephone_number="+15551234567", pin="1234",
        products=CustomerProducts(has_personal_banking=True, has_mortgage=False, has_credit_card=True),
    ),
    "CUST002": CustomerProfile(
        customer_id="CUST002", first_name="Jane", last_name="Doe",
        telephone_number="+15559876543", pin="5678",
        products=CustomerProducts(has_personal_banking=True, has_mortgage=True, has_credit_card=False),
    ),
}

_telephone_to_customer_id: dict[str, str] = {
    "+15551234567": "CUST001",
    "+15559876543": "CUST002",
}

def get_customer_products(customer_id: str) -> CustomerProducts:
    profile = _customer_database.get(customer_id)
    return profile.products if profile else CustomerProducts(False, False, False)

def get_customer_profile(customer_id: str) -> CustomerProfile | None:
    return _customer_database.get(customer_id)

def get_customer_profile_by_phone(telephone_number: str) -> CustomerProfile | None:
    customer_id = _telephone_to_customer_id.get(telephone_number)
    return _customer_database.get(customer_id) if customer_id else None

def verify_customer_pin(telephone_number: str, pin: str) -> bool:
    profile = get_customer_profile_by_phone(telephone_number)
    return profile.pin == pin if profile else False
```

---

## 5. Welcome & Authentication Tools

**Patterns demonstrated:** Welcome tool (`_meta.welcomeTool: true`), model visibility (`visibility: ['app']`), widget (number input for PIN), `refreshThreadCapabilities`, agent handoff on auth failure.

### TypeScript - welcome.ts

```typescript
import { z } from 'zod';
import { getCustomerProfileByPhone, verifyCustomerPin } from './customerDatabase';
import { setGlobalVariable } from './globalStore';

export const welcomeCustomerTool = {
  name: 'welcome_customer',
  config: {
    title: 'Welcome Customer',
    description: 'Welcome the customer and authenticate them with their PIN',
    inputSchema: {},
    _meta: {
      welcomeTool: true,  // Automatically invoked when thread begins
      ui: {
        visibility: ['app'],  // Hidden from model
      },
    },
  },
  handler: async (args: any, extra: any) => {
    const _meta = extra?._meta;
    const telephoneNumber = _meta?.['com.ibm.orchestrate/context']?.telephoneNumber;
    const customerProfile = telephoneNumber
      ? getCustomerProfileByPhone(telephoneNumber)
      : null;

    // If we can't find the customer, transfer to agent
    if (!telephoneNumber || !customerProfile) {
      return {
        content: [{
          type: 'text',
          text: 'Welcome! I was unable to find your account. Let me connect you with an agent who can assist you.',
          annotations: { audience: ['user'] },
        }],
        _meta: {
          'com.ibm.orchestrate/extensions': {
            transfer_to_live_agent: {
              message_to_human_agent: 'Customer account could not be found. Authentication failed.',
              agent_available: 'Please wait while I connect you to an agent.',
              agent_unavailable: "I'm sorry, but no agents are online at the moment. Please try again later.",
            },
          },
        },
      };
    }

    // Greet and request PIN via widget
    return {
      content: [{
        type: 'text',
        text: `Hello ${customerProfile.firstName} ${customerProfile.lastName}! Welcome to CustomerCare Banking.`,
        annotations: { audience: ['user'] },
      }],
      _meta: {
        'com.ibm.orchestrate/widget': {
          type: 'number',
          collection_type: 'integer',
          title: 'For your security, please enter your 4-digit PIN.',
          min_number: 0,
          max_number: 9999,
          min_digits: 4,
          max_digits: 4,
          on_event: {
            tool: 'verify_customer_pin',
            parameters: {},
            map_input_to: 'pin',
          },
        },
      },
    };
  },
};

export const verifyCustomerPinTool = {
  name: 'verify_customer_pin',
  config: {
    title: 'Verify Customer PIN',
    description: 'Verify the PIN entered by the customer',
    inputSchema: {
      pin: z.string().describe('PIN entered by the customer'),
    },
  },
  handler: async ({ pin }: { pin: string }, extra: any) => {
    const telephoneNumber = extra?._meta?.['com.ibm.orchestrate/context']?.telephoneNumber;
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
    const isValid = telephoneNumber && verifyCustomerPin(telephoneNumber, pin);

    if (isValid && telephoneNumber) {
      const customerProfile = getCustomerProfileByPhone(telephoneNumber);
      if (threadId && customerProfile) {
        setGlobalVariable(threadId, 'customerId', customerProfile.customerId);
      }

      return {
        content: [{
          type: 'text',
          text: 'Thank you! Your PIN has been verified. How can I assist you today?',
          annotations: { audience: ['user'] },
        }],
        _meta: {
          // Signal all MCP servers to refresh their tool/resources lists
          refreshThreadCapabilities: threadId,
        },
      };
    } else {
      return {
        content: [{
          type: 'text',
          text: "I'm sorry, but the PIN you entered is incorrect. Please try again.",
          annotations: { audience: ['user'] },
        }],
        _meta: {
          'com.ibm.orchestrate/widget': {
            type: 'number',
            collection_type: 'integer',
            title: 'Please enter your 4-digit PIN.',
            min_number: 0, max_number: 9999, min_digits: 4, max_digits: 4,
            on_event: {
              tool: 'verify_customer_pin',
              parameters: {},
              map_input_to: 'pin',
            },
          },
        },
      };
    }
  },
};

export const welcomeTools = [welcomeCustomerTool, verifyCustomerPinTool];
```

### Python - welcome.py

```python
from .customer_database import get_customer_profile_by_phone, verify_customer_pin
from .global_store import set_global_variable


async def welcome_customer_handler(args: dict, extra: dict) -> dict:
    _meta = extra.get("_meta", {})
    telephone_number = _meta.get("com.ibm.orchestrate/context", {}).get("telephoneNumber")
    customer_profile = get_customer_profile_by_phone(telephone_number) if telephone_number else None

    if not telephone_number or not customer_profile:
        return {
            "content": [{"type": "text", "text": "Welcome! I was unable to find your account. Let me connect you with an agent.", "annotations": {"audience": ["user"]}}],
            "_meta": {
                "com.ibm.orchestrate/extensions": {
                    "transfer_to_live_agent": {
                        "message_to_human_agent": "Customer account could not be found.",
                        "agent_available": "Please wait while I connect you to an agent.",
                        "agent_unavailable": "No agents are online. Please try again later.",
                    }
                }
            },
        }

    return {
        "content": [{"type": "text", "text": f"Hello {customer_profile.first_name} {customer_profile.last_name}! Welcome to CustomerCare Banking.", "annotations": {"audience": ["user"]}}],
        "_meta": {
            "com.ibm.orchestrate/widget": {
                "type": "number", "collection_type": "integer",
                "title": "For your security, please enter your 4-digit PIN.",
                "min_number": 0, "max_number": 9999, "min_digits": 4, "max_digits": 4,
                "on_event": {"tool": "verify_customer_pin", "parameters": {}, "map_input_to": "pin"},
            }
        },
    }


async def verify_customer_pin_handler(args: dict, extra: dict) -> dict:
    pin = args.get("pin", "")
    _meta = extra.get("_meta", {})
    telephone_number = _meta.get("com.ibm.orchestrate/context", {}).get("telephoneNumber")
    thread_id = _meta.get("com.ibm.orchestrate/systemcontext", {}).get("thread_id")

    is_valid = telephone_number and verify_customer_pin(telephone_number, pin)

    if is_valid and telephone_number:
        customer_profile = get_customer_profile_by_phone(telephone_number)
        if thread_id and customer_profile:
            set_global_variable(thread_id, "customerId", customer_profile.customer_id)

        return {
            "content": [{"type": "text", "text": "Thank you! Your PIN has been verified. How can I assist you today?", "annotations": {"audience": ["user"]}}],
            "_meta": {"refreshThreadCapabilities": thread_id},
        }
    else:
        return {
            "content": [{"type": "text", "text": "Incorrect PIN. Please try again.", "annotations": {"audience": ["user"]}}],
            "_meta": {
                "com.ibm.orchestrate/widget": {
                    "type": "number", "collection_type": "integer",
                    "title": "Please enter your 4-digit PIN.",
                    "min_number": 0, "max_number": 9999, "min_digits": 4, "max_digits": 4,
                    "on_event": {"tool": "verify_customer_pin", "parameters": {}, "map_input_to": "pin"},
                }
            },
        }


welcome_customer_tool = {
    "name": "welcome_customer",
    "config": {
        "title": "Welcome Customer",
        "description": "Welcome the customer and authenticate them with their PIN",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
        "_meta": {"welcomeTool": True, "ui": {"visibility": ["app"]}},
    },
    "handler": welcome_customer_handler,
}

verify_customer_pin_tool = {
    "name": "verify_customer_pin",
    "config": {
        "title": "Verify Customer PIN",
        "description": "Verify the PIN entered by the customer",
        "inputSchema": {
            "type": "object",
            "properties": {"pin": {"type": "string", "description": "PIN entered by the customer"}},
            "required": ["pin"],
        },
    },
    "handler": verify_customer_pin_handler,
}

welcome_tools = [welcome_customer_tool, verify_customer_pin_tool]
```

---

## 6. Personal Banking Tools

**Patterns demonstrated:** Direct response (`audience: ['user']`), hybrid response (model + user content), transaction pattern (two-step confirm/cancel), options widget, datetime widget, confirmation widget, tool chaining (`nextTool`), MCP resources, model visibility (`visibility: ['app']`), local store for transaction state.

### TypeScript - personalBanking.ts

```typescript
import { z } from 'zod';
import { PersonalBankingService } from './personalBankingService';
import { deleteLocalVariable, getLocalVariable, setLocalVariable } from './localStore';

/**
 * PATTERN: Direct Response (audience: ['user'])
 * Data goes directly to user, no LLM rewriting. Zero hallucination risk.
 */
export const getAccountBalanceTool = {
  name: 'get_account_balance',
  config: {
    title: 'Get Account Balance',
    description: 'Retrieve current account balance for the authenticated customer',
    inputSchema: {
      accountType: z.enum(['checking', 'savings']).describe('Type of account'),
    },
    outputSchema: {
      customerId: z.string(), accountType: z.string(),
      balance: z.number(), currency: z.string(), asOfDate: z.string(),
    },
  },
  handler: async ({ customerId, accountType }: { customerId: string; accountType: string }, extra: any) => {
    const accountBalance = PersonalBankingService.getAccountBalance(customerId, accountType);
    return {
      content: [{
        type: 'text',
        text: `Account Balance:\nCustomer ID: ${accountBalance.customerId}\nAccount Type: ${accountBalance.accountType}\nBalance: $${accountBalance.balance.toFixed(2)} ${accountBalance.currency}\nAs of: ${accountBalance.asOfDate}`,
        annotations: { audience: ['user'] },
      }],
      structuredContent: accountBalance,
    };
  },
};

/**
 * PATTERN: Hybrid Response (model gets context, user gets exact data)
 * No audience annotation on text = model sees it AND user sees it.
 * structuredContent is always visible to model.
 */
export const getAccountStatementTool = {
  name: 'get_account_statement',
  config: {
    title: 'Get Account Statement',
    description: 'Retrieve recent account statement with transactions',
    inputSchema: {
      accountType: z.enum(['checking', 'savings']).describe('Type of account'),
      days: z.number().optional().describe('Number of days to retrieve (default: 30)'),
    },
    outputSchema: {
      customerId: z.string(), accountType: z.string(),
      startDate: z.string(), endDate: z.string(),
      transactions: z.array(z.object({
        date: z.string(), description: z.string(), amount: z.number(), balance: z.number(),
      })),
    },
  },
  handler: async ({ customerId, accountType, days = 30 }: { customerId: string; accountType: string; days?: number }, extra: any) => {
    const accountStatement = PersonalBankingService.getAccountStatement(customerId, accountType, days);
    const transactionText = accountStatement.transactions
      .map(t => `  ${t.date} | ${t.description.padEnd(35)} | ${t.amount >= 0 ? '+' : ''}$${t.amount.toFixed(2).padStart(10)} | Balance: $${t.balance.toFixed(2)}`)
      .join('\n');

    return {
      content: [{
        type: 'text',
        text: `Account Statement:\nCustomer ID: ${accountStatement.customerId}\nAccount Type: ${accountStatement.accountType}\nPeriod: ${accountStatement.startDate} to ${accountStatement.endDate}\n\nRecent Transactions:\n${transactionText}`,
      }],
      structuredContent: accountStatement,
    };
  },
};

/**
 * PATTERN: Transaction (Step 1 - Prepare)
 * Multi-step widget collection: options picker -> options picker -> date picker -> confirmation
 * Uses tool chaining (nextTool) for locked account -> agent handoff
 * Stores transaction in LOCAL store (isolated to this MCP server)
 */
export const prepareTransferTool = {
  name: 'prepare_money_transfer',
  config: {
    title: 'Prepare Money Transfer',
    description: 'Prepare a transfer between your accounts.',
    inputSchema: {
      fromAccountId: z.string().optional().describe('Account ID to transfer from'),
      toAccountId: z.string().optional().describe('Account ID to transfer to'),
      amount: z.number().min(0.01).describe('Amount to transfer in USD'),
      scheduledDate: z.string().optional().describe('Date in YYYY-MM-DD format'),
      memo: z.string().optional().describe('Optional memo'),
    },
  },
  _meta: { ui: { resourceUri: 'ui://ibm.com/orchestrate/widget' } },
  handler: async (args: {
    customerId: string; fromAccountId?: string; toAccountId?: string;
    amount: number; scheduledDate?: string; memo?: string;
  }, extra: any) => {
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
    if (!threadId) throw new Error('Thread ID is required');

    const allAccounts = PersonalBankingService.getAccounts(args.customerId);

    // Step 1: If fromAccountId missing, show "from" account picker
    if (!args.fromAccountId) {
      const fromAccounts = allAccounts.filter(acc => acc.canTransferFrom && acc.accountId !== args.toAccountId);
      return {
        _meta: {
          'com.ibm.orchestrate/widget': {
            type: 'options',
            title: 'Select Account to Transfer From',
            options: fromAccounts.map(acc => ({
              value: acc.accountId,
              label: `${acc.accountName}${acc.accountHolder ? ` (${acc.accountHolder})` : ''}`,
              description: `${acc.accountType} - ${acc.accountId}`,
            })),
            on_event: {
              tool: 'prepare_money_transfer',
              parameters: { ...args },
              map_input_to: 'fromAccountId',
            },
          },
        },
      };
    }

    // Step 2: Check if account is locked -> tool chain to handoff
    const selectedFromAccount = allAccounts.find(acc => acc.accountId === args.fromAccountId);
    if (selectedFromAccount?.isLocked) {
      return {
        content: [{
          type: 'text',
          text: `Your ${selectedFromAccount.accountName} account is currently locked. Let me connect you with an agent.`,
          annotations: { audience: ['user'] },
        }],
        _meta: {
          nextTool: {
            tool: 'request_agent_handoff',
            arguments: { reason: `Locked account: ${selectedFromAccount.accountName}` },
          },
        },
      };
    }

    // Step 3: If toAccountId missing, show "to" account picker
    if (!args.toAccountId) {
      const toAccounts = allAccounts.filter(acc => acc.canTransferTo && acc.accountId !== args.fromAccountId);
      return {
        _meta: {
          'com.ibm.orchestrate/widget': {
            type: 'options',
            title: 'Select Account to Transfer To',
            options: toAccounts.map(acc => ({
              value: acc.accountId,
              label: `${acc.accountName}${acc.accountHolder ? ` (${acc.accountHolder})` : ''}`,
              description: `${acc.accountType} - ${acc.accountId}`,
            })),
            on_event: {
              tool: 'prepare_money_transfer',
              parameters: { ...args },
              map_input_to: 'toAccountId',
            },
          },
        },
      };
    }

    // Step 4: If scheduledDate missing, show date picker
    if (!args.scheduledDate) {
      const today = new Date();
      const minDate = new Date(today); minDate.setDate(today.getDate() + 3);
      const maxDate = new Date(today); maxDate.setDate(today.getDate() + 30);
      return {
        _meta: {
          'com.ibm.orchestrate/widget': {
            type: 'datetime',
            collection_type: 'date',
            title: 'Select Transfer Date',
            min_datetime: minDate.toISOString().split('T')[0],
            max_datetime: maxDate.toISOString().split('T')[0],
            on_event: {
              tool: 'prepare_money_transfer',
              parameters: { ...args },
              map_input_to: 'scheduledDate',
            },
          },
        },
      };
    }

    // Step 5: All info collected -- validate and show confirmation
    const { fromAccount, toAccount } = PersonalBankingService.validateTransfer(
      args.customerId, args.fromAccountId, args.toAccountId, args.amount,
    );
    const transactionId = `TXN-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Store in LOCAL store (isolated per MCP server)
    setLocalVariable(threadId, `transaction_${transactionId}`, {
      customerId: args.customerId, transactionId,
      fromAccountId: args.fromAccountId, fromAccountName: fromAccount.accountName,
      toAccountId: args.toAccountId, toAccountName: toAccount.accountName,
      amount: args.amount, scheduledDate: args.scheduledDate, memo: args.memo,
    });

    return {
      _meta: {
        'com.ibm.orchestrate/widget': {
          type: 'confirmation',
          title: 'Confirm Transfer',
          confirmation_text: `## Confirm Transfer\n\n- **From:** ${fromAccount.accountName} (${args.fromAccountId})\n- **To:** ${toAccount.accountName} (${args.toAccountId})\n- **Amount:** $${args.amount.toFixed(2)}\n- **Date:** ${args.scheduledDate}\n\n**Transaction ID:** ${transactionId}`,
          on_confirm: {
            tool: 'confirm_or_cancel_money_transfer',
            parameters: { transactionId, action: 'confirm' },
          },
          on_cancel: {
            tool: 'confirm_or_cancel_money_transfer',
            parameters: { transactionId, action: 'cancel' },
          },
        },
      },
    };
  },
};

/**
 * PATTERN: Transaction (Step 2 - Confirm/Cancel)
 * Hidden from model (visibility: ['app']) -- only UI widget can call this.
 * Retrieves transaction from local store, verifies ownership, processes.
 */
export const confirmOrCancelTransferTool = {
  name: 'confirm_or_cancel_money_transfer',
  config: {
    title: 'Confirm or Cancel Money Transfer',
    description: 'Handle user action for a previously prepared money transfer.',
    inputSchema: {
      transactionId: z.string().describe('Transaction ID from prepare_money_transfer'),
      action: z.enum(['confirm', 'cancel']).describe('User action'),
    },
    _meta: {
      ui: { visibility: ['app'] },  // Hidden from model
    },
  },
  handler: async (params: { customerId: string; transactionId: string; action: 'confirm' | 'cancel' }, extra: any) => {
    const { customerId, transactionId, action } = params;
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
    if (!threadId) throw new Error('Thread ID is required');

    const transaction = getLocalVariable(threadId, `transaction_${transactionId}`);
    if (!transaction) throw new Error(`Transaction ${transactionId} not found.`);
    if (transaction.customerId !== customerId) throw new Error('Transaction does not belong to this customer');

    deleteLocalVariable(threadId, `transaction_${transactionId}`);

    if (action === 'cancel') {
      return {
        content: [
          { type: 'text', text: `Transfer Cancelled\n\nTransaction ID: ${transactionId}\nNo funds were moved.`, annotations: { audience: ['user'] } },
          { type: 'text', text: `Transfer ${transactionId} cancelled by user.`, annotations: { audience: ['assistant'] } },
        ],
      };
    }

    const transferResult = PersonalBankingService.transferMoney(
      transaction.customerId, transaction.fromAccountId, transaction.toAccountId,
      transaction.amount, transaction.scheduledDate, transaction.memo,
    );

    return {
      content: [{
        type: 'text',
        text: `Transfer Confirmed!\n\nConfirmation: ${transferResult.transferId}\n- From: ${transaction.fromAccountName}\n- To: ${transaction.toAccountName}\n- Amount: $${transaction.amount.toFixed(2)}`,
        annotations: { audience: ['user'] },
      }],
    };
  },
};

/**
 * PATTERN: MCP Resource
 * Provides account list as a resource the model can read.
 */
export const availableAccountsResource = {
  uri: 'banking://accounts/available',
  name: 'Available Accounts',
  description: 'List of accounts for transfers, including IDs, names, types, and transfer capabilities',
  mimeType: 'application/json',
  handler: async (args: { customerId: string }, extra: any) => {
    const accounts = PersonalBankingService.getAccounts(args.customerId);
    const accountList = accounts.map(acc => {
      const holder = acc.accountHolder ? ` (${acc.accountHolder})` : '';
      return `${acc.accountId} - ${acc.accountName}${holder}\n  Type: ${acc.accountType} | From: ${acc.canTransferFrom ? 'Y' : 'N'} | To: ${acc.canTransferTo ? 'Y' : 'N'}`;
    }).join('\n\n');

    return {
      contents: [{ uri: 'banking://accounts/available', mimeType: 'application/json', text: `Available Accounts:\n\n${accountList}` }],
      structuredContent: accounts,
    };
  },
};

export const personalBankingTools = [getAccountBalanceTool, getAccountStatementTool, prepareTransferTool, confirmOrCancelTransferTool];
export const personalBankingResources = [availableAccountsResource];
```

### Python - personal_banking.py

```python
from datetime import datetime, timedelta
import random
import string

from .personal_banking_service import PersonalBankingService
from .local_store import set_local_variable, get_local_variable, delete_local_variable


async def get_account_balance_handler(args: dict, extra: dict) -> dict:
    """PATTERN: Direct Response (audience: ['user'])"""
    customer_id = args.get("customerId")
    account_type = args.get("account_type", "")
    balance = PersonalBankingService.get_account_balance(customer_id, account_type)
    return {
        "content": [{"type": "text", "text": f"Account Balance:\nType: {balance['account_type']}\nBalance: ${balance['balance']:.2f} {balance['currency']}", "annotations": {"audience": ["user"]}}],
        "structuredContent": balance,
    }


async def get_account_statement_handler(args: dict, extra: dict) -> dict:
    """PATTERN: Hybrid Response (model + user both see content)"""
    customer_id = args.get("customerId")
    account_type = args.get("account_type", "")
    days = args.get("days", 30)
    statement = PersonalBankingService.get_account_statement(customer_id, account_type, days)
    text = "\n".join(f"  {t['date']} | {t['description']:<35} | ${t['amount']:>10.2f}" for t in statement["transactions"])
    return {
        "content": [{"type": "text", "text": f"Account Statement:\nPeriod: {statement['start_date']} to {statement['end_date']}\n\n{text}"}],
        "structuredContent": statement,
    }


async def prepare_money_transfer_handler(args: dict, extra: dict) -> dict:
    """PATTERN: Transaction Step 1 -- multi-step widget collection + confirmation"""
    customer_id = args.get("customerId")
    amount = args.get("amount", 0)
    from_id = args.get("from_account_id")
    to_id = args.get("to_account_id")
    scheduled_date = args.get("scheduled_date")
    memo = args.get("memo")

    _meta = extra.get("_meta", {})
    thread_id = _meta.get("com.ibm.orchestrate/systemcontext", {}).get("thread_id")
    if not thread_id:
        raise ValueError("Thread ID is required")

    all_accounts = PersonalBankingService.get_accounts(customer_id)

    # Step 1: From account picker
    if not from_id:
        options = [{"value": a.account_id, "label": a.account_name, "description": f"{a.account_type} - {a.account_id}"} for a in all_accounts if a.can_transfer_from and a.account_id != to_id]
        return {"_meta": {"com.ibm.orchestrate/widget": {"type": "options", "title": "Select Account to Transfer From", "options": options, "on_event": {"tool": "prepare_money_transfer", "parameters": {k: v for k, v in {"amount": amount, "from_account_id": from_id, "to_account_id": to_id, "scheduled_date": scheduled_date, "memo": memo}.items() if v is not None}, "map_input_to": "from_account_id"}}}}

    # Step 2: Locked account -> chain to handoff
    from_account = next((a for a in all_accounts if a.account_id == from_id), None)
    if from_account and from_account.is_locked:
        return {"content": [{"type": "text", "text": f"Your {from_account.account_name} account is locked.", "annotations": {"audience": ["user"]}}], "_meta": {"nextTool": {"tool": "request_agent_handoff", "arguments": {"reason": f"Locked account: {from_account.account_name}"}}}}

    # Step 3: To account picker
    if not to_id:
        options = [{"value": a.account_id, "label": a.account_name, "description": f"{a.account_type} - {a.account_id}"} for a in all_accounts if a.can_transfer_to and a.account_id != from_id]
        return {"_meta": {"com.ibm.orchestrate/widget": {"type": "options", "title": "Select Account to Transfer To", "options": options, "on_event": {"tool": "prepare_money_transfer", "parameters": {k: v for k, v in {"amount": amount, "from_account_id": from_id, "to_account_id": to_id, "scheduled_date": scheduled_date, "memo": memo}.items() if v is not None}, "map_input_to": "to_account_id"}}}}

    # Step 4: Date picker
    if not scheduled_date:
        min_d = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        max_d = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        return {"_meta": {"com.ibm.orchestrate/widget": {"type": "datetime", "collection_type": "date", "title": "Select Transfer Date", "min_datetime": min_d, "max_datetime": max_d, "on_event": {"tool": "prepare_money_transfer", "parameters": {k: v for k, v in {"amount": amount, "from_account_id": from_id, "to_account_id": to_id, "scheduled_date": scheduled_date, "memo": memo}.items() if v is not None}, "map_input_to": "scheduled_date"}}}}

    # Step 5: Validate and show confirmation
    validation = PersonalBankingService.validate_transfer(customer_id, from_id, to_id, amount)
    fa, ta = validation["from_account"], validation["to_account"]
    txn_id = f"TXN-{int(datetime.now().timestamp()*1000)}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=9))}"

    set_local_variable(thread_id, f"transaction_{txn_id}", {"customer_id": customer_id, "transaction_id": txn_id, "from_account_id": from_id, "from_account_name": fa.account_name, "to_account_id": to_id, "to_account_name": ta.account_name, "amount": amount, "scheduled_date": scheduled_date, "memo": memo})

    return {"_meta": {"com.ibm.orchestrate/widget": {"type": "confirmation", "title": "Confirm Transfer", "confirmation_text": f"## Confirm Transfer\n\n- **From:** {fa.account_name}\n- **To:** {ta.account_name}\n- **Amount:** ${amount:.2f}\n- **Date:** {scheduled_date}\n\n**Transaction ID:** {txn_id}", "on_confirm": {"tool": "confirm_or_cancel_money_transfer", "parameters": {"transaction_id": txn_id, "action": "confirm"}}, "on_cancel": {"tool": "confirm_or_cancel_money_transfer", "parameters": {"transaction_id": txn_id, "action": "cancel"}}}}}


async def confirm_or_cancel_handler(args: dict, extra: dict) -> dict:
    """PATTERN: Transaction Step 2 -- hidden from model"""
    customer_id = args.get("customerId")
    txn_id = args.get("transaction_id", "")
    action = args.get("action", "")
    _meta = extra.get("_meta", {})
    thread_id = _meta.get("com.ibm.orchestrate/systemcontext", {}).get("thread_id")
    if not thread_id:
        raise ValueError("Thread ID is required")

    txn = get_local_variable(thread_id, f"transaction_{txn_id}")
    if not txn:
        raise ValueError(f"Transaction {txn_id} not found.")
    if txn["customer_id"] != customer_id:
        raise ValueError("Transaction does not belong to this customer")

    delete_local_variable(thread_id, f"transaction_{txn_id}")

    if action == "cancel":
        return {"content": [
            {"type": "text", "text": f"Transfer Cancelled.\nTransaction ID: {txn_id}", "annotations": {"audience": ["user"]}},
            {"type": "text", "text": f"Transfer {txn_id} cancelled by user.", "annotations": {"audience": ["assistant"]}},
        ]}

    result = PersonalBankingService.transfer_money(txn["customer_id"], txn["from_account_id"], txn["to_account_id"], txn["amount"], txn.get("scheduled_date"), txn.get("memo"))
    return {"content": [{"type": "text", "text": f"Transfer Confirmed!\nConfirmation: {result.transfer_id}\nAmount: ${txn['amount']:.2f}", "annotations": {"audience": ["user"]}}]}


# Tool definitions
get_account_balance_tool = {"name": "get_account_balance", "config": {"title": "Get Account Balance", "description": "Retrieve current account balance", "inputSchema": {"type": "object", "properties": {"account_type": {"type": "string", "description": "Account type (checking, savings)"}}, "required": ["account_type"]}}, "handler": get_account_balance_handler}

get_account_statement_tool = {"name": "get_account_statement", "config": {"title": "Get Account Statement", "description": "Retrieve recent account statement", "inputSchema": {"type": "object", "properties": {"account_type": {"type": "string"}, "days": {"type": "integer"}}, "required": ["account_type"]}}, "handler": get_account_statement_handler}

prepare_money_transfer_tool = {"name": "prepare_money_transfer", "config": {"title": "Prepare Money Transfer", "description": "Prepare a transfer between accounts", "inputSchema": {"type": "object", "properties": {"amount": {"type": "number"}, "from_account_id": {"type": "string"}, "to_account_id": {"type": "string"}, "scheduled_date": {"type": "string"}, "memo": {"type": "string"}}, "required": ["amount"]}, "_meta": {"ui": {"resourceUri": "ui://ibm.com/orchestrate/widget"}}}, "handler": prepare_money_transfer_handler}

confirm_or_cancel_tool = {"name": "confirm_or_cancel_money_transfer", "config": {"title": "Confirm or Cancel Transfer", "description": "Handle confirm/cancel for prepared transfer", "inputSchema": {"type": "object", "properties": {"transaction_id": {"type": "string"}, "action": {"type": "string"}}, "required": ["transaction_id", "action"]}, "_meta": {"ui": {"visibility": ["app"]}}}, "handler": confirm_or_cancel_handler}

personal_banking_tools = [get_account_balance_tool, get_account_statement_tool, prepare_money_transfer_tool, confirm_or_cancel_tool]

# MCP resource
available_accounts_resource = {"uri": "banking://accounts/available", "name": "Available Accounts", "description": "List of accounts for transfers", "mimeType": "text/plain", "handler": lambda args, extra: PersonalBankingService.get_accounts(args.get("customerId"))}
personal_banking_resources = [available_accounts_resource]
```

---

## 7. Agent Handoff Tools

**Patterns demonstrated:** Options widget for user choice, `transfer_to_live_agent` extension, hidden step-2 tool.

### TypeScript - handoff.ts

```typescript
import { z } from 'zod';

export const requestAgentHandoffTool = {
  name: 'request_agent_handoff',
  config: {
    title: 'Request Agent Handoff',
    description: 'Initiate a handoff to a human agent.',
    inputSchema: {
      reason: z.string().optional().describe('Reason for handoff'),
    },
  },
  handler: async ({ customerId, reason }: { customerId?: string; reason?: string }, extra: any) => {
    const contextMessage = reason
      ? `User requested agent assistance. Reason: ${reason}. Customer: ${customerId || 'not authenticated'}`
      : `User requested to speak with an agent. Customer: ${customerId || 'not authenticated'}`;

    return {
      content: [{
        type: 'text',
        text: "I'd be happy to connect you with an agent. How would you like to proceed?",
        annotations: { audience: ['user'] },
      }],
      _meta: {
        'com.ibm.orchestrate/widget': {
          type: 'options',
          title: 'Choose Connection Type',
          options: [
            { value: 'realtime', label: 'Connect Now' },
            { value: 'callback', label: 'Request Callback' },
          ],
          on_event: {
            tool: 'process_agent_handoff_choice',
            parameters: { contextMessage },
            map_input_to: 'handoffType',
          },
        },
      },
    };
  },
};

export const processAgentHandoffChoiceTool = {
  name: 'process_agent_handoff_choice',
  config: {
    title: 'Process Agent Handoff Choice',
    description: 'Process handoff type selection',
    inputSchema: {
      handoffType: z.enum(['realtime', 'callback']),
      contextMessage: z.string(),
    },
    _meta: { ui: { visibility: ['app'] } },
  },
  handler: async ({ handoffType, contextMessage }: { handoffType: 'realtime' | 'callback'; contextMessage: string }, extra: any) => {
    if (handoffType === 'realtime') {
      return {
        content: [{ type: 'text', text: 'Connecting you to an agent...', annotations: { audience: ['user'] } }],
        _meta: {
          'com.ibm.orchestrate/extensions': {
            transfer_to_live_agent: {
              message_to_human_agent: contextMessage,
              agent_available: 'Please wait while I connect you to an agent.',
              agent_unavailable: "No agents are online. Please try again later or request a callback.",
            },
          },
        },
      };
    }
    return {
      content: [{ type: 'text', text: "Callback request submitted. An agent will contact you within one business day.", annotations: { audience: ['user'] } }],
    };
  },
};

export const handoffTools = [requestAgentHandoffTool, processAgentHandoffChoiceTool];
```

### Python - handoff.py

```python
async def request_agent_handoff_handler(args: dict, extra: dict) -> dict:
    reason = args.get("reason")
    customer_id = args.get("customerId")
    ctx = f"Reason: {reason}. Customer: {customer_id or 'not authenticated'}" if reason else f"User requested agent. Customer: {customer_id or 'not authenticated'}"
    return {
        "content": [{"type": "text", "text": "How would you like to connect with an agent?", "annotations": {"audience": ["user"]}}],
        "_meta": {"com.ibm.orchestrate/widget": {"type": "options", "title": "Choose Connection Type", "options": [{"value": "realtime", "label": "Connect Now"}, {"value": "callback", "label": "Request Callback"}], "on_event": {"tool": "process_agent_handoff_choice", "parameters": {"context_message": ctx}, "map_input_to": "handoff_type"}}},
    }

async def process_agent_handoff_choice_handler(args: dict, extra: dict) -> dict:
    if args.get("handoff_type") == "realtime":
        return {
            "content": [{"type": "text", "text": "Connecting you to an agent...", "annotations": {"audience": ["user"]}}],
            "_meta": {"com.ibm.orchestrate/extensions": {"transfer_to_live_agent": {"message_to_human_agent": args.get("context_message", ""), "agent_available": "Please wait.", "agent_unavailable": "No agents online."}}},
        }
    return {"content": [{"type": "text", "text": "Callback request submitted.", "annotations": {"audience": ["user"]}}]}

request_agent_handoff_tool = {"name": "request_agent_handoff", "config": {"title": "Request Agent Handoff", "description": "Initiate handoff to human agent", "inputSchema": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": []}}, "handler": request_agent_handoff_handler}
process_agent_handoff_choice_tool = {"name": "process_agent_handoff_choice", "config": {"title": "Process Handoff Choice", "description": "Process handoff type selection", "inputSchema": {"type": "object", "properties": {"handoff_type": {"type": "string"}, "context_message": {"type": "string"}}, "required": ["handoff_type", "context_message"]}, "_meta": {"ui": {"visibility": ["app"]}}}, "handler": process_agent_handoff_choice_handler}
handoff_tools = [request_agent_handoff_tool, process_agent_handoff_choice_tool]
```

---

## 8. Knowledge/RAG Tools

**Patterns demonstrated:** Conditional tool registration, OpenSearch integration, configurable field mappings, `structuredContent` for model reasoning.

### TypeScript - knowledge.ts + knowledgeService.ts

```typescript
// knowledge.ts
import { z } from 'zod';
import * as logger from './logger';
import { KnowledgeService, OpenSearchConnection } from './knowledgeService';

function getOpenSearchConfig(): OpenSearchConnection {
  return {
    url: process.env.OPENSEARCH_ENDPOINT || "https://localhost",
    port: process.env.OPENSEARCH_PORT || "9200",
    index: process.env.INDEX_NAME || 'knowledge_vector_index',
    credentials: {
      username: process.env.OPENSEARCH_USERNAME || "admin",
      password: process.env.OPENSEARCH_PASSWORD
    },
    field_mapping: {
      title: process.env.OPENSEARCH_FIELD_TITLE || 'title',
      body: process.env.OPENSEARCH_FIELD_BODY || 'passage_text',
      url: process.env.OPENSEARCH_FIELD_URL || 'url',
    }
  };
}

export const searchKnowledgeTool = {
  name: 'search_knowledge_base',
  config: {
    title: 'Search Knowledge Base',
    description: process.env.SEARCH_TOOL_DESCRIPTION || 'Search the knowledge base for relevant information.',
    inputSchema: {
      query: z.string().min(1).describe('Search query'),
    },
    outputSchema: {
      query: z.string(),
      results: z.array(z.object({ title: z.string(), body: z.string(), url: z.string().optional(), score: z.number().optional() })),
      totalResults: z.number(),
      searchTime: z.number(),
    },
  },
  handler: async ({ query }: { query: string }, extra: any) => {
    try {
      const config = getOpenSearchConfig();
      const searchResult = await KnowledgeService.searchKnowledge(query, config);
      return {
        content: [{ type: 'text', text: `Found ${searchResult.totalResults} result(s) for "${query}" in ${searchResult.searchTime.toFixed(3)}s\n\n${JSON.stringify(searchResult.results)}` }],
        structuredContent: searchResult,
      };
    } catch (error) {
      return { content: [{ type: 'text', text: `Error: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },
};

export const knowledgeTools = [searchKnowledgeTool];
```

```typescript
// knowledgeService.ts
import { Agent } from 'undici';

export interface OpenSearchConnection {
  url: string;
  port?: string;
  index: string;
  credentials: { username?: string; password?: string };
  field_mapping: { title: string; body: string; url?: string };
}

export class KnowledgeService {
  static async searchKnowledge(query: string, config: OpenSearchConnection) {
    if (!query?.trim()) throw new Error('Search query is required');

    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (config.credentials.username && config.credentials.password) {
      headers['Authorization'] = `Basic ${Buffer.from(`${config.credentials.username}:${config.credentials.password}`).toString('base64')}`;
    }

    let queryBody = process.env.OPENSEARCH_QUERY_BODY
      ? JSON.parse(process.env.OPENSEARCH_QUERY_BODY)
      : { _source: { excludes: ["passage_embedding"] }, query: { neural: { passage_embedding: { query_text: '$QUERY', k: 10 } } } };

    const queryBodyStr = JSON.stringify(queryBody).replace(/\$QUERY/g, query);
    const portPart = config.port ? `:${config.port}` : '';
    const url = `${config.url}${portPart}/${config.index}/_search`;

    const startTime = Date.now();
    const response = await fetch(url, {
      method: 'POST', headers, body: queryBodyStr,
      // @ts-ignore
      dispatcher: new Agent({ connect: { rejectUnauthorized: false } })
    });

    if (!response.ok) throw new Error(`OpenSearch failed: ${response.status}`);
    const data = await response.json() as any;
    const elapsed = (Date.now() - startTime) / 1000;

    const results = (data.hits?.hits || []).map((hit: any) => ({
      title: hit._source?.[config.field_mapping.title] || '',
      body: hit._source?.[config.field_mapping.body] || '',
      url: config.field_mapping.url ? hit._source?.[config.field_mapping.url] : undefined,
      id: String(hit._id),
      score: hit._score,
    }));

    return { query, results, totalResults: results.length, searchTime: elapsed };
  }
}
```

### Python - knowledge.py + knowledge_service.py

```python
# knowledge.py
import os, json
from .knowledge_service import KnowledgeService, get_opensearch_config
from . import logger

async def search_knowledge_handler(args: dict, extra: dict) -> dict:
    query = args.get("query", "")
    try:
        config = get_opensearch_config()
        result = await KnowledgeService.search_knowledge(query, config)
        return {
            "content": [{"type": "text", "text": f"Found {result.total_results} result(s) for \"{query}\""}],
            "structuredContent": {"query": result.query, "results": [{"title": r.title, "body": r.body, "url": r.url, "score": r.score} for r in result.results], "total_results": result.total_results, "search_time": result.search_time},
        }
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}

search_knowledge_tool = {"name": "search_knowledge_base", "config": {"title": "Search Knowledge Base", "description": os.getenv("SEARCH_TOOL_DESCRIPTION") or "Search the knowledge base.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}, "handler": search_knowledge_handler}
knowledge_tools = [search_knowledge_tool]
```

```python
# knowledge_service.py
import os, json, base64
from dataclasses import dataclass
from datetime import datetime
import httpx

@dataclass
class KnowledgeResult:
    title: str
    body: str
    url: str | None = None
    id: str | None = None
    score: float | None = None

@dataclass
class KnowledgeSearchResult:
    query: str
    results: list[KnowledgeResult]
    total_results: int
    search_time: float

@dataclass
class OpenSearchConnection:
    url: str
    port: str | None
    index: str
    credentials: dict
    field_mapping: dict

def get_opensearch_config() -> OpenSearchConnection:
    return OpenSearchConnection(
        url=os.getenv("OPENSEARCH_ENDPOINT", "https://localhost"),
        port=os.getenv("OPENSEARCH_PORT", "9200"),
        index=os.getenv("INDEX_NAME", "knowledge_vector_index"),
        credentials={"username": os.getenv("OPENSEARCH_USERNAME", "admin"), "password": os.getenv("OPENSEARCH_PASSWORD")},
        field_mapping={"title": os.getenv("OPENSEARCH_FIELD_TITLE", "title"), "body": os.getenv("OPENSEARCH_FIELD_BODY", "passage_text"), "url": os.getenv("OPENSEARCH_FIELD_URL", "url")},
    )

class KnowledgeService:
    @staticmethod
    async def search_knowledge(query: str, config: OpenSearchConnection) -> KnowledgeSearchResult:
        if not query or not query.strip():
            raise ValueError("Search query is required")

        headers = {"Content-Type": "application/json"}
        if config.credentials.get("username") and config.credentials.get("password"):
            creds = base64.b64encode(f"{config.credentials['username']}:{config.credentials['password']}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"

        query_body = json.loads(os.getenv("OPENSEARCH_QUERY_BODY")) if os.getenv("OPENSEARCH_QUERY_BODY") else {"_source": {"excludes": ["passage_embedding"]}, "query": {"neural": {"passage_embedding": {"query_text": "$QUERY", "k": 10}}}}
        query_body_str = json.dumps(query_body).replace("$QUERY", query)

        port_part = f":{config.port}" if config.port else ""
        url = f"{config.url}{port_part}/{config.index}/_search"

        start = datetime.now()
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, headers=headers, json=json.loads(query_body_str))
            if response.status_code != 200:
                raise ValueError(f"OpenSearch failed: {response.status_code}")
            data = response.json()

        elapsed = (datetime.now() - start).total_seconds()
        results = [KnowledgeResult(title=h.get("_source", {}).get(config.field_mapping["title"], ""), body=h.get("_source", {}).get(config.field_mapping["body"], ""), url=h.get("_source", {}).get(config.field_mapping.get("url")), id=str(h.get("_id")), score=h.get("_score")) for h in data.get("hits", {}).get("hits", [])]
        return KnowledgeSearchResult(query=query, results=results, total_results=len(results), search_time=elapsed)
```

---

## 9. Service Layer Patterns

Service modules contain business logic and mock data. Replace mock data with your actual data source. The interfaces and method signatures define the contract.

### TypeScript - personalBankingService.ts (interfaces + signatures)

```typescript
export interface Account {
  accountId: string;
  accountName: string;
  accountType: string;
  canTransferFrom: boolean;
  canTransferTo: boolean;
  isLocked: boolean;
  accountHolder?: string;
}

export interface TransferResult {
  customerId: string;
  fromAccountId: string;
  toAccountId: string;
  amount: number;
  scheduledDate?: string;
  memo?: string;
  transferId: string;
  status: string;
  timestamp: string;
}

export class PersonalBankingService {
  /** Get list of accounts for a customer */
  static getAccounts(customerId: string): Account[] {
    // Replace with database query
    return [/* mock account data */];
  }

  /** Get account balance by account type */
  static getAccountBalance(customerId: string, accountType: string): {
    customerId: string; accountType: string; balance: number; currency: string; asOfDate: string;
  } {
    // Replace with actual balance lookup
    return { customerId, accountType, balance: 5432.18, currency: 'USD', asOfDate: new Date().toISOString() };
  }

  /** Get account statement with transactions */
  static getAccountStatement(customerId: string, accountType: string, days: number = 30): {
    customerId: string; accountType: string; startDate: string; endDate: string;
    transactions: Array<{ date: string; description: string; amount: number; balance: number }>;
  } {
    // Replace with actual statement query
    return { customerId, accountType, startDate: '', endDate: '', transactions: [] };
  }

  /** Transfer money between accounts */
  static transferMoney(customerId: string, fromAccountId: string, toAccountId: string, amount: number, scheduledDate?: string, memo?: string): TransferResult {
    if (fromAccountId === toAccountId) throw new Error('Cannot transfer to same account');
    const transferId = `TXN-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    return { customerId, fromAccountId, toAccountId, amount, scheduledDate, memo, transferId, status: scheduledDate ? 'scheduled' : 'completed', timestamp: new Date().toISOString() };
  }

  /** Validate a transfer request */
  static validateTransfer(customerId: string, fromAccountId: string, toAccountId: string, amount: number): { fromAccount: Account; toAccount: Account } {
    const accounts = this.getAccounts(customerId);
    const fromAccount = accounts.find(a => a.accountId === fromAccountId);
    const toAccount = accounts.find(a => a.accountId === toAccountId);
    if (!fromAccount) throw new Error(`Source account ${fromAccountId} not found`);
    if (!toAccount) throw new Error(`Destination account ${toAccountId} not found`);
    if (!fromAccount.canTransferFrom) throw new Error(`Cannot transfer from ${fromAccount.accountName}`);
    if (amount <= 0) throw new Error('Amount must be greater than zero');
    return { fromAccount, toAccount };
  }
}
```

### Python - personal_banking_service.py (interfaces + signatures)

```python
from dataclasses import dataclass
from datetime import datetime
import random, string

@dataclass
class Account:
    account_id: str
    account_name: str
    account_type: str
    can_transfer_from: bool
    can_transfer_to: bool
    is_locked: bool
    account_holder: str | None = None

@dataclass
class TransferResult:
    customer_id: str
    from_account_id: str
    to_account_id: str
    amount: float
    transfer_id: str
    status: str
    timestamp: str
    scheduled_date: str | None = None
    memo: str | None = None

class PersonalBankingService:
    @staticmethod
    def get_accounts(customer_id: str) -> list[Account]:
        """Replace with database query."""
        return []  # mock data

    @staticmethod
    def get_account_balance(customer_id: str, account_type: str) -> dict:
        """Replace with actual balance lookup."""
        return {"customer_id": customer_id, "account_type": account_type, "balance": 0.0, "currency": "USD", "as_of_date": datetime.now().isoformat()}

    @staticmethod
    def get_account_statement(customer_id: str, account_type: str, days: int = 30) -> dict:
        """Replace with actual statement query."""
        return {"customer_id": customer_id, "account_type": account_type, "start_date": "", "end_date": "", "transactions": []}

    @staticmethod
    def transfer_money(customer_id: str, from_id: str, to_id: str, amount: float, scheduled_date: str | None = None, memo: str | None = None) -> TransferResult:
        if from_id == to_id:
            raise ValueError("Cannot transfer to same account")
        tid = f"TXN-{int(datetime.now().timestamp()*1000)}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=9))}"
        return TransferResult(customer_id=customer_id, from_account_id=from_id, to_account_id=to_id, amount=amount, transfer_id=tid, status="scheduled" if scheduled_date else "completed", timestamp=datetime.now().isoformat(), scheduled_date=scheduled_date, memo=memo)

    @staticmethod
    def validate_transfer(customer_id: str, from_id: str, to_id: str, amount: float) -> dict:
        accounts = PersonalBankingService.get_accounts(customer_id)
        from_acc = next((a for a in accounts if a.account_id == from_id), None)
        to_acc = next((a for a in accounts if a.account_id == to_id), None)
        if not from_acc: raise ValueError(f"Source {from_id} not found")
        if not to_acc: raise ValueError(f"Destination {to_id} not found")
        if not from_acc.can_transfer_from: raise ValueError(f"Cannot transfer from {from_acc.account_name}")
        if amount <= 0: raise ValueError("Amount must be > 0")
        return {"from_account": from_acc, "to_account": to_acc}
```

### Optional Logger Modules

**TypeScript - logger.ts:**
```typescript
import pino from 'pino';
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: { target: 'pino-pretty', options: { colorize: true, translateTime: 'SYS:standard', ignore: 'pid,hostname' } },
});

export function info(message: string, data?: any): void { data ? logger.info(data, message) : logger.info(message); }
export function warn(message: string, data?: any): void { data ? logger.warn(data, message) : logger.warn(message); }
export function error(message: string, data?: any): void { data ? logger.error(data, message) : logger.error(message); }
```

**Python - logger.py:**
```python
import os, structlog

def configure_logging() -> None:
    structlog.configure(
        processors=[structlog.stdlib.add_log_level, structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer(colors=True)],
        wrapper_class=structlog.stdlib.BoundLogger, context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(), cache_logger_on_first_use=True,
    )

configure_logging()
_logger = structlog.get_logger()

def info(message: str, **data) -> None: _logger.info(message, **data) if data else _logger.info(message)
def warn(message: str, **data) -> None: _logger.warning(message, **data) if data else _logger.warning(message)
def error(message: str, **data) -> None: _logger.error(message, **data) if data else _logger.error(message)
```
