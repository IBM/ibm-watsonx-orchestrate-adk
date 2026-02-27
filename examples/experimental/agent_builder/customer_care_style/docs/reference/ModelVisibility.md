# Model Visibility

## Overview

Understanding what the AI model can and cannot see is critical for implementing effective risk mitigation strategies in customer care applications. This document provides a comprehensive guide to controlling model visibility through the MCP protocol and Watsonx Orchestrate extensions.

**Model visibility operates on two levels:**

1. **Content Visibility** - Controlling what tool response data the model sees
2. **Tool Visibility** - Controlling which tools the model can see and call

Both are essential for risk mitigation:

- **Content visibility** prevents hallucination of critical data (balances, amounts, dates)
- **Tool visibility** prevents the model from taking actions without explicit user consent (e.g., confirming financial transactions)

The visibility rules determine:

- What information the model uses to formulate responses
- What data is protected from potential hallucination or misinterpretation
- Which tools the model can invoke versus which require explicit user interaction
- How to balance natural conversation with data accuracy guarantees and security

## Content Visibility Rules

### 1. Content Array - Default Behavior (No Audience Annotation)

**Rule:** If a content element does not have an `audience` field within `annotations`, the model sees it by default.

```typescript
return {
  content: [
    {
      type: 'text',
      text: 'Account balance retrieved successfully.',
      // No annotations.audience field = model sees this
    },
  ],
};
```

**When to use:**

- Standard tool responses where the model should see the output
- Information that helps the model formulate contextual responses
- Data that the model needs to reason about or reference in follow-up interactions

**Example from codebase:**
- **TypeScript**: [`ts_server/src/personalBanking.ts`](../../toolkits/banking_mcp_server/ts_server/src/personalBanking.ts) - `getAccountBalanceTool`
- **Python**: [`py_server/src/personal_banking.py`](../../toolkits/banking_mcp_server/py_server/src/personal_banking.py) - `get_account_balance_tool`

### 2. Content Array - User-Only Audience

**Rule:** Content marked with `annotations: { audience: ['user'] }` goes directly to the user and the model does NOT see it.

```typescript
return {
  content: [
    {
      type: 'text',
      text: 'Your balance is $5,432.10',
      annotations: { audience: ['user'] }, // Model does NOT see this
    },
  ],
};
```

**When to use:**

- Critical data that must be displayed exactly as provided (e.g., account balances, transaction amounts)
- Regulatory-required information that cannot be paraphrased
- Eliminating hallucination risk for sensitive data
- Improving response times by bypassing LLM processing

**Benefits:**

- **Zero hallucination risk**: Data goes directly from your code to the user
- **Faster responses**: Eliminates LLM processing time on the return path
- **Regulatory compliance**: Ensures exact formatting and content
- **Liability protection**: No possibility of model transcription errors

**Example from codebase:**
- **TypeScript**: [`ts_server/src/mortgage.ts`](../../toolkits/banking_mcp_server/ts_server/src/mortgage.ts) - `getMortgageBalanceTool`
- **Python**: [`py_server/src/mortgage.py`](../../toolkits/banking_mcp_server/py_server/src/mortgage.py) - `get_mortgage_balance_tool`

