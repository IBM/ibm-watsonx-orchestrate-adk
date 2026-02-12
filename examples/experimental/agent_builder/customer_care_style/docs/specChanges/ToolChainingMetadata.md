# MCP Specification Proposal: Tool Chaining Metadata

## Overview

This document proposes a standardized mechanism for tools to explicitly instruct clients to invoke subsequent tools through response metadata, enabling deterministic tool chaining without relying on LLM reasoning.

**Note:** This specification is for **tool-to-tool** chaining. For **tool-to-human** handoff, see agent handoff patterns.

## Motivation

### Problem Statement

Current MCP implementations require LLMs to infer multi-step workflows from tool descriptions and responses. When a tool determines another tool must be called next, it can only communicate this through natural language, leading to:

- **Reliability Issues**: LLMs may not recognize follow-up requirements, select wrong tools, or extract incorrect arguments
- **Context Loss**: Critical state must be communicated through text and re-parsed
- **Token Waste**: Workflows must be explained in natural language
- **Non-Determinism**: Same inputs may produce different outcomes

### Use Case: Banking Customer Service

When an account issue requires specialist assistance:

1. **Tool A** (`check_account_issue`): Analyzes issue, determines human assistance needed
2. **Tool B** (`initiate_human_handoff`): Manages agent handoff workflow, creates support ticket

**Current problematic flow:**

```javascript
// Tool A returns text description
{
  content: [
    {
      type: 'text',
      text: 'This requires specialist assistance. Use initiate_human_handoff with customer ID 12345...',
    },
  ];
}
// LLM must parse text, understand intent, extract arguments, and call next tool
```

**With this proposal:**

```javascript
// Tool A returns explicit chaining instruction
{
  content: [{
    type: "text",
    text: "This account lockout requires specialist assistance."
  }],
  _meta: {
    nextTool: {
      tool: "initiate_human_handoff",
      arguments: {
        customerId: "12345",
        issueType: "account_locked",
        urgency: "high"
      }
    }
  }
}
```

## Proposed Solution

### Tool Response Metadata

Tools MAY include `nextTool` in the `_meta` object to instruct the client to invoke another tool:

```typescript
interface CallToolResult {
  content: ContentItem[];
  isError?: boolean;
  _meta?: {
    nextTool?: {
      tool: string; // Required: Tool name to invoke
      arguments?: Record<string, any>; // Optional: Arguments for the tool
    };
  };
}
```

### Client Behavior

### Client Behavior

Clients receiving `nextTool` MUST:

1. **Invoke the Tool**: Automatically call the specified tool with provided arguments
2. **Validate Arguments**: Ensure arguments match the tool's schema
3. **Prevent Loops**: Implement depth limits to prevent infinite chains (recommended: 5 levels)

### Server Implementation

Servers implementing tool chaining MUST:

- Only specify tools they expose in their tool list
- Provide complete, valid arguments for the next tool

## Example Implementation

### Server (TypeScript)

```typescript
server.setRequestHandler(CallToolRequestSchema, async request => {
  if (request.params.name === 'check_account_issue') {
    const analysis = await analyzeIssue(request.params.arguments);

    if (analysis.requiresHuman) {
      return {
        content: [
          {
            type: 'text',
            text: 'Issue requires specialist assistance.',
          },
        ],
        _meta: {
          nextTool: {
            tool: 'initiate_human_handoff',
            arguments: {
              customerId: request.params.arguments.customerId,
              issueType: analysis.issueType,
              urgency: analysis.urgency,
            },
          },
        },
      };
    }

    return {
      content: [{ type: 'text', text: `Resolved: ${analysis.resolution}` }],
    };
  }
});
```

### Client (TypeScript)

```typescript
async function callToolWithChaining(
  name: string,
  arguments: Record<string, any>,
  depth: number = 0,
): Promise<CallToolResult> {
  if (depth >= 5) throw new Error('Max chain depth exceeded');

  const result = await client.callTool({ name, arguments });
  const nextTool = result._meta?.nextTool;

  if (!nextTool) return result;

  console.log(`Tool '${name}' instructs calling '${nextTool.tool}'`);

  // Automatically invoke the next tool
  return callToolWithChaining(
    nextTool.tool,
    nextTool.arguments || {},
    depth + 1,
  );
}
```

## Additional Use Cases

- **Multi-Stage Approvals**: Expense exceeds threshold → request manager approval
- **Error Recovery**: Database auth fails → refresh credentials
- **Staged Processing**: CSV validation fails → clean data
- **Conditional Workflows**: Document type detection → appropriate extraction tool

## Security Considerations

- **Argument Validation**: Clients MUST validate suggested arguments against tool schema
- **Infinite Loops**: Clients MUST implement depth limits (recommended: 5 levels) and detect circular chains
- **Authorization**: Chained tools MUST undergo normal authorization checks

## Backward Compatibility

Fully backward compatible using `_meta` extension point:

- Old clients ignore `_meta.nextTool` and rely on LLM reasoning (current behavior)
- Old servers don't include the field (current behavior)
- New clients automatically invoke chained tools when present
- No protocol version negotiation required

## Benefits

1. **Deterministic**: Tool chains execute reliably without LLM interpretation
2. **Type Safety**: Arguments are proper JSON objects, not parsed text
3. **Efficiency**: Eliminates tokens needed for workflow coordination
4. **Separation of Concerns**: Workflow logic stays in tools, not LLM prompts
5. **Backward Compatible**: Existing implementations unaffected

## References

- OpenAI Apps SDK: Uses `_meta["openai/nextTool"]` for similar patterns
