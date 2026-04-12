# Passing Context to Tools

## Overview

MCP servers need access to contextual information to properly serve authenticated users. This document explains the three distinct layers of context available in Watson Orchestrate MCP integrations and when to use each one.

## The Three Layers of Context

### Layer 1: Context Variables (API-Provided)

Context variables are passed by the caller of the Orchestrate API as part of the request. These can be system-provided (by Orchestrate), channel-provided (by Orchestrate) or application-provided (by the caller). They flow through to your MCP server via the `_meta` parameter.

**Use for:** Authentication tokens, tenant identifiers, or any data the calling application wants to provide.

**How to Access:**

Tool handlers receive context variables through the `extra._meta` parameter (TypeScript) or `_meta` parameter (Python):

**TypeScript:**
```typescript
handler: async (args: any, extra: any) => {
  // Access customer-provided context variables
  const jwtToken = extra?._meta?.['com.ibm.orchestrate/context']?.jwtToken;
  
  // Access system-provided context (e.g., thread_id, locale)
  const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
  const locale = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.locale;
  
  // Use the values directly
  const balance = await CreditCardService.getBalance(jwtToken);
}
```

**Python:**
```python
async def handler(args: dict, _meta: dict | None = None) -> dict:
    # Access customer-provided context variables
    jwt_token = _meta.get('com.ibm.orchestrate/context', {}).get('jwtToken') if _meta else None
    
    # Access system-provided context (e.g., thread_id, locale)
    thread_id = _meta.get('com.ibm.orchestrate/systemcontext', {}).get('thread_id') if _meta else None
    locale = _meta.get('com.ibm.orchestrate/systemcontext', {}).get('locale') if _meta else None
    
    # Use the values directly
    balance = CreditCardService.get_credit_card_balance(jwt_token)
```

**Key Point:** Context variables are automatically available in every tool handler via `extra._meta`. No additional setup required.

See [Context.md](./reference/Context.md) for complete details on system provided and customer provided context variables.

### Layer 2: Global Store (Conversation-Wide)

A **thread** represents an entire conversation in Watson Orchestrate and is identified by a unique `thread_id` provided in the system context. The thread persists for the duration of the conversation, regardless of how many MCP servers are involved.

The **global store** is a key-value store keyed by `thread_id` that can be accessed across all MCP servers within that conversation. This allows different MCP servers to share data within the same conversation context.

**Use for:** Global data that should be shared across all MCP servers in a conversation, such as:
- Customer ID (once authenticated)
- User permissions
- Tenant/organization ID
- Feature flags

**How to Access:**

1. **Extract `thread_id` from system context** (available in every tool handler)
2. **Look up variables in your global store** using the `thread_id` as the key

**TypeScript:**
```typescript
handler: async (args: any, extra: any) => {
  // Step 1: Get thread_id from system context
  const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
  
  // Step 2: Look up variables in your global store
  const customerId = getGlobalVariable(threadId, 'customerId');
  
  // Use the values
  const accounts = await BankingService.getAccounts(customerId);
}
```

**Python:**
```python
async def handler(args: dict, _meta: dict | None = None) -> dict:
    # Step 1: Get thread_id from system context
    thread_id = _meta.get('com.ibm.orchestrate/systemcontext', {}).get('thread_id') if _meta else None
    
    # Step 2: Look up variables in your global store
    customer_id = get_global_variable(thread_id, 'customerId')
    
    # Use the values
    accounts = BankingService.get_accounts(customer_id)
```

**Storage Requirement:** You must implement your own key-value store keyed by `thread_id`. Watson Orchestrate does not provide a global store implementation. See reference implementations:
- TypeScript: [`ts_server/src/globalStore.ts`](../toolkits/banking_mcp_server/ts_server/src/globalStore.ts)
- Python: [`py_server/src/global_store.py`](../toolkits/banking_mcp_server/py_server/src/global_store.py)

**Typical Pattern:** Store data in the global store during authentication or initialization, then retrieve it in subsequent tool calls within the same conversation.

### Layer 3: Local Store (MCP Server-Specific)

The **local store** is a key-value store that provides isolation for data specific to a single MCP server within a conversation. Like the global store, it is keyed by `thread_id`, but each MCP server maintains its own separate local store.

**Use for:** Transient data specific to a single MCP server's operations, such as:
- Pending transactions awaiting confirmation
- Multi-step operation state
- Temporary calculations
- Draft data before commit

**How to Access:**

1. **Extract `thread_id` from system context** (available in every tool handler)
2. **Look up variables in your local store** using the `thread_id` as the key

**TypeScript:**
```typescript
handler: async (args: any, extra: any) => {
  // Step 1: Get thread_id from system context
  const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
  
  // Step 2: Look up variables in your local store
  const transaction = getLocalVariable(threadId, `transaction_${transactionId}`);
  
  // Use the values
  if (action === 'confirm') {
    await BankingService.processTransaction(transaction);
  }
  
  // Clean up
  deleteLocalVariable(threadId, `transaction_${transactionId}`);
}
```

