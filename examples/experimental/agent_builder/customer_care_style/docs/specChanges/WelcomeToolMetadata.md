# MCP Specification Proposal: Welcome Tool Metadata

## Overview

This document proposes a mechanism for MCP servers to designate a tool that should be automatically invoked when a conversation thread begins, enabling initialization workflows and context establishment without requiring explicit user requests.

## Motivation

### Problem Statement

When agents start conversations, they often need to:

- Establish user context and preferences
- Authenticate user (maybe with a pin)
- Load relevant conversational state
- Initialize services or connections
- Present welcome information or available capabilities

Currently, these initialization steps require either:
- Explicit user requests ("show me my account")
- Out-of-band initialization logic in the client

This leads to inconsistent startup experiences and unnecessary latency.

### Use Case: Customer Service Agent Initialization

When a customer service conversation begins:

1. Load customer profile and recent interactions
2. Check for pending issues or notifications
3. Establish authentication context
4. Present personalized greeting with relevant information

**Current problematic flow:**

```javascript
// Agent must either wait for user to ask, or LLM must decide to call tools
User: "Hello"
LLM: "Let me check your account..." → calls get_customer_profile
```

**With this proposal:**

```javascript
// Tool automatically invoked when thread begins
{
  name: "initialize_conversation",
  _meta: {
    welcomeTool: true
  }
}
// Agent starts with full context already loaded
```

## Proposed Solution

### Tool Registration Metadata

Tools MAY include `welcomeTool: true` in the `_meta` object to designate themselves as welcome tools:

```typescript
interface Tool {
  name: string;
  description?: string;
  inputSchema: object;
  _meta?: {
    welcomeTool?: boolean; // Designates this tool as a welcome tool
  };
}
```

### Server Behavior

Servers implementing welcome tools MUST:

- Designate at most ONE tool as a welcome tool per server
- Ensure the welcome tool can execute without required arguments (or with sensible defaults)
- Return quickly to avoid blocking thread initialization

### Client Behavior

Clients receiving tool lists with welcome tools MUST:

1. **Single Selection**: If multiple MCP servers define welcome tools, select only ONE to invoke
2. **Selection Strategy**: The selection strategy is implementation-defined (e.g., first registered, priority-based, user-configured)
3. **Automatic Invocation**: Invoke the selected welcome tool automatically when the thread begins
4. **No Arguments**: Invoke with empty arguments `{}` unless the client has stored preferences

### Constraints

- **One Per Server**: Each MCP server MAY define at most one welcome tool
- **One Per Thread**: Only one welcome tool will be invoked per thread initialization, even if multiple servers define them
- **Undefined Behavior**: If multiple servers define welcome tools, which one is selected is implementation-defined

## Example Implementation

### Server (TypeScript)

```typescript
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'initialize_customer_conversation',
        description: 'Initialize customer service conversation with user context',
        inputSchema: {
          type: 'object',
          properties: {},
        },
        _meta: {
          welcomeTool: true, // ← Designate as welcome tool
        },
      },
      // ... other tools
    ],
  };
});

```

## Use Cases

- **Conversation Initialization**: Load user profile, preferences, and context
- **Authentication Check**: Verify user authentication status and permissions
- **Notification Delivery**: Present pending alerts or important information
- **Service Discovery**: Inform user of available capabilities based on their context
- **State Restoration**: Restore previous conversation state or context

## Design Considerations

### Why Only One Welcome Tool Per Agent?

1. **Predictable Startup**: Multiple welcome tools could create race conditions or conflicting initialization
2. **Performance**: Parallel initialization from multiple servers could overwhelm the agent
3. **User Experience**: Single, coherent welcome experience is clearer than multiple competing initializations