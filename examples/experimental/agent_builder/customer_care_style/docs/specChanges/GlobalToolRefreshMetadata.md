# MCP Specification Proposal: Thread-Scoped Capability Refresh Metadata

## Overview

This document proposes a mechanism for MCP servers to signal that all connected MCP servers should refresh their tools and resources for a specific thread context.

## Thread and MCP Server Architecture

**Key Concept**: A single conversation thread can connect to multiple MCP servers. When any server signals a refresh for a thread ID, the client refreshes tool lists across ALL MCP servers associated with that thread.

```
Thread "thread-abc-123"
│
├─ Connection to Auth MCP Server
├─ Connection to Account MCP Server
├─ Connection to Transaction MCP Server
└─ Connection to Analytics MCP Server

When Auth Server signals: refreshThreadCapabilities: "thread-abc-123"
→ Client refreshes tools and resources from ALL 4 MCP servers for this thread:
  - tools/list and resources/list from Auth Server
  - tools/list and resources/list from Account Server
  - tools/list and resources/list from Transaction Server
  - tools/list and resources/list from Analytics Server
```

### Why This Matters

When a user logs in via the Auth Server:

- Auth Server knows the user is authenticated
- Account Server can now make available account tools and resources
- Transaction Server can now make available transaction tools and resources
- Analytics Server can now make available analytics tools and resources

All these servers need to refresh their tools and resources for that specific thread, even though only one server triggered the change.

## Motivation

### Problem Statement

The MCP specification includes `notifications/tools/list_changed`, but it has limitations:

1. **Single Server Scope**: Only applies to the server that sent it
2. **Can Be Missed**: Notifications may not be received during processing
3. **No Thread Context**: Doesn't specify which thread context changed

### Use Case: Authentication State Changes

When a user logs in, tools and resources across multiple servers become available for that specific thread:

```javascript
// Current: No way to signal other servers to refresh for this thread
{
  content: [{ type: "text", text: "Logged in successfully" }]
}

// Proposed: Signal thread-scoped refresh
{
  content: [{ type: "text", text: "Logged in successfully" }],
  _meta: {
    refreshThreadCapabilities: "thread-abc-123"
  }
}
```

## Proposed Solution

### Tool Response Metadata

Tools MAY include `refreshThreadCapabilities` to signal a thread-scoped refresh of tools and resources:

```typescript
interface CallToolResult {
  content: ContentItem[];
  isError?: boolean;
  _meta?: {
    refreshThreadCapabilities?: string; // Thread ID to refresh
  };
}
```

### Client Behavior

When receiving `refreshThreadCapabilities`:

1. **Refresh All MCP Servers**: Send `tools/list` and `resources/list` to ALL MCP servers associated with the specified thread ID, including the thread_id in the context
2. **Thread-Scoped**: Only refresh the connections for the specified thread, not other threads
3. **Async**: Perform refresh without blocking the response

## Example Implementation

### Server

```typescript
server.setRequestHandler(CallToolRequestSchema, async request => {
  if (request.params.name === 'user_login') {
    const result = await authenticateUser(request.params.arguments);

    if (result.success) {
      return {
        content: [{ type: 'text', text: 'Logged in successfully' }],
        _meta: {
          refreshThreadCapabilities: result.threadId,
        },
      };
    }
  }
});
```

## Use Cases

- **Authentication**: User logs in → tools and resources become available for that thread
- **Service Signup**: User signs up for new service (e.g., premium tier, new product) → new capability-specific tools and resources become available

## Security Considerations

- **Rate Limiting**: Prevent abuse through excessive refreshes
- **Thread Validation**: Verify thread ID belongs to current conversation

## Benefits

1. **Thread-Scoped**: Only affects relevant thread
2. **Coordinated**: All servers refresh together
3. **Guaranteed**: Part of tool response
4. **Explicit**: Clear which thread context changed