**Python:**
```python
async def handler(args: dict, _meta: dict | None = None) -> dict:
    # Step 1: Get thread_id from system context
    thread_id = _meta.get('com.ibm.orchestrate/systemcontext', {}).get('thread_id') if _meta else None
    
    # Step 2: Look up variables in your local store
    transaction = get_local_variable(thread_id, f'transaction_{transaction_id}')
    
    # Use the values
    if action == 'confirm':
        BankingService.process_transaction(transaction)
    
    # Clean up
    delete_local_variable(thread_id, f'transaction_{transaction_id}')
```

**Storage Requirement:** You must implement your own key-value store keyed by `thread_id`. Watson Orchestrate does not provide a local store implementation. See reference implementations:
- TypeScript: [`ts_server/src/localStore.ts`](../toolkits/banking_mcp_server/ts_server/src/localStore.ts)
- Python: [`py_server/src/local_store.py`](../toolkits/banking_mcp_server/py_server/src/local_store.py)

**Best Practice:** For optimal encapsulation and isolation, prefer local store variables for most transient data. Only use global store variables when data truly needs to be shared across multiple MCP servers.

**Important:** Both `thread_id` and the local store are accessed the same way - via `thread_id` from `extra._meta`. The difference is that each MCP server has its own local store instance, providing automatic isolation.

## Choosing the Right Layer

| Layer | Scope | Lifetime | Storage | Source | Use When |
|-------|-------|----------|---------|--------|----------|
| **Context Variables** | Request | Single API call | Watson Orchestrate | System (Orchestrate) or Application (caller) | Authentication/config data provided by caller |
| **Global Store** | Conversation (thread) | Until conversation ends | You implement | Your code | Data shared across MCP servers in conversation |
| **Local Store** | MCP Server within thread | Until thread ends | You implement | Your code | Data isolated per MCP server |

**Key Concepts:**
- A **thread** represents the entire conversation and has a unique `thread_id`
- The **global store** is shared across all MCP servers in a thread
- Each MCP server has its own **local store** for the thread, providing automatic isolation
- Both stores are keyed by `thread_id` but maintained separately

**General Recommendation:** For best encapsulation and isolation, prefer local store variables for most transient data. Only use global store variables when data truly needs to be shared across multiple MCP servers within the same conversation.

**Implementation Note:** Watson Orchestrate does not provide global or local store implementations. You must implement your own storage mechanisms (in-memory, Redis, database, etc.) keyed by `thread_id`.

## Complete Implementation Example

This example demonstrates all three layers working together in a banking application.

### Layer 1: Context Variables for Authentication

Credit card tools use JWT tokens passed via context variable on each request:

**TypeScript:** [`ts_server/src/creditCard.ts`](../toolkits/banking_mcp_server/ts_server/src/creditCard.ts)
**Python:** [`py_server/src/credit_card.py`](../toolkits/banking_mcp_server/py_server/src/credit_card.py)

```typescript
export const getCreditCardBalanceTool = {
  name: 'get_credit_card_balance',
  config: {
    title: 'Get Credit Card Balance',
    description: 'Retrieve current credit card balance',
    inputSchema: {
      // No authentication parameters - JWT comes from context
    },
  },
  handler: async (args: any, extra: any) => {
    // Extract JWT from context variables (Layer 1)
    const jwtToken = extra?._meta?.['com.ibm.orchestrate/context']?.jwtToken;
    
    if (!jwtToken) {
      throw new Error('JWT token required for authentication');
    }

    // Use JWT to authenticate with backend service
    const balance = CreditCardService.getCreditCardBalance(jwtToken);
    return { content: [{ type: 'text', text: `Balance: $${balance}` }] };
  },
};
```

**Server Setup:**
- TypeScript: [`ts_server/src/index.ts`](../toolkits/banking_mcp_server/ts_server/src/index.ts)
- Python: [`py_server/src/server.py`](../toolkits/banking_mcp_server/py_server/src/server.py)

```typescript
// Credit card tools use JWT from context - no injection needed
for (const tool of creditCardTools) {
  server.registerTool(tool.name, tool.config, tool.handler);
}
```

### Layer 2: Global Store for Customer Identity

Personal banking and mortgage tools use customer ID stored in the global store:

**Server Setup:**
- TypeScript: [`ts_server/src/index.ts`](../toolkits/banking_mcp_server/ts_server/src/index.ts)
- Python: [`py_server/src/server.py`](../toolkits/banking_mcp_server/py_server/src/server.py)

