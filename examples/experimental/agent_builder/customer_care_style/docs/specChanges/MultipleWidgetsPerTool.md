# MCP Apps Specification Proposal: Multiple Widget Support Per Tool

## Overview

This document proposes an extension to the [MCP Apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/draft/apps.mdx) to support multiple UI widgets from a single tool.

## Motivation

### Problem Statement

The current MCP Apps specification allows tools to declare a single `resourceUri` for UI rendering. However, real-world business logic often requires different UI widgets at different stages of tool execution.

### Use Case: Date Selection with Business Rules

Consider a money transfer tool that needs to:

1. Present a date picker with business-rule-constrained dates (e.g., "future dates only, but not more than 30 days out")
2. Show a confirmation screen with transfer details
3. Display a success message after completion

**Why This Matters:**

- Business rules for valid selections are often complex and context-dependent
- These rules are best enforced in the tool's business logic, not in generic UI components
- The tool needs to dynamically select which widget to display based on the current state

### Current Limitation

With the current spec, a tool can only declare one UI resource:

```typescript
{
  name: "visualize_data",
  _meta: {
    ui: {
      resourceUri: "ui://charts/bar-chart"  // ← Single URI only
    }
  }
}
```

This forces developers to either:

- Create overly complex, multi-purpose widgets
- Use multiple separate tools for what should be a single logical operation
- Implement business logic in the UI layer (violating separation of concerns)

## Proposed Solution

### 1. Tool Registration Enhancement

Add a new `resourceUris` array to declare all possible widgets a tool may use:

```typescript
{
  name: "transfer_money",
  _meta: {
    ui: {
      resourceUri: "ui://widgets/confirmation",  // ← Default/fallback
      resourceUris: [  // ← NEW: Array of possible widgets
        "ui://widgets/date-picker",
        "ui://widgets/confirmation",
        "ui://widgets/success"
      ]
    }
  }
}
```

**Key Points:**

- `resourceUri` remains as the default/fallback widget
- `resourceUris` declares all widgets the tool may use
- Backward compatible: existing tools without `resourceUris` continue to work

### 2. Dynamic Widget Selection in Tool Response

Tools can override the widget in their response:

```typescript
// Tool response dynamically selects widget
{
  content: [...],
  structuredContent: {...},
  _meta: {
    ui: {
      resourceUri: "ui://widgets/date-picker"  // ← Override
    }
  }
}
```

### 3. Type Definitions

```typescript
interface McpUiToolMeta {
  /** Default/fallback URI */
  resourceUri?: string;

  /** NEW: Array of possible UI resources this tool may use */
  resourceUris?: string[];

  visibility?: Array<'model' | 'app'>;
}
```

### 4. Validation Rules

1. **Response Validation**: If a tool response includes `_meta.ui.resourceUri`, it MUST be present in the declared `resourceUris[]` array
2. **Fallback Behavior**: If `resourceUris` is present but the response doesn't specify `resourceUri`, use the default `resourceUri`
3. **Prefetching**: Host applications SHOULD prefetch ALL URIs in `resourceUris[]` at connection time for optimal performance

## Example Implementation

### Complete Tool Registration

```typescript
server.registerTool(
  'transfer_money',
  {
    inputSchema: {
      from_account: z.string(),
      to_account: z.string(),
      amount: z.number(),
      transfer_date: z.string().optional(),
    },
    _meta: {
      ui: {
        resourceUri: 'ui://widgets/confirmation', // Default
        resourceUris: [
          'ui://widgets/date-picker',
          'ui://widgets/confirmation',
          'ui://widgets/success',
        ],
      },
    },
  },
  async (args: { from_account: string; to_account: string; amount: number; transfer_date?: string }, extra: any) => {
    const { from_account, to_account, amount, transfer_date } = args;
    
    // Stage 1: Date selection with business rules
    if (!transfer_date) {
      return {
        content: [{ type: 'text', text: 'Select transfer date' }],
        structuredContent: {
          validDateRange: {
            min: today(),
            max: thirtyDaysOut(),
          },
        },
        _meta: {
          ui: {
            resourceUri: 'ui://widgets/date-picker',
          },
        },
      };
    }

    // Stage 2: Confirmation
    return {
      content: [{ type: 'text', text: 'Confirm transfer' }],
      structuredContent: {
        from_account,
        to_account,
        amount,
        transfer_date,
      },
      _meta: {
        ui: {
          resourceUri: 'ui://widgets/confirmation',
        },
      },
    };
  },
);
```

### Flow Diagram

```
User Request → Tool Invoked (no date)
                ↓
            Returns date-picker widget
            with business rules (min/max dates)
                ↓
User Selects Date → Tool Invoked (with date)
                ↓
            Returns confirmation widget
            with transfer details
                ↓
User Confirms → Tool Executes Transfer
                ↓
            Returns success widget
```

## Benefits

1. **Separation of Concerns**: Business logic stays in the tool, UI stays in widgets
2. **Reusable Widgets**: Generic widgets (date-picker, confirmation) can be reused across tools
3. **Dynamic UX**: Tools can adapt their UI based on state and business rules
4. **Backward Compatible**: Existing tools continue to work without changes
5. **Performance**: Hosts can prefetch all possible widgets at connection time

## Migration Path

### For Existing Tools

No changes required. Tools with only `resourceUri` continue to work as before.

### For New Tools

1. Declare all possible widgets in `resourceUris[]`
2. Set a sensible default in `resourceUri`
3. Return appropriate `resourceUri` in tool responses based on state

### For Host Applications

1. Support both `resourceUri` (existing) and `resourceUris[]` (new)
2. Implement validation: response URIs must be in declared array
3. Consider prefetching all declared URIs for better performance

## Open Questions

1. Should there be a maximum limit on `resourceUris[]` array size?
2. Should hosts be required to prefetch, or is it optional?
3. How should errors be handled if a tool returns an undeclared `resourceUri`?

## References

- [MCP Apps Specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/draft/apps.mdx)
- Related discussion: [Issue tracking this proposal](https://github.com/modelcontextprotocol/ext-apps/issues/191)
