# Unique Tools and Resources Per User

## Overview

This pattern enables MCP servers to provide different sets of tools to different users based on their context, permissions, or entitlements. In customer care scenarios, this allows the agent to offer personalized experiences where each customer only sees tools relevant to their specific products or services.

## Problems This Pattern Solves

### **Personalized Customer Experience**

Different customers have different products and services. A customer with only a checking account shouldn't see mortgage-related tools, while a customer with both banking and mortgage products should have access to all relevant capabilities.

## Implementation Walkthrough

Below we walk through a sample banking application that demonstrates this pattern. The sample shows how a financial services company provides different tools to customers based on whether they have personal banking accounts, mortgages, credit cards, or any combination thereof.

### Step 1: Thread-Based Context Management

The foundation of this pattern is thread-based context management. Each conversation thread maintains customer identity through the global store.

#### Creating Context for a Thread

When a customer first connects, the system extracts their identity from authentication headers and stores it in the global store. The sample includes a global store implementation in [`src/globalStore.ts`](../src/globalStore.ts) that maps thread IDs to customer data.

The HTTP endpoint handles thread context:

**File:** [`src/index.ts`](../src/index.ts)

```typescript
app.post('/mcp', async (req: Request, res: Response) => {
  try {
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

    // Create transport
    const transport = new StreamableHTTPServerTransport({
      enableJsonResponse: true,
    });

    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    // Error handling...
  }
});
```

The context lifecycle works as follows:

1. **Thread Context**: The system extracts the thread ID from system context in each request
2. **Customer Identity**: The system retrieves the customer ID from the global store using the thread ID
3. **Authentication**: Customer ID is typically set by the welcome tool after successful authentication (see [Authentication.md](Authentication.md))

### Step 2: Determining User-Specific Tools

Now that we have the customer's identity stored in the thread, we determine which tools they should have access to based on their products and entitlements.

#### Customer Products and Entitlements

The sample uses a customer database module that maps which products each customer has access to:

**File:** [`src/customerDatabase.ts`](../src/customerDatabase.ts)

```typescript
export interface CustomerProducts {
  hasPersonalBanking: boolean;
  hasMortgage: boolean;
  hasCreditCard: boolean;
}

export function getCustomerProducts(customerId: string): CustomerProducts {
  return (
    customerDatabase[customerId] ?? {
      hasPersonalBanking: false,
      hasMortgage: false,
      hasCreditCard: false,
    }
  );
}
```

#### Tool Organization by Product Line

The sample organizes tools into separate modules for each product line. Personal banking tools handle checking and savings accounts:

**File:** [`src/personalBanking.ts`](../src/personalBanking.ts)

```typescript
export const personalBankingTools = [
  getAccountBalanceTool,
  getAccountStatementTool,
  prepareTransferTool,
  confirmOrCancelTransferTool,
];
```

Mortgage tools handle loan information:

**File:** [`src/mortgage.ts`](../src/mortgage.ts)

```typescript
export const mortgageTools = [
  getMortgageBalanceTool,
  getMortgagePaymentsTool,
  prepareMortgagePaymentTool,
  confirmOrCancelMortgagePaymentTool,
];
```

Credit card tools handle credit card operations:

**File:** [`src/creditCard.ts`](../src/creditCard.ts)

```typescript
export const creditCardTools = [getCreditCardBalanceTool];
```

#### Creating the Server with User-Specific Tools

The core of the pattern is in how the sample creates an MCP server instance for each customer with **only their relevant tools** registered:

**File:** [`src/index.ts`](../src/index.ts)

```typescript
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

  // Register handoff tools (available at all times)
  registerToolsWithCustomerId(server, handoffTools);

  // If no customerId, only welcome and handoff tools are available (pre-authentication)
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

    // Register personal banking resources
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

// Helper function to register tools with customerId from global store
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
```

In this code:

- The server instance is created with explicit `capabilities` declaration for both `resources` and `tools`
- Welcome tools are always registered (for pre-authentication scenarios)
- Handoff tools are always registered (available to all customers)
- **Empty resources handler** is set for unauthenticated users (no customerId)
- For authenticated users, the code checks if any resources will be registered
- **Empty resources handler** is also set for authenticated users without resources (e.g., customers with only mortgages or credit cards)
- Product-specific tools are conditionally registered based on the customer's products
- Tool handlers are wrapped to inject the `customerId` from the global store
- Credit card tools use JWT tokens from context variables and don't need wrapping
- Personal banking resources are registered only for customers with personal banking
- No tools or resources are registered for products the customer doesn't have

This means when the Orchestrate platform queries the server for available tools and resources, it only receives those that are relevant to that specific customer.

### Step 3: Resources Pattern

Resources in MCP provide read-only data that can be accessed by the AI agent. Like tools, resources should also be personalized per user.

#### Declaring Resources Capability

When creating an MCP server that supports resources, you must declare the `resources` capability:

```typescript
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
```

**Important**: If you declare the `resources` capability, you **must** handle resource listing requests, even if you have no resources to provide.

#### Handling Empty Resources

There are two scenarios where you need to register an empty resources handler:

**1. Unauthenticated Users (No Customer ID)**

Before authentication, no customer-specific resources are available:

```typescript
if (!customerId) {
  // Set empty resources handler only when no resources will be registered
  server.server.setRequestHandler(ListResourcesRequestSchema, async () => {
    return { resources: [] };
  });
  return server;
}
```

**2. Authenticated Users Without Resources**

Some customers may not have products that provide resources. For example, a customer with only mortgages or credit cards (but no personal banking) has no resources:

```typescript
// Check if we have any resources to register
const hasResources = products.hasPersonalBanking;

// If no resources, set empty handler before registering tools
if (!hasResources) {
  server.server.setRequestHandler(ListResourcesRequestSchema, async () => {
    return { resources: [] };
  });
}
```

#### Registering Resources for Eligible Users

For customers with personal banking, resources are registered conditionally:

```typescript
// Register personal banking tools if customer has personal banking
if (products.hasPersonalBanking) {
  registerToolsWithCustomerId(server, personalBankingTools);

  // Register personal banking resources
  registerResourcesWithCustomerId(server, personalBankingResources);
}
```

### Step 4: Tool and Resource Refresh and Dynamic Updates

The platform supports dynamic tool and resource updates through the refresh mechanism:

- **Initial Discovery**: When a thread starts, the server determines which tools and resources are available based on authentication state
- **Authentication Changes**: When a customer authenticates (e.g., via the welcome tool), the server signals a refresh
- **Updated Lists**: The platform re-queries the server, which now returns authenticated tools and resources based on the customer's products
- **Thread Context Persists**: Customer identity stored in the global store persists throughout the thread lifecycle

This refresh behavior enables seamless transitions from unauthenticated to authenticated states while maintaining user-specific tool and resource availability.

## Key Takeaways

This sample demonstrates how the "Unique Tools and Resources Per User" pattern provides a simple and scalable way to personalize the customer care agent for your customers.

The pattern is necessary for customer care scenarios where different customers have different needs and entitlements based on their products and/or services. By properly handling both tools and resources with appropriate empty handlers, you ensure a robust and error-free experience for all users.
