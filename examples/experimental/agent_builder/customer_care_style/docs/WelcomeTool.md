# Welcome Tool Pattern

## Overview

The Welcome Tool Pattern enables automatic execution of initialization logic when a conversation thread begins. A tool designated with `welcomeTool: true` metadata is automatically invoked by the client at thread start, without requiring user input or model decision-making.

This pattern is ideal for:
- Greeting users with personalized messages
- Establishing initial context
- Performing authentication flows (see [Authentication](Authentication.md))
- Setting up thread-specific configuration
- Triggering initial data collection

## Problems This Pattern Solves

### **Automatic Invocation at Thread Start**

Without the welcome tool pattern, initialization logic would require:
- Explicit user requests ("I want to start")
- The model deciding when to call initialization tools
- Inconsistent conversation start experiences
- Unnecessary latency and back-and-forth

The Welcome Tool Pattern eliminates these issues by automatically running initialization when the thread begins, ensuring a consistent and immediate start to every conversation.

### **Seamless User Experience**

The pattern enables:
- Immediate personalized greetings without user prompting
- Automatic context establishment from the first message
- Professional, consistent conversation starts
- Reduced friction in the user experience

## Implementation

### Basic Example

Here's a simplified example showing the core pattern:

```typescript
export const greetUserTool = {
  name: 'greet_user',
  config: {
    title: 'Greet User',
    description: 'Greet the user when the conversation starts',
    inputSchema: {}, // Welcome tools typically have no input parameters
    outputSchema: {},
    _meta: {
      welcomeTool: true, // ← Designates this as a welcome tool
      ui: {
        visibility: ['app'], // Hidden from model - only callable by system
      },
    },
  },
  handler: async (args: any, extra: any) => {
    // Access context variables for personalization
    const userName = extra?._meta?.['com.ibm.orchestrate/context']?.userName;

    return {
      content: [
        {
          type: 'text',
          text: `Hello${userName ? ' ' + userName : ''}! How can I help you today?`,
          annotations: { audience: ['user'] },
        },
      ],
    };
  },
};
```

**Key aspects:**

1. **Welcome Tool Flag**: `_meta.welcomeTool: true` designates automatic invocation at thread start
2. **Hidden from Model**: `visibility: ['app']` ensures only the system can invoke it, not the model
3. **No Input Parameters**: Welcome tools typically have empty `inputSchema` since they're invoked automatically
4. **Context Access**: Can access context variables from `_meta` for personalization

### Full Working Example

For a complete implementation including authentication, PIN verification, and tool refresh, see:
- **TypeScript**: [`ts_server/src/welcome.ts`](../toolkits/banking_mcp_server/ts_server/src/welcome.ts)
- **Python**: [`py_server/src/welcome.py`](../toolkits/banking_mcp_server/py_server/src/welcome.py)

This production example demonstrates:
- Customer identification from context
- JWT token pre-authentication (when token is provided)
- PIN-based authentication flow (fallback when no JWT)
- Error handling with agent handoff
- Using `refreshThreadCapabilities` to update tool availability after authentication

### Tool Refresh Pattern

Welcome tools often need to trigger changes in tool availability after initialization (e.g., after authentication). Use the `refreshThreadCapabilities` metadata to signal the client to refresh tool lists:

```typescript
return {
  content: [{ type: 'text', text: 'Initialization complete!' }],
  _meta: {
    // Signal client to refresh tool lists from all MCP servers
    refreshThreadCapabilities: threadId,
  },
};
```

This is commonly used after authentication to make authenticated tools available. See [Authentication](Authentication.md) for a complete authentication flow example.

### How It Works

1. **Thread Begins**: Client detects a tool with `welcomeTool: true` metadata
2. **Automatic Invocation**: Client automatically invokes the welcome tool (no user input needed)
3. **Initialization Logic**: Welcome tool executes (greeting, authentication, context setup, etc.)
4. **Optional Refresh**: If needed, tool returns `refreshThreadCapabilities` to update available tools
5. **Conversation Ready**: Thread is initialized and ready for user interaction

## Use Cases

The Welcome Tool Pattern is ideal for:

- **Personalized Greetings**: Welcome users by name using context variables
- **Authentication Flows**: Initiate authentication at conversation start (see [Authentication](Authentication.md))
- **Context Establishment**: Set up thread-specific state or configuration
- **Data Collection**: Gather initial information needed for the conversation
- **Consistent Experience**: Ensure every conversation starts the same way

## Specification References

### Welcome Tool Metadata

See [WelcomeToolMetadata.md](./specChanges/WelcomeToolMetadata.md) for the complete specification.

**Key points:**
- Tools designate themselves with `_meta.welcomeTool: true`
- Clients automatically invoke the welcome tool when the thread begins
- Only one welcome tool is invoked per thread, even if multiple servers define them
- Welcome tools should execute quickly and not require arguments

### Global Tool Refresh Metadata

See [GlobalToolRefreshMetadata.md](./specChanges/GlobalToolRefreshMetadata.md) for the complete specification.

**Key points:**
- Tools signal refresh with `_meta.refreshThreadCapabilities: threadId`
- Clients refresh tool lists from ALL MCP servers for the specified thread
- Commonly used after authentication to make authenticated tools available
- Thread-scoped to avoid affecting other conversations

## See Also

- [Authentication](Authentication.md) - Complete guide to authentication patterns, including agent authentication using welcome tools