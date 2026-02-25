# Tool Chaining Pattern

## Overview

This pattern demonstrates how to use the `_meta.nextTool` field to create deterministic tool chains without relying on LLM reasoning. When a tool determines that another tool must be called next, it can explicitly instruct the client to invoke that tool with specific arguments, ensuring reliable multi-step workflows.

This pattern implements the [Tool Chaining Metadata Specification](./specChanges/ToolChainingMetadata.md) proposal for MCP.

**Note:** This pattern is for **tool-to-tool** chaining. For **tool-to-human** handoff, see the [Agent Handoff Pattern](./Handoff.md).

## Problems This Pattern Solves

### **Deterministic Tool Chaining**

When a tool needs to trigger another tool based on business logic:

- **Reliability**: LLMs may not recognize follow-up requirements or select wrong tools
- **Token Waste**: Workflows must be explained in natural language
- **Non-Determinism**: Same inputs may produce different outcomes

The Tool Chaining Pattern addresses these issues by allowing tools to explicitly specify the next tool to call with structured arguments.

### **Automatic Escalation Workflows**

When business rules require automatic escalation:

- Account locked → handoff to customer service
- Approval threshold exceeded → route to manager
- Error conditions → trigger recovery workflow
- Compliance requirements → initiate audit trail

The pattern ensures these workflows execute reliably without depending on LLM interpretation.

## Implementation Walkthrough

Below we walk through a locked account detection implementation that demonstrates this pattern.

### Use Case: Locked Account Detection

When a customer attempts to transfer money from a locked account, the system should:

1. Detect the locked status immediately
2. Inform the user clearly
3. Automatically initiate agent handoff
4. Pass context about the locked account to the agent

**Implementation Files:**

**TypeScript:**
- [`ts_server/src/personalBankingService.ts`](../toolkits/banking_mcp_server/ts_server/src/personalBankingService.ts) - Account data model
- [`ts_server/src/personalBanking.ts`](../toolkits/banking_mcp_server/ts_server/src/personalBanking.ts) - Transfer tool with handoff logic

**Python:**
- [`py_server/src/personal_banking_service.py`](../toolkits/banking_mcp_server/py_server/src/personal_banking_service.py) - Account data model
- [`py_server/src/personal_banking.py`](../toolkits/banking_mcp_server/py_server/src/personal_banking.py) - Transfer tool with handoff logic

### Step 1: Account Data Model

First, we add an `isLocked` field to the account interface:

```typescript
export interface Account {
  accountId: string;
  accountName: string;
  accountType: string;
  canTransferFrom: boolean;
  canTransferTo: boolean;
  isLocked: boolean; // Indicates if the account is locked
  accountHolder?: string;
}
```

In the mock data, we set one account as locked to demonstrate the pattern:

```typescript
static getAccounts(customerId: string): Account[] {
  return [
    {
      accountId: 'acc_checking_001',
      accountName: 'Primary Checking',
      accountType: 'checking',
      canTransferFrom: true,
      canTransferTo: true,
      isLocked: true, // This account is locked - requires customer service
    },
    {
      accountId: 'acc_savings_001',
      accountName: 'High Yield Savings',
      accountType: 'savings',
      canTransferFrom: true,
      canTransferTo: true,
      isLocked: false,
    },
    // ... other accounts
  ];
}
```

### Step 2: Locked Account Check with Handoff Metadata

In the `prepare_money_transfer` tool, we check for locked accounts immediately after the user selects the "from" account:

