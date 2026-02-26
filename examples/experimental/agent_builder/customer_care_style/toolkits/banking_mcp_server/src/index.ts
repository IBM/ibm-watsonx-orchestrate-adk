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
  host: '0.0.0.0',
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
  // This ensures the capability is always available for dynamic resource discovery
  if (!customerId) {
    // Set empty resources handler only when no resources will be registered
    server.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return { resources: [] };
    });
    return server;
  }

  // Customer is authenticated - register product-specific tools
  const products = getCustomerProducts(customerId);

  // Check if we have any resources to register
  const hasResources = products.hasPersonalBanking;

  // If no resources, set empty handler before registering tools
  if (!hasResources) {
    server.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return { resources: [] };
    });
  }

  // Register personal banking tools if customer has personal banking
  if (products.hasPersonalBanking) {
    registerToolsWithCustomerId(server, personalBankingTools);

    // Register personal banking resources, used to tell the model about the accounts the user has
    registerResourcesWithCustomerId(server, personalBankingResources);
  }

  // Register mortgage tools if customer has mortgage
  if (products.hasMortgage) {
    registerToolsWithCustomerId(server, mortgageTools);
  }

  // Register credit card tools if customer has credit card
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
      headers: {
        'accept': req.headers['accept'],
        'content-type': req.headers['content-type'],
      },
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
    // Note: customerId is set by the welcome tool after successful PIN verification
    if (threadId) {
      customerId = getGlobalVariable(threadId, 'customerId');
    }

    // Create server instance with customer-specific tools
    // If customerId is undefined, only welcome and handoff tools will be registered
    const server = createCustomerServer(customerId);

    
    // Create transport in STATELESS mode (no session validation)
    // This allows each request to be handled independently
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,  // Stateless mode - no session validation
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
const PORT = process.env.PORT || 3004;
app.listen(PORT, () => {
  logger.info(`CustomerCare Banking MCP server listening on port ${PORT}`);
});
