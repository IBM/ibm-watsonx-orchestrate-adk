# Authentication Patterns

## Overview

This document describes authentication patterns for MCP servers in customer care applications. Authentication is critical for ensuring that tools access data securely and only for authorized users.

There are two general approaches to authentication:

1. **Client Authentication (Recommended)**: Your application authenticates the user before invoking the agent, then passes authentication credentials (like a JWT token) as context variables. The agent uses these credentials to access backend services. This is the recommended approach for most scenarios.

2. **Agent Authentication**: The agent handles authentication as part of the conversation, such as asking the user to enter a PIN during a voice call. This approach is less common and should only be used when client authentication is not feasible (e.g., voice channels, step-up authentication).

**Default to client authentication unless you have a specific reason to authenticate within the agent.**

## Recommended Approach: Client Authentication

**In most cases, you should authenticate users outside of the agent and pass authentication credentials as context variables.**

This is the recommended approach because:

- **Security**: Authentication logic is handled by your trusted application code, not by the Agent.
- **Simplicity**: The agent doesn't need to manage authentication flows
- **Reliability**: No risk of the model mishandling authentication
- **User Experience**: Users authenticate through familiar, tested UI flows

### Implementation

When a user authenticates with your application:

1. Your application authenticates the user (login, SSO, etc.)
2. Your application obtains an authentication token (JWT, session token, etc.)
3. When invoking the Watson Orchestrate API, pass the token as a context variable
4. The token is automatically included in all tool calls via `_meta['com.ibm.orchestrate/context']`
5. Tools use the token to authenticate with backend services

### Example: JWT Token Authentication

This example demonstrates passing a JWT token from the client application to tools.

#### Step 1: Client Application Passes JWT Token

When your application calls the Watson Orchestrate API, include the JWT token in the context.

#### Step 2: Tool Receives JWT Token from Context Variables

The tool handler receives the JWT token through `_meta`:

**TypeScript:** [`ts_server/src/creditCard.ts`](../toolkits/banking_mcp_server/ts_server/src/creditCard.ts)
**Python:** [`py_server/src/credit_card.py`](../toolkits/banking_mcp_server/py_server/src/credit_card.py)

**TypeScript Example:**

```typescript
export const getCreditCardBalanceTool = {
  name: 'get_credit_card_balance',
  config: {
    title: 'Get Credit Card Balance',
    description: 'Retrieve current credit card balance',
    inputSchema: {},
    outputSchema: {
      cardNumber: z.string(),
      currentBalance: z.number(),
      // ... other fields
    },
  },
  handler: async ({
    _meta,
  }: {
    _meta?: {
      'com.ibm.orchestrate/systemcontext'?: {
        locale?: string;
      };
      'com.ibm.orchestrate/context'?: {
        jwtToken?: string;
      };
    };
  }) => {
    // Extract JWT token from CONTEXT VARIABLES (passed by API caller)
    const jwtToken = _meta?.['com.ibm.orchestrate/context']?.jwtToken;

    if (!jwtToken) {
      throw new Error(
        'JWT token is required. It must be provided in context variables by the API caller.',
      );
    }

    // Use JWT token to authenticate with backend service
    const cardBalance = CreditCardService.getCreditCardBalance(jwtToken);

    return {
      content: [
        {
          type: 'text',
          text: `Balance: $${cardBalance.currentBalance.toFixed(2)}`,
        },
      ],
      structuredContent: cardBalance,
    };
  },
};
```

#### Step 3: Service Uses JWT Token

The service layer uses the JWT token to authenticate with backend APIs:

**TypeScript:** [`ts_server/src/creditCardService.ts`](../toolkits/banking_mcp_server/ts_server/src/creditCardService.ts)
**Python:** [`py_server/src/credit_card_service.py`](../toolkits/banking_mcp_server/py_server/src/credit_card_service.py)

**TypeScript Example:**

```typescript
export class CreditCardService {
  static getCreditCardBalance(jwtToken: string): CreditCardBalance {
    // In a real implementation, this would:
    // 1. Validate the JWT token
    // 2. Extract customer ID from the token claims
    // 3. Make an authenticated API call to the backend service
    // 4. Return the actual credit card data

    if (!jwtToken) {
      throw new Error('JWT token is required');
    }

    // Example: Call backend API with JWT token
    // const response = await fetch('https://api.example.com/creditcard/balance', {
    //   headers: {
    //     'Authorization': `Bearer ${jwtToken}`
    //   }
    // });

    return {
      cardNumber: '**** **** **** 4532',
      currentBalance: 2847.63,
      // ... other fields
    };
  }
}
```

### JWT Pre-Authentication in Welcome Tool

