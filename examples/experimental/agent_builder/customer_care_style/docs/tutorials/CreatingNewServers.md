# Creating New MCP Servers

This guide shows you how to create a completely new MCP server from scratch for your own domain. Use this when you want to build a customer care agent for a different industry or use case.

## Overview

Creating a new MCP server involves:

1. Setting up the project structure
2. Implementing the MCP protocol
3. Defining tools for your domain
4. Managing context and state
5. Configuring the agent runtime
6. Testing and iterating

## Project Setup

### 1. Create a New Node.js Project

```bash
# Create project directory
mkdir my-mcp-server
cd my-mcp-server

# Initialize npm project
npm init -y

# Install dependencies
npm install @modelcontextprotocol/sdk express pino pino-pretty

# Install dev dependencies
npm install --save-dev typescript @types/node @types/express ts-node
```

### 2. Configure TypeScript

Create `tsconfig.json`:

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

### 3. Set Up Package Scripts

Update `package.json`:

```json
{
  "name": "my-customer-care-server",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "ts-node src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  }
}
```

## Implementing the MCP Server

### 1. Create the Server Entry Point

**File: `src/index.ts`**

```typescript
#!/usr/bin/env node

import { Request, Response } from 'express';
import { createMcpExpressApp } from '@modelcontextprotocol/sdk/server/express.js';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import pino from 'pino';

// Create logger
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
    },
  },
});

// Create Express app with MCP support
const app = createMcpExpressApp();

/**
 * Create MCP server instance
 */
function createServer(): McpServer {
  const server = new McpServer({
    name: 'my-customer-care-server',
    version: '1.0.0',
  });

  // Register your tools here
  // We'll add tools in the next section

  return server;
}

// MCP endpoint
app.post('/mcp', async (req: Request, res: Response) => {
  try {
    logger.info('Received MCP request', {
      method: req.body?.method,
    });

    // Create server instance
    const server = createServer();

    // Create transport in stateless mode
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true,
    });

    // Handle cleanup
    res.on('close', async () => {
      await transport.close();
      await server.close();
    });

    // Connect and handle request
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
  res.json({ status: 'ok', service: 'my-customer-care-server' });
});

// Start server
const PORT = process.env.PORT || 3004;
app.listen(PORT, () => {
  logger.info(`MCP server listening on port ${PORT}`);
});
```

### 2. Define Your Domain Model

Create interfaces for your domain. For example, an insurance domain:

**File: `src/types.ts`**

```typescript
export interface Policy {
  policyId: string;
  policyType: 'auto' | 'home' | 'life' | 'health';
  policyNumber: string;
  status: 'active' | 'pending' | 'cancelled';
  premium: number;
  coverageAmount: number;
  startDate: string;
  endDate: string;
}

export interface Claim {
  claimId: string;
  policyId: string;
  claimNumber: string;
  status: 'submitted' | 'under_review' | 'approved' | 'denied' | 'paid';
  claimAmount: number;
  dateSubmitted: string;
  description: string;
}

export interface Customer {
  customerId: string;
  name: string;
  email: string;
  phone: string;
  policies: Policy[];
}
```

### 3. Implement Business Logic

Create service modules for your business logic:

**File: `src/policyService.ts`**

```typescript
import { Policy, Customer } from './types';

export class PolicyService {
  // In a real implementation, this would connect to your database
  private static customers: Record<string, Customer> = {
    'CUST001': {
      customerId: 'CUST001',
      name: 'John Doe',
      email: 'john@example.com',
      phone: '+15551234567',
      policies: [
        {
          policyId: 'POL001',
          policyType: 'auto',
          policyNumber: 'AUTO-2024-001',
          status: 'active',
          premium: 150,
          coverageAmount: 50000,
          startDate: '2024-01-01',
          endDate: '2025-01-01',
        },
        {
          policyId: 'POL002',
          policyType: 'home',
          policyNumber: 'HOME-2024-001',
          status: 'active',
          premium: 200,
          coverageAmount: 300000,
          startDate: '2024-01-01',
          endDate: '2025-01-01',
        },
      ],
    },
  };

  static getCustomer(customerId: string): Customer {
    const customer = this.customers[customerId];
    if (!customer) {
      throw new Error(`Customer ${customerId} not found`);
    }
    return customer;
  }

  static getPolicies(customerId: string): Policy[] {
    return this.getCustomer(customerId).policies;
  }

  static getPolicy(customerId: string, policyId: string): Policy {
    const policies = this.getPolicies(customerId);
    const policy = policies.find(p => p.policyId === policyId);
    if (!policy) {
      throw new Error(`Policy ${policyId} not found`);
    }
    return policy;
  }
}
```