```typescript
export const prepareTransferTool = {
  name: 'prepare_money_transfer',
  config: {
    title: 'Prepare Money Transfer',
    description: 'Prepare a transfer between your accounts...',
    inputSchema: {
      fromAccountId: z.string().optional(),
      toAccountId: z.string().optional(),
      amount: z.number().min(0.01),
      scheduledDate: z.string().optional(),
      memo: z.string().optional(),
    },
  },
  handler: async (
    args: {
      customerId: string;
      fromAccountId?: string;
      toAccountId?: string;
      amount: number;
      scheduledDate?: string;
      memo?: string;
    },
    extra: any,
  ) => {
    const allAccounts = PersonalBankingService.getAccounts(args.customerId);

    // Step 1: If fromAccountId is missing, show picker
    if (!args.fromAccountId) {
      // ... show account picker widget
    }

    // Step 2: Check if the from account is locked (once fromAccountId is present)
    const fromAccount = allAccounts.find(
      acc => acc.accountId === args.fromAccountId,
    );

    if (fromAccount?.isLocked) {
      return {
        content: [
          {
            type: 'text',
            text: `I'm sorry, but your ${fromAccount.accountName} account (${fromAccount.accountId}) is currently locked. You'll need to speak with a customer service agent to resolve this issue before you can transfer funds from this account.`,
            annotations: { audience: ['user'] },
          },
        ],
        _meta: {
          nextTool: {
            tool: 'request_agent_handoff',
            arguments: {
              reason: `Customer attempted to transfer from locked account: ${fromAccount.accountName} (${fromAccount.accountId})`,
            },
          },
        },
      };
    }

    // Step 3: Continue with normal transfer flow if account is not locked
    // ... rest of transfer preparation logic
  },
};
```

### How Tool Chaining Works

The complete flow when a locked account is detected:

1. **User Selects Account**: Customer chooses "Primary Checking" as the from account
2. **Lock Detection**: The tool checks `fromAccount.isLocked` and finds it's `true`
3. **User Notification**: A clear message explains the account is locked
4. **Automatic Chaining**: The `_meta.nextTool` field instructs the client to call `request_agent_handoff`
5. **Context Passed**: The reason includes specific details about which account is locked
6. **Agent Handoff Initiated**: The `request_agent_handoff` tool presents connection options to the user
7. **No LLM Reasoning Required**: The entire chain executes deterministically

**Key aspects of the chaining metadata:**

```typescript
_meta: {
  nextTool: {
    tool: 'request_agent_handoff',           // Tool to call next
    arguments: {                              // Structured arguments
      reason: `Customer attempted to transfer from locked account: ${fromAccount.accountName} (${fromAccount.accountId})`
    }
  }
}
```

### The \_meta.nextTool Field

The `nextTool` metadata field has two components:

- **`name`** (required): The exact name of the tool to invoke next
- **`arguments`** (optional): A structured object containing the arguments to pass to that tool

**Benefits over natural language instructions:**

- ✅ **Type-safe**: Arguments are proper JSON objects, not parsed text
- ✅ **Deterministic**: Same input always produces same tool chain
- ✅ **Efficient**: No tokens wasted explaining what to do next
- ✅ **Reliable**: No risk of LLM misinterpreting instructions

## Key Takeaways

The Tool Chaining Pattern provides essential capabilities for building reliable multi-step workflows:

- **Deterministic Execution**: Tool chains execute reliably without LLM interpretation
- **Type Safety**: Arguments are structured JSON objects, not parsed text
- **Efficiency**: Eliminates tokens needed for workflow coordination
- **Separation of Concerns**: Workflow logic stays in tools, not LLM prompts
- **Backward Compatible**: Uses `_meta` extension point, doesn't break existing clients

**When to use this pattern:**

- Business rules require specific tool sequences
- Error conditions need automatic recovery workflows
- Approval chains must follow defined paths
- Compliance requires audit trails of tool invocations
- Context must be preserved across tool calls without LLM interpretation
- **Multiple tools share the same business logic** - separate that logic into its own tool and call it via `nextTool` to avoid duplication

**When NOT to use this pattern:**

- The next step depends on LLM reasoning or user input
- Multiple valid next steps exist and LLM should choose

## Specification Reference

This pattern implements the [Tool Chaining Metadata Specification](./specChanges/ToolChainingMetadata.md), which proposes adding `_meta.nextTool` as a standardized mechanism for deterministic tool chaining in the Model Context Protocol (MCP).

The specification includes:

- Complete TypeScript interface definitions
- Client and server implementation requirements
- Security considerations and best practices
- Additional use cases and examples

The Tool Chaining Pattern is a powerful addition to MCP that enables reliable, deterministic multi-step workflows while maintaining backward compatibility with existing implementations.