JWT tokens can also be used for pre-authentication in the welcome tool, allowing users to be automatically authenticated when the conversation starts:

**TypeScript:** [`ts_server/src/welcome.ts`](../toolkits/banking_mcp_server/ts_server/src/welcome.ts)

```typescript
handler: async (args: any, extra: any) => {
  const _meta = extra?._meta;
  const threadId = _meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
  
  // Check for pre-authenticated JWT token
  const jwtToken = _meta?.['com.ibm.orchestrate/context']?.jwtToken;
  
  if (jwtToken && threadId) {
    const decoded = decodeTestJWT(jwtToken);
    
    if (decoded && decoded.customerId) {
      const customerProfile = getCustomerProfile(decoded.customerId);
      
      if (customerProfile) {
        // Pre-authenticated! Set customerId and skip PIN flow
        setGlobalVariable(threadId, 'customerId', decoded.customerId);
        
        return {
          content: [{
            type: 'text',
            text: `Hello ${customerProfile.firstName}! Welcome back.`,
            annotations: { audience: ['user'] }
          }],
          _meta: {
            refreshThreadCapabilities: threadId
          }
        };
      }
    }
  }
  
  // Fall back to PIN authentication if no valid JWT
  // ... PIN flow code ...
}
```

This pattern allows the welcome tool to:
- Detect JWT tokens passed in context variables
- Automatically authenticate users without requiring PIN entry
- Fall back to PIN authentication if no JWT is provided
- Trigger tool refresh to make authenticated tools available

### Key Benefits

1. **Model Never Sees Credentials**: The AI model never has access to passwords, tokens, or other sensitive authentication data
2. **Standard Security Practices**: Use your existing authentication infrastructure (OAuth, SAML, JWT, etc.)
3. **Centralized Authentication**: Authentication logic lives in one place, not scattered across tools
4. **Easy Token Refresh**: Your application can refresh tokens without the agent knowing
5. **Audit Trail**: Authentication events are logged in your application, not in the agent

### Security Considerations

- **Token Validation**: Always validate tokens in your service layer before using them
- **Token Expiration**: Handle expired tokens gracefully and prompt for re-authentication

## Alternative Approach: Agent Authentication

**Note:** This approach is less common and should only be used when client-side authentication is not feasible.

Some scenarios require authentication to happen within the agent conversation:

- **Voice Interactions**: User enters a PIN or security code during a voice call
- **Step-Up Authentication**: Additional verification needed for sensitive operations

### When to Use Agent Authentication

Consider agent authentication when:

- Users interact through channels where pre-authentication isn't possible (voice, SMS)
- You need step-up authentication for high-risk operations
- The authentication flow is part of the conversation (e.g., "Please enter your PIN")

### Implementation

Agent authentication follows this pattern:

1. **Collect credentials** from the user (PIN, security code, etc.)
2. **Verify credentials** against your backend system
3. **Store authentication state** in global store (e.g., customerId)
4. **Trigger tool refresh** so authenticated tools become available

#### Basic Example

Here's a simplified example showing the core pattern:

```typescript
export const verifyPinTool = {
  name: 'verify_pin',
  config: {
    title: 'Verify PIN',
    description: 'Verify customer PIN for authentication',
    inputSchema: {
      pin: z.string().describe('4-digit PIN entered by customer')
    },
    _meta: {
      ui: { visibility: ['app'] }  // Hidden from model
    }
  },
  handler: async ({ pin }: { pin: string }, extra: any) => {
    // Get user identifier from context variable (passed by caller)
    const userId = extra?._meta?.['com.ibm.orchestrate/context']?.userId;
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
    
    if (!userId) {
      throw new Error('User ID required in context variables');
    }
    
    // Verify PIN against backend
    const isValid = verifyUserPin(userId, pin);
    
    if (isValid) {
      // Look up customer profile
      const customerProfile = getCustomerProfile(userId);
      
      // ✅ Store customerId in global store (NOT the PIN)
      setGlobalVariable(threadId, 'customerId', customerProfile.customerId);
      
      return {
        content: [{
          type: 'text',
          text: 'Thank you! Your PIN has been verified.',
          annotations: { audience: ['user'] }
        }],
        _meta: {
          // ✅ Signal client to refresh tools for authenticated user
          refreshThreadCapabilities: threadId
        }
      };
    }
    
    // PIN verification failed
    return {
      content: [{
        type: 'text',
        text: 'Incorrect PIN. Please try again.',
        annotations: { audience: ['user'] }
      }]
    };
  }
};
```

**Key aspects:**