### 4. Create Tools

Define tools that expose your business logic:

**File: `src/policyTools.ts`**

```typescript
import { PolicyService } from './policyService';

/**
 * Tool: Get Policy Details
 */
export const getPolicyDetailsTool = {
  name: 'get_policy_details',
  config: {
    description: 'Get detailed information about a specific insurance policy',
    inputSchema: {
      type: 'object',
      properties: {
        customerId: {
          type: 'string',
          description: 'Customer identifier',
        },
        policyId: {
          type: 'string',
          description: 'Policy identifier',
        },
      },
      required: ['customerId', 'policyId'],
    },
  },
  handler: async (
    args: {
      customerId: string;
      policyId: string;
    },
    extra: any,
  ) => {
    try {
      const policy = PolicyService.getPolicy(args.customerId, args.policyId);

      const response = `## Policy Details

**Policy Number**: ${policy.policyNumber}
**Type**: ${policy.policyType.charAt(0).toUpperCase() + policy.policyType.slice(1)} Insurance
**Status**: ${policy.status.charAt(0).toUpperCase() + policy.status.slice(1)}
**Premium**: $${policy.premium}/month
**Coverage Amount**: $${policy.coverageAmount.toLocaleString()}
**Coverage Period**: ${policy.startDate} to ${policy.endDate}`;

      return {
        content: [
          {
            type: 'text',
            text: response,
          },
        ],
        // Send directly to user, bypassing LLM
        _meta: {
          audience: ['user'],
        },
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: 'text',
            text: `Error retrieving policy details: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  },
};

/**
 * Tool: List Customer Policies
 */