**Important limitation:** When content is marked `annotations: { audience: ['user'] }`, the model cannot see it for cross-tool reasoning. For example, if one tool returns a balance with `annotations: { audience: ['user'] }` and another returns transactions, the model cannot compare them. This is actually a feature—it prevents the model from making potentially incorrect calculations or inferences. See [Trade-offs](#trade-offs) section below.

### 3. Content Array - Assistant-Only Audience

**Rule:** Content marked with `annotations: { audience: ['assistant'] }` is seen by the model but NOT displayed to the user.

```typescript
return {
  content: [
    {
      type: 'text',
      text: 'Payment data retrieved. A table will be displayed to the user.',
      annotations: { audience: ['assistant'] }, // Model sees this, user does not
    },
    {
      type: 'text',
      text: '| Date | Amount |\n|------|--------|\n| 2025-01-01 | $100 |',
      annotations: { audience: ['user'] }, // User sees this, model does not
    },
  ],
};
```

**When to use:**

- Providing context to the model about what data is being shown to the user
- Instructing the model on how to respond (e.g., "politely decline to calculate totals")
- Informing the model about UI widgets or structured content being displayed
- Enabling natural conversation while protecting data accuracy

**Benefits:**

- **Natural interaction**: Model can provide conversational context around data
- **Data accuracy**: Critical data still comes directly from your code
- **Performance optimization**: Model only processes minimal context, not full datasets
- **Safe calculation handling**: Model can acknowledge data without performing risky calculations

**Example from codebase:**
- **TypeScript**: [`ts_server/src/mortgage.ts`](../../toolkits/banking_mcp_server/ts_server/src/mortgage.ts) - `getMortgagePaymentsTool`
- **Python**: [`py_server/src/mortgage.py`](../../toolkits/banking_mcp_server/py_server/src/mortgage.py) - `get_mortgage_payments_tool`

This is the foundation of the **Hybrid Response Pattern** documented in [HybridResponses.md](./HybridResponses.md).

### 4. StructuredContent Field

**Rule:** `structuredContent` is ALWAYS seen by the model. Use it for data that the model should see and reason about.

```typescript
return {
  content: [
    {
      type: 'text',
      text: 'Balance retrieved',
    },
  ],
  structuredContent: {
    balance: 5432.1,
    currency: 'USD',
  }, // Model sees this
};
```

**When to use structuredContent:**

- Data objects that the model should see and reference
- Information that helps the model formulate contextual responses
- Structured data that matches your declared `outputSchema`

**Important:** Widget definitions should NOT go in `structuredContent`. They belong in `_meta` (see next section).

**Example from codebase:**
- **TypeScript**: [`ts_server/src/mortgage.ts`](../../toolkits/banking_mcp_server/ts_server/src/mortgage.ts) - `getMortgagePaymentsTool`
- **Python**: [`py_server/src/mortgage.py`](../../toolkits/banking_mcp_server/py_server/src/mortgage.py) - `get_mortgage_payments_tool`

### 5. \_meta Field in Tool Responses

**Rule:** The `_meta` field in tool responses is delivered only to the component (UI/app/system) and is NEVER seen by the model.

Use `_meta` for any information that needs to be sent to the front-end or app that either:

1. **Is not needed by the model** - UI implementation details, internal references, debug info
2. **Should not be seen by the model** - For risk mitigation reasons (preventing hallucination, ensuring security, maintaining data accuracy)

```typescript
handler: async (args: any, extra: any) => {
  return {
    // Note: When using Orchestrate widgets, a content block is not necessary.
    // IBM Orchestrate automatically exposes the necessary information to the model
    // (e.g., that a confirmation dialog is being shown).
    _meta: {
      // Model does NOT see any of this - only UI/app sees it
      'com.ibm.orchestrate/widget': {
        responseType: 'confirmation',
        confirmationText: '## Confirm Payment\n\nAmount: $100',
        onConfirm: { tool: 'confirm_payment', parameters: { id: '123' } },
        onCancel: { tool: 'cancel_payment', parameters: { id: '123' } },
      },
      'com.example/internal': {
        transactionReference: 'internal-ref-12345',
        debugInfo: { timestamp: '2025-01-01T00:00:00Z' },
      },
    },
  };
};
```

**When to use \_meta:**

**For UI/App needs:**

- **Widget definitions** - Confirmation dialogs, input pickers, date selectors, custom UI components
- **UI-specific configuration** - Layout hints, styling preferences, rendering instructions

**For risk mitigation:**

- **Sensitive data** - Information that should reach the app but not influence model reasoning
- **Internal identifiers** - Transaction IDs, correlation IDs that the model shouldn't reference

**Key benefits:**

- **Security**: Prevents model from seeing or referencing sensitive implementation details
- **Risk mitigation**: Eliminates hallucination risk for data the model doesn't need
- **Clean separation**: Keeps conversational context separate from technical implementation
- **Flexibility**: Allows rich app functionality without polluting model context

**Namespacing:**
Use reverse DNS notation with a slash for `_meta` keys:

- `com.ibm.orchestrate/widget` - For Watsonx Orchestrate widgets
- `com.yourcompany/feature` - For your custom app-specific data

**Examples in codebase:**

- **TypeScript**: [`ts_server/src/mortgage.ts`](../../toolkits/banking_mcp_server/ts_server/src/mortgage.ts) - `prepareMortgagePaymentTool`
- **Python**: [`py_server/src/mortgage.py`](../../toolkits/banking_mcp_server/py_server/src/mortgage.py) - `prepare_mortgage_payment_tool`

## Tool Visibility Rules

Tool visibility is controlled through the `_meta.ui.visibility` field and determines which tools the model can see in its available tools list and subsequently call. This is a critical security mechanism for preventing unauthorized actions.

### Default Behavior - Tools Visible to Model

**Rule:** By default, all tools are visible to the model and can be called during conversation.

```typescript
export const getBalanceTool = {
  name: 'get_balance',
  config: {
    title: 'Get Account Balance',
    description: 'Retrieve current account balance',
    inputSchema: {
      /* ... */
    },
  },
  // No _meta.ui.visibility = model can see and call this tool
  handler: async (args: any, extra: any) => {
    /* ... */
  },
};
```

**When to use:**

- Standard tools that the model should be able to call autonomously
- Read-only operations (getting balances, retrieving data)
- Tools that don't require explicit user confirmation
- Operations where model autonomy is desired and safe

### Hidden Tools - Only Callable by UI

**Rule:** Tools with `_meta.ui.visibility: ['app']` are hidden from the model and can only be called by UI components.

```typescript
export const confirmPaymentTool = {
  name: 'confirm_payment',
  config: {
    title: 'Confirm Payment',
    description: 'Confirm a previously prepared payment',
    inputSchema: {
      transactionId: z.string(),
      action: z.enum(['confirm', 'cancel']),
    },
    // No outputSchema - this tool returns user-facing messages, not structured data
    _meta: {
      ui: {
        visibility: ['app'], // 🔒 Hidden from model - only UI can call
      },
    },
  },
  handler: async (
    {
      transactionId,
      action,
    }: {
      transactionId: string;
      action: 'confirm' | 'cancel';
    },
    extra: any,
  ) => {
    /* ... */
  },
};
```

**When to use:**

- Confirmation steps in two-step transaction flows
- Actions that require explicit user consent (financial transactions, data sharing)
- Operations that should never be automatically triggered by the model
- Security-critical operations where user interaction is mandatory

**Critical security benefits:**

- **Prevents unauthorized actions**: Model cannot automatically confirm transactions
- **Enforces explicit consent**: Only user button clicks can trigger these tools
- **Regulatory compliance**: Ensures audit trail of explicit user approval
- **Liability protection**: Eliminates risk of model taking actions without permission

**Example from codebase:**
- **TypeScript**: [`ts_server/src/mortgage.ts`](../../toolkits/banking_mcp_server/ts_server/src/mortgage.ts) - `confirmOrCancelMortgagePaymentTool`
- **Python**: [`py_server/src/mortgage.py`](../../toolkits/banking_mcp_server/py_server/src/mortgage.py) - `confirm_or_cancel_mortgage_payment_tool`

### Two-Step Transaction Pattern

The most common use of tool visibility is in the two-step transaction pattern:

1. **Step 1 - Prepare Tool** (visible to model):
   - Model can call this to prepare a transaction
   - Returns a confirmation widget with transaction details
   - Specifies which hidden tool to call for confirm/cancel actions

2. **Step 2 - Confirm/Cancel Tool** (hidden from model):
   - Model cannot see or call this tool
   - Only callable by UI widget when user clicks Confirm or Cancel
   - Processes the user's explicit choice

This pattern ensures the model can initiate transactions but cannot complete them without explicit user approval.

**Complete example:** See [Transactions.md](./Transactions.md) for full implementation details.

## Summary Tables

### Content Visibility Summary

| Content Type                                              | Model Sees? | User Sees? | Notes                                                                                         |
| --------------------------------------------------------- | ----------- | ---------- | --------------------------------------------------------------------------------------------- |
| `content` (no annotations.audience)                       | ✅ Yes      | ✅ Yes     | Standard behavior for tool responses                                                          |
| `content` with `annotations: { audience: ['user'] }`      | ❌ No       | ✅ Yes     | Goes directly to user, bypasses LLM                                                           |
| `content` with `annotations: { audience: ['assistant'] }` | ✅ Yes      | ❌ No      | Provides context to model without showing user                                                |
| `structuredContent`                                       | ✅ Yes      | ✅ Yes     | Always visible to model - use for data model should see                                       |
| `_meta`                                                   | ❌ Never    | ❌ Never   | Hidden from model - use for widgets (`com.ibm.orchestrate/widget`), internal data, debug info |

### Tool Visibility Summary

| Tool Configuration             | Model Can See Tool? | Model Can Call Tool? | Use Case                                                                  |
| ------------------------------ | ------------------- | -------------------- | ------------------------------------------------------------------------- |
| No `_meta.ui.visibility`       | ✅ Yes              | ✅ Yes               | Standard tools (read operations, safe actions)                            |
| `_meta.ui.visibility: ['app']` | ❌ No               | ❌ No                | Confirmation tools, transaction completions, security-critical operations |

## Best Practices

### Content Visibility Best Practices

1. **Default to model visibility** for standard tool responses where natural conversation is desired and hallucination risk is low

2. **Use `annotations: { audience: ['user'] }` for critical data** that must be exact:
   - Financial amounts (balances, payments, transaction totals)
   - Dates and timestamps
   - Account numbers and identifiers
   - Any data where transcription errors create liability

3. **Use `annotations: { audience: ['assistant'] }` for context** when you want the model to provide natural language wrapping around user-targeted data:
   - "Payment history retrieved and displayed below"
   - "The table shows your recent transactions"
   - Instructions to politely decline calculations

4. **Consider latency implications**:
   - `annotations: { audience: ['user'] }` is fastest (bypasses LLM entirely)
   - `annotations: { audience: ['assistant'] }` + `annotations: { audience: ['user'] }` is middle ground (Hybrid Response)
   - No audience annotation requires full LLM processing

5. **Remember widgets are hidden** - the model doesn't see widget configurations in `structuredContent`, only the context you provide via `annotations: { audience: ['assistant'] }`

6. **Never put sensitive data in `_meta`** - it's for platform configuration only, not data

### Tool Visibility Best Practices

7. **Default tools to visible** for safe, read-only operations:
   - Getting balances, statements, transaction history
   - Retrieving customer information
   - Looking up data that doesn't modify state

8. **Hide tools that require explicit consent** using `_meta.ui.visibility: ['app']`:
   - Transaction confirmation/cancellation tools
   - Payment execution tools
   - Account modification tools
   - Any operation that changes state or moves money

9. **Use two-step patterns for transactions**:
   - Step 1: Prepare tool (visible to model) - validates and returns confirmation widget
   - Step 2: Confirm/cancel tool (hidden from model) - only callable by UI widget

### General Best Practices

12. **Balance natural interaction with accuracy** - use Hybrid Responses when you want both conversational flow and data guarantees

13. **Consider cross-tool reasoning limitations** - when data is hidden from the model via `annotations: { audience: ['user'] }`, it cannot reason across multiple tool outputs. This is a feature, not a bug - it prevents incorrect calculations

14. **Provide alternative paths** when the model cannot perform operations:
    - Create dedicated calculation tools in your code (zero hallucination risk)
    - Display all necessary data so users can make their own decisions
    - Have the model politely explain why it cannot perform certain operations

## Related Documentation

- [Tool Responses to Users](./ToolResponsesToUsers.md) - Direct bypass pattern
- [Hybrid Responses](./HybridResponses.md) - Natural conversation with data accuracy
- [Transactions](./Transactions.md) - Two-step confirmation pattern with tool visibility

## Conclusion

Model visibility control is a powerful tool for building customer care applications that balance natural conversation with the accuracy guarantees businesses require. By understanding these rules and patterns, you can:

- Eliminate hallucination risk for critical data
- Improve response times by bypassing unnecessary LLM processing
- Maintain natural conversational experiences where appropriate
- Ensure regulatory compliance through exact data formatting
- Prevent unauthorized transactions through tool visibility controls

**Remember:** Model instructions and hope are no way to run a business. These visibility controls provide the guarantees businesses need to feel confident in their agent's behavior.