1. **User ID from Context**: The userId comes from context variables (passed by the API caller)
2. **PIN Verification**: The PIN is verified against the backend using that userId
3. **Store Authentication State**: After successful verification, store customerId in thread variables (NEVER store the PIN itself)
4. **Trigger Tool Refresh**: Use `refreshThreadCapabilities` to make authenticated tools available
5. **Hidden from Model**: `visibility: ['app']` ensures only the system can invoke this tool

#### Full Working Example

For a complete production implementation including numeric widgets for PIN entry, error handling with agent handoff fallback, and welcome tool integration, see:
- TypeScript: [`ts_server/src/welcome.ts`](../toolkits/banking_mcp_server/ts_server/src/welcome.ts)
- Python: [`py_server/src/welcome.py`](../toolkits/banking_mcp_server/py_server/src/welcome.py)

#### MCP Server Returns Conditional Tools

When the client refreshes tools after authentication, your MCP server checks the global store to retrieve the customer id which can then be used to determine which tools to register. This example shows the actual implementation:
- TypeScript: [`ts_server/src/index.ts`](../toolkits/banking_mcp_server/ts_server/src/index.ts)
- Python: [`py_server/src/server.py`](../toolkits/banking_mcp_server/py_server/src/server.py)

**TypeScript Example:**

```typescript
// Extract thread_id from request
if (req.body?.params?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id) {
  threadId = req.body.params._meta['com.ibm.orchestrate/systemcontext'].thread_id;
}

// Retrieve customerId from GLOBAL STORE
// Note: customerId is set by the welcome tool after successful PIN verification
if (threadId) {
  customerId = getGlobalVariable(threadId, 'customerId');
}

// Create server instance with customer-specific tools
// If customerId is undefined, only welcome and handoff tools will be registered
const server = createCustomerServer(customerId);

// In createCustomerServer function:
function createCustomerServer(customerId: string | undefined): McpServer {
  const server = new McpServer({ /* ... */ });

  // Register welcome tools (available before authentication)
  registerToolsDirect(server, welcomeTools);

  // Register handoff tools (available at all times)
  registerToolsWithCustomerId(server, handoffTools);

  // If no customerId, only welcome and handoff tools are available (pre-authentication)
  if (!customerId) {
    return server;
  }

  // Customer is authenticated - register product-specific tools
  const products = getCustomerProducts(customerId);

  // Register personal banking tools if customer has personal banking
  if (products.hasPersonalBanking) {
    registerToolsWithCustomerId(server, personalBankingTools);
  }

  // Register mortgage tools if customer has mortgage
  if (products.hasMortgage) {
    registerToolsWithCustomerId(server, mortgageTools);
  }

  // Register credit card tools if customer has credit card
  if (products.hasCreditCard) {
    registerToolsDirect(server, creditCardTools);
  }

  return server;
}
```

**Key Points:**
- Before authentication: Only welcome and handoff tools are available
- After authentication: Product-specific tools are registered based on customer's products
- The server checks global store on every request to determine authentication state

### Authentication Flow

```
1. User provides credentials (PIN, security code, etc.)
2. Tool verifies credentials against backend
3. Tool stores customerId in global store
4. Tool returns refreshThreadCapabilities metadata
5. Client refreshes tool lists from all MCP servers
6. MCP servers check for customerId in global store
7. MCP servers return authenticated tools
8. Model can now use authenticated tools
```

### Security Best Practices

1. **Never Store Credentials**: Store only authentication state (customerId), never PINs or passwords
2. **Use Visibility Controls**: Set `visibility: ['app']` on authentication tools so that the model cannot call them by accident.
3. **Validate Every Request**: Always check global store before accessing sensitive data

### Example Implementation

For a complete working example of agent authentication with PIN verification, see:

**TypeScript:**
- Authentication Tools: [`ts_server/src/welcome.ts`](../toolkits/banking_mcp_server/ts_server/src/welcome.ts)
- Global Storage: [`ts_server/src/globalStore.ts`](../toolkits/banking_mcp_server/ts_server/src/globalStore.ts)

**Python:**
- Authentication Tools: [`py_server/src/welcome.py`](../toolkits/banking_mcp_server/py_server/src/welcome.py)
- Global Storage: [`py_server/src/global_store.py`](../toolkits/banking_mcp_server/py_server/src/global_store.py)

## Choosing the Right Approach

| Scenario                   | Recommended Approach  |
| -------------------------- | --------------------- |
| Web application with login | Client authentication |
| Mobile app with login      | Client authentication |
| API integration            | Client authentication |
| Voice channel (IVR)        | Agent authentication  |
| SMS/text channel           | Agent authentication  |
| Step-up authentication     | Agent authentication  |

**Default to client authentication unless you have a specific reason to authenticate within the agent.**

## See Also

- [Welcome Tool](WelcomeTool.md) - Automatic tool invocation at thread start for authentication flows