```typescript
// Extract thread_id from system context
const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;

// Store customer ID in global store (Layer 2)
if (threadId && customerId) {
  setGlobalVariable(threadId, 'customerId', customerId);
}

// Wrap handlers to inject customerId from global store
for (const tool of personalBankingTools) {
  const wrappedHandler = async (args: any, extra: any) => {
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
    const customerIdFromGlobal = threadId
      ? getGlobalVariable(threadId, 'customerId')
      : undefined;
    
    return tool.handler(
      {
        ...args,
        customerId: customerIdFromGlobal, // From Layer 2
      },
      extra,
    );
  };
  server.registerTool(tool.name, tool.config, wrappedHandler as any);
}
```

### Layer 3: Local Store for Pending Transactions

The local store provides isolation between MCP servers and is ideal for multi-step operations like transaction confirmation. The pattern involves storing operation details in the local store, then retrieving and processing them in a subsequent step.

**Storing in Local Store (Prepare Step):**

```typescript
// In prepare_money_transfer handler
handler: async (args: any, extra: any) => {
  const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
  const { customerId, fromAccount, toAccount, amount } = args;
  
  // Validate the transfer
  const validation = PersonalBankingService.validateTransfer(
    customerId, fromAccount, toAccount, amount
  );

  // Generate transaction ID
  const transactionId = `TXN-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  // Store transaction details in local store (Layer 3)
  setLocalVariable(threadId, `transaction_${transactionId}`, {
    transactionId,
    customerId,
    fromAccount,
    toAccount,
    amount,
    createdAt: new Date().toISOString(),
  });

  return { transactionId, status: 'pending' };
};
```

**Retrieving from Local Store (Confirm/Cancel Step):**

```typescript
// In confirm_or_cancel_money_transfer handler
handler: async (args: any, extra: any) => {
  const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
  const { customerId, transactionId, action } = args;
  
  // Retrieve transaction from local store (Layer 3)
  const transaction = getLocalVariable(threadId, `transaction_${transactionId}`);

  if (!transaction) {
    throw new Error(`Transaction ${transactionId} not found`);
  }

  // Verify ownership (security check)
  if (transaction.customerId !== customerId) {
    throw new Error('Transaction does not belong to this customer');
  }

  if (action === 'confirm') {
    // Process the transfer
    const result = PersonalBankingService.transferMoney(
      transaction.customerId,
      transaction.fromAccount,
      transaction.toAccount,
      transaction.amount,
    );
  }

  // Clean up local variable after processing
  deleteLocalVariable(threadId, `transaction_${transactionId}`);

  return { status: action === 'confirm' ? 'completed' : 'cancelled' };
};
```

**Why Local Store?**

This pattern uses the local store (Layer 3) instead of the global store (Layer 2) for important reasons:

1. **Encapsulation**: Transaction data is isolated to the personal banking MCP server. Other MCP servers in the same thread cannot access or interfere with these transactions.

2. **Security**: Each MCP server has its own local store, preventing cross-contamination of sensitive operation data.

3. **Clarity**: It's immediately clear which MCP server owns and manages the transaction data.

If we used the global store instead, all MCP servers in the conversation could potentially access and modify the transaction data, creating security and data integrity risks.

See the complete implementation:
- TypeScript: [`ts_server/src/personalBanking.ts`](../toolkits/banking_mcp_server/ts_server/src/personalBanking.ts) and [`ts_server/src/mortgage.ts`](../toolkits/banking_mcp_server/ts_server/src/mortgage.ts)
- Python: [`py_server/src/personal_banking.py`](../toolkits/banking_mcp_server/py_server/src/personal_banking.py) and [`py_server/src/mortgage.py`](../toolkits/banking_mcp_server/py_server/src/mortgage.py)

## Security Considerations

### Never Trust the Model

**Critical Rule:** Never rely on the model to provide authentication or authorization data.

- ❌ **Wrong:** Including `customerId` in the input schema and trusting the model to pass it
- ✅ **Right:** Injecting `customerId` from thread store or extracting from JWT

The model could:
- Forget to include the parameter
- Pass the wrong value
- Be manipulated to access another customer's data

## Key Takeaways

1. **Three distinct layers** serve different purposes:
   - Context Variables: per request API-provided authentication/config
   - Global Store: Conversation-wide data shared across MCP servers
   - Local Store: Transient data isolated per MCP server

2. **Choose the right layer** based on scope and lifetime:
   - Use context variables for caller-provided data
   - Use global store for data shared across MCP servers
   - Use local store for transient, operation-specific data within a single MCP server

3. **Security first:**
   - Never trust the model for authentication data
   - Always inject controlled data from your application

4. **Encapsulation matters:**
   - Prefer local store for isolation
   - Only use global store when truly needed

## Related Documentation

- [Context.md](./reference/Context.md) - System and customer context details
- [Authentication.md](./Authentication.md) - Authentication patterns
- [Transactions.md](./Transactions.md) - Multi-step transaction patterns