export const listPoliciesTool = {
  name: 'list_policies',
  config: {
    description: 'List all insurance policies for a customer',
    inputSchema: {
      type: 'object',
      properties: {
        customerId: {
          type: 'string',
          description: 'Customer identifier',
        },
      },
      required: ['customerId'],
    },
  },
  handler: async (
    args: {
      customerId: string;
    },
    extra: any,
  ) => {
    try {
      const policies = PolicyService.getPolicies(args.customerId);

      if (policies.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: 'You do not have any active policies.',
            },
          ],
        };
      }

      const policyList = policies.map(p => 
        `- **${p.policyType.toUpperCase()}** (${p.policyNumber}): $${p.premium}/month, $${p.coverageAmount.toLocaleString()} coverage`
      ).join('\n');

      const response = `## Your Insurance Policies

You have ${policies.length} active ${policies.length === 1 ? 'policy' : 'policies'}:

${policyList}`;

      return {
        content: [
          {
            type: 'text',
            text: response,
          },
        ],
        _meta: {
          audience: ['user'],
        },
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: 'text',
            text: `Error retrieving policies: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  },
};

// Export all policy tools
export const policyTools = [
  getPolicyDetailsTool,
  listPoliciesTool,
];
```

### 5. Register Tools in Server

Update `src/index.ts` to register your tools:

```typescript
import { policyTools } from './policyTools';

function createServer(): McpServer {
  const server = new McpServer({
    name: 'my-customer-care-server',
    version: '1.0.0',
  });

  // Register tools
  for (const tool of policyTools) {
    server.registerTool(
      tool.name,
      tool.config,
      tool.handler as any
    );
  }

  return server;
}
```

## Adding Context Management

### 1. Implement Global Store

For conversation-wide context:

**File: `src/globalStore.ts`**

```typescript
/**
 * Global store for conversation-wide context
 * Keyed by thread_id, shared across all MCP servers
 */
const globalStore: Record<string, Record<string, any>> = {};

export function setGlobalVariable(
  threadId: string,
  key: string,
  value: any,
): void {
  if (!globalStore[threadId]) {
    globalStore[threadId] = {};
  }
  globalStore[threadId][key] = value;
}

export function getGlobalVariable(
  threadId: string,
  key: string,
): any | undefined {
  return globalStore[threadId]?.[key];
}

export function clearGlobalStore(threadId: string): void {
  delete globalStore[threadId];
}
```

### 2. Implement Local Store

For MCP server-specific state:

**File: `src/localStore.ts`**

```typescript
/**
 * Local store for MCP server-specific context
 * Keyed by thread_id, isolated per MCP server
 */
const localStore: Record<string, Record<string, any>> = {};

export function setLocalVariable(
  threadId: string,
  key: string,
  value: any,
): void {
  if (!localStore[threadId]) {
    localStore[threadId] = {};
  }
  localStore[threadId][key] = value;
}

export function getLocalVariable(
  threadId: string,
  key: string,
): any | undefined {
  return localStore[threadId]?.[key];
}

export function clearLocalStore(threadId: string): void {
  delete localStore[threadId];
}
```

### 3. Use Context in Tools

Access context variables in your tool handlers:

```typescript
handler: async (args: any, extra: any) => {
  // Access system context
  const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
  const locale = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.locale;
  
  // Access customer-provided context
  const jwtToken = extra?._meta?.['com.ibm.orchestrate/context']?.jwtToken;
  
  // Access global store
  const customerId = getGlobalVariable(threadId, 'customerId');
  
  // Access local store
  const pendingClaim = getLocalVariable(threadId, 'pendingClaim');
  
  // Use the context...
}
```

## Configuring the Agent Runtime

### 1. Create Agent Configuration

**File: `agents/insurance_agent.yaml`**

```yaml
spec_version: v1
style: experimental_customer_care
name: insurance_agent
instructions: >
  You are a helpful insurance customer service agent.
  Help customers with their insurance policies, claims, and questions.
  Always be professional and empathetic.
  When discussing policy details or claim amounts, use the exact values from the tools.
toolkits:
  - insurance
```

### 2. Create Toolkit Configuration

**File: `toolkits/insurance_mcp_server.yaml`**

```yaml
spec_version: v1
kind: mcp
name: insurance
description: An MCP server for insurance customer care
transport: streamable_http
url: http://localhost:3004/mcp
tools: []
```

### 3. Create Customer Context

**File: `sample_context/customer1.yaml`**

```yaml
# Customer context variables
customerId: "CUST001"
jwtToken: "your-jwt-token-here"
```

### 4. Create Start Script

**File: `start.sh`**

```bash
#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

uvx cca chat \
  -a ${SCRIPT_DIR}/agents/insurance_agent.yaml \
  -t ${SCRIPT_DIR}/toolkits/insurance_mcp_server.yaml \
  -c ${SCRIPT_DIR}/sample_context/customer1.yaml
```

Make it executable:

```bash
chmod +x start.sh
```

## Testing Your Server

### 1. Start the MCP Server

```bash
npm run dev
```

### 2. Run the Agent

```bash
./start.sh
```

### 3. Test Interactions

Try these example queries:

- "What policies do I have?"
- "Show me details about my auto insurance"
- "What's my coverage amount?"

## Adding Advanced Features

### 1. Implement Authentication

Add a welcome tool for authentication:

**File: `src/authTools.ts`**

```typescript
import { setGlobalVariable } from './globalStore';

export const welcomeTool = {
  name: 'authenticate_customer',
  config: {
    description: 'Authenticate customer with PIN',
    inputSchema: {
      type: 'object',
      properties: {
        pin: {
          type: 'string',
          description: 'Customer PIN',
        },
      },
      required: ['pin'],
    },
    // Mark as welcome tool for automatic invocation
    'com.ibm.orchestrate/welcomeTool': true,
  },
  handler: async (args: { pin: string }, extra: any) => {
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
    
    // Validate PIN (in real implementation, check against database)
    if (args.pin === '1234') {
      const customerId = 'CUST001';
      
      // Store customer ID in global store
      if (threadId) {
        setGlobalVariable(threadId, 'customerId', customerId);
      }
      
      return {
        content: [
          {
            type: 'text',
            text: 'Authentication successful. How can I help you today?',
          },
        ],
        _meta: {
          audience: ['user'],
          // Trigger tool refresh to show customer-specific tools
          refreshToolsForThread: threadId,
        },
      };
    }
    
    return {
      content: [
        {
          type: 'text',
          text: 'Invalid PIN. Please try again.',
        },
      ],
      isError: true,
    };
  },
};
```

### 2. Add Widget-Based Tools

Create tools with rich interactions:

```typescript
export const fileClaimTool = {
  name: 'file_claim',
  config: {
    description: 'File a new insurance claim',
    inputSchema: {
      type: 'object',
      properties: {
        customerId: { type: 'string' },
        policyId: { type: 'string' },
        incidentDate: { type: 'string' },
        description: { type: 'string' },
        estimatedAmount: { type: 'number' },
      },
      required: ['customerId'],
    },
  },
  handler: async (args: any, extra: any) => {
    // Step 1: Select policy
    if (!args.policyId) {
      const policies = PolicyService.getPolicies(args.customerId);
      const options = policies.map(p => ({
        value: p.policyId,
        label: `${p.policyType.toUpperCase()} - ${p.policyNumber}`,
        description: `Coverage: $${p.coverageAmount.toLocaleString()}`,
      }));
      
      return {
        _meta: {
          'com.ibm.orchestrate/widget': {
            responseType: 'single-choice',
            title: 'Select Policy',
            description: 'Which policy is this claim for?',
            options,
            onChange: {
              toolName: 'file_claim',
              parameters: { ...args },
              mapSelectionTo: 'policyId',
            },
          },
        },
      };
    }
    
    // Step 2: Select incident date
    if (!args.incidentDate) {
      const today = new Date();
      const minDate = new Date();
      minDate.setDate(minDate.getDate() - 365); // Claims up to 1 year old
      
      return {
        _meta: {
          'com.ibm.orchestrate/widget': {
            responseType: 'date-picker',
            title: 'Incident Date',
            description: 'When did the incident occur?',
            minDate: minDate.toISOString().split('T')[0],
            maxDate: today.toISOString().split('T')[0],
            onChange: {
              toolName: 'file_claim',
              parameters: { ...args },
              mapSelectionTo: 'incidentDate',
            },
          },
        },
      };
    }
    
    // Additional steps for description and amount...
    // Final step: confirmation widget
  },
};
```

### 3. Add Resources

Provide contextual information to the agent:

```typescript
export const customerPoliciesResource = {
  name: 'Customer Policies',
  uri: 'insurance://policies',
  description: 'Information about customer insurance policies',
  mimeType: 'text/plain',
  handler: async (args: { customerId: string }, extra: any) => {
    const policies = PolicyService.getPolicies(args.customerId);
    
    const policyInfo = policies.map(p =>
      `- ${p.policyType.toUpperCase()} (${p.policyNumber}): $${p.coverageAmount.toLocaleString()} coverage`
    ).join('\n');
    
    return {
      contents: [
        {
          uri: 'insurance://policies',
          mimeType: 'text/plain',
          text: `Customer has ${policies.length} active policies:\n\n${policyInfo}`,
        },
      ],
    };
  },
};
```

## Best Practices

### 1. Follow the MCP Protocol

- Use proper JSON-RPC 2.0 format
- Handle errors gracefully
- Implement required MCP methods

### 2. Separate Concerns

- Business logic in service modules
- MCP interface in tool modules
- Context management in dedicated modules

### 3. Use Appropriate Response Types

- `audience: ['user']` for exact responses
- Widgets for structured interactions
- Let LLM handle conversational responses

### 4. Implement Proper Context Management

- Use context variables for per-request data
- Use global store for conversation-wide data
- Use local store for MCP server-specific state

### 5. Test Thoroughly

- Test with different customer profiles
- Test error conditions
- Test multi-step workflows
- Test across different channels (if applicable)

## Next Steps

- Study the [pattern documentation](../) for advanced techniques
- Review the [banking example](../../src/) for more complex implementations
- Experiment with different widget types
- Add localization support
- Implement proper authentication
- Connect to real data sources

## Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [MCP SDK Documentation](https://github.com/modelcontextprotocol/typescript-sdk)
- [Pattern Documentation](../)
- [Banking Example Implementation](../../toolkits/banking_mcp_server/)