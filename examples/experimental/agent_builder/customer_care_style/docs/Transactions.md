# Transaction Pattern

## Overview

This pattern demonstrates how to implement secure, user-confirmed transactions that require explicit approval before execution. The pattern uses a two-step flow with a customizable confirmation dialog to ensure that customers explicitly approve changes before they take effect, and that the model cannot automatically confirm transactions on behalf of users.

## Problems This Pattern Solves

### **Preventing Unauthorized Transactions**

When a customer requests a financial transaction like "Pay my mortgage" or "Transfer $500 to savings," the system must ensure:

- The user sees exactly what will happen before it occurs
- The user explicitly confirms the specific transaction details
- The model cannot automatically approve or modify the transaction
- The exact transaction the user approved is what gets executed

Without proper safeguards, there are significant risks:

- The model might misinterpret the user's intent and execute the wrong transaction
- The model could hallucinate different amounts or accounts after the user confirms
- Regulatory compliance requirements for explicit user consent might be violated
- Liability exposure from unauthorized or incorrect transactions

The Transaction Pattern eliminates these risks by requiring explicit user interaction through a confirmation dialog that the model cannot bypass.

### **Regulatory Compliance and Audit Trails**

Many industries require explicit user consent for transactions:

- **Financial services**: Regulations often mandate that customers explicitly approve transfers, payments, and account changes
- **Healthcare**: HIPAA and other regulations require explicit consent for sharing medical information
- **Legal services**: Client authorization is required before taking actions on their behalf

The Transaction Pattern provides:

- Clear audit trails showing the user explicitly confirmed the transaction
- Separation between transaction preparation and execution
- Explicit user action captured through UI interactions

### **Customizable Confirmation Experience**

Different transactions require different confirmation experiences. The Transaction Pattern allows you to:

- Customize the confirmation dialog content with markdown or HTML
- Display transaction-specific details (amounts, dates, accounts, etc.)
- Add warnings or important notices (e.g., "This transaction will expire in 5 minutes")
- Provide clear confirm and cancel options
- Maintain consistent UX across different transaction types

## Implementation Walkthrough

Below we walk through the mortgage payment transaction that demonstrates this pattern.

### Two-Step Transaction Flow

The Transaction Pattern uses a two-step flow and two corresponding tools. One of these tools is seen by the model and one is not preventing the model from being able to confirm the transaction :

1. **Prepare Step**: Validates the request and returns a confirmation dialog
2. **Confirm/Cancel Step**: Processes the user's explicit choice

**Implementation Files:**
- **TypeScript**: [`ts_server/src/mortgage.ts`](../toolkits/banking_mcp_server/ts_server/src/mortgage.ts)
- **Python**: [`py_server/src/mortgage.py`](../toolkits/banking_mcp_server/py_server/src/mortgage.py)

### Step 1: Prepare the Transaction

The prepare tool validates the request and returns a structured confirmation dialog. Here's the mortgage payment example:

```typescript
// Step 1: Prepare mortgage payment
export const prepareMortgagePaymentTool = {
  name: 'prepare_mortgage_payment',
  config: {
    title: 'Prepare Mortgage Payment',
    description: 'Prepare a mortgage payment for user confirmation',
    inputSchema: {
      amount: z.number().positive(),
      paymentDate: z.string().optional()
    }
  },
  handler: async (args: any, extra: any) => {
    const { customerId, amount, paymentDate } = args;
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
    
    if (!threadId) {
      throw new Error('Thread ID is required');
    }
    
    // Validate payment date
    const validation = validatePaymentDate(paymentDate);
    if (!validation.isValid) {
      return {
        content: [{
          type: 'text',
          text: validation.error,
          annotations: { audience: ['user'] }
        }],
        isError: true
      };
    }
    
    // Generate payment ID
    const paymentId = generatePaymentId();
    
    // Store payment in local store (MCP server-specific)
    setLocalVariable(threadId, `payment_${paymentId}`, {
      paymentId,
      customerId,
      amount,
      paymentDate: validation.date,
      createdAt: new Date().toISOString()
    });
    
    // Return confirmation widget
    return {
      _meta: {
        'com.ibm.orchestrate/widget': {
          type: 'confirmation',
          confirmation_text: `## Confirm Mortgage Payment\n\n**Amount:** $${amount.toFixed(2)}\n**Payment Date:** ${validation.date}\n\n⚠️ This payment will be processed immediately and cannot be reversed.`,
          description: 'Transaction confirmation',
          confirmation_details: {
            label: 'Confirm',
            value: 'confirm'
          },
          cancelation_details: {
            label: 'Cancel',
            value: 'cancel'
          },
          on_event: {
            tool: 'confirm_or_cancel_mortgage_payment',
            parameters: { paymentId },
            map_input_to: 'action'
          }
        }
      }
    };
  }
};
```

**Key aspects:**

1. **Validation First**: Validate the transaction before storing anything
2. **Transaction ID**: Generate a unique ID to track this specific transaction
3. **Local Storage**: Store transaction details in the local store (transient, MCP server-specific)
4. **Confirmation Widget**: Return a confirmation dialog with the transaction details
5. **Widget Actions**: Specify which tool to call for confirm/cancel with the transaction ID

### Step 2: Confirm or Cancel

The second tool handles the user's explicit choice:

```typescript
// Step 2: Confirm or cancel mortgage payment (hidden from model)
export const confirmOrCancelMortgagePaymentTool = {
  name: 'confirm_or_cancel_mortgage_payment',
  config: {
    title: 'Confirm or Cancel Mortgage Payment',
    inputSchema: {
      paymentId: z.string(),
      action: z.enum(['confirm', 'cancel'])
    },
    // No outputSchema - this tool returns user-facing messages, not structured data
    _meta: {
      ui: { visibility: ['app'] }  // 🔒 Hidden from model
    }
  },
  handler: async (args: any, extra: any) => {
    const { customerId, paymentId, action } = args;
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
    
    if (!threadId) {
      throw new Error('Thread ID is required');
    }
    
    // Retrieve payment from local store
    const payment = getLocalVariable(threadId, `payment_${paymentId}`);
    
    if (!payment) {
      throw new Error('Payment not found or expired');
    }
    
    // Verify ownership (security check)
    if (payment.customerId !== customerId) {
      throw new Error('Payment does not belong to this customer');
    }
    
    // Clean up local variable
    deleteLocalVariable(threadId, `payment_${paymentId}`);
    
    if (action === 'confirm') {
      // Process the mortgage payment
      const result = processMortgagePayment(payment);
      return {
        content: [{
          type: 'text',
          text: `Mortgage payment confirmed! Your payment of $${payment.amount.toFixed(2)} has been scheduled for ${payment.paymentDate}. Confirmation number: ${result.confirmationNumber}`,
          annotations: { audience: ['user'] }
        }]
      };
    }
    
    // Handle cancellation
    return {
      content: [{
        type: 'text',
        text: 'Mortgage payment cancelled. No payment has been processed.',
        annotations: { audience: ['user'] }
      }]
    };
  }
};
```

**Key aspects:**

1. **Hidden from Model**: `visibility: ['app']` prevents model from auto-confirming
2. **Retrieve from Local Store**: Get transaction details using the transaction ID
3. **Security Check**: Verify the transaction belongs to this customer
4. **Cleanup**: Delete local variable after processing
5. **Process or Cancel**: Execute the transaction or cancel based on user action

#### Full Working Examples

For complete production implementations with date validation, detailed error handling, and formatted confirmation dialogs, see:

**TypeScript:**
- **Mortgage Payments**: [`ts_server/src/mortgage.ts`](../toolkits/banking_mcp_server/ts_server/src/mortgage.ts) - Shows payment preparation with date validation and expiration handling
- **Money Transfers**: [`ts_server/src/personalBanking.ts`](../toolkits/banking_mcp_server/ts_server/src/personalBanking.ts) - Demonstrates multi-step widget flow with account selection before confirmation

**Python:**
- **Mortgage Payments**: [`py_server/src/mortgage.py`](../toolkits/banking_mcp_server/py_server/src/mortgage.py) - Shows payment preparation with date validation and expiration handling
- **Money Transfers**: [`py_server/src/personal_banking.py`](../toolkits/banking_mcp_server/py_server/src/personal_banking.py) - Demonstrates multi-step widget flow with account selection before confirmation

### How the Transaction Flow Works

The complete transaction flow demonstrates the use of the local store (Layer 3) for secure transaction handling:

1. **User Request**: Customer initiates a transaction (e.g., "Pay my mortgage $1,500")
2. **Model Calls Prepare Tool**: The model invokes `prepare_mortgage_payment` with the amount and optional payment date
3. **Validation & Storage**: The prepare tool:
   - Extracts `thread_id` from system context
   - Validates the payment date
   - Generates a unique payment ID
   - Stores payment details in the **local store** (keyed by `thread_id`, isolated per MCP server)
   - Returns a confirmation widget with the payment ID
4. **Widget Rendered**: The confirmation widget displays with payment details and Confirm/Cancel buttons
5. **User Clicks Button**: The user explicitly clicks either "Confirm" or "Cancel"
6. **Widget Calls Confirm/Cancel Tool**: The widget directly invokes `confirm_or_cancel_mortgage_payment` with the payment ID and action
7. **Retrieval & Processing**: The confirm/cancel tool:
   - Extracts `thread_id` from system context
   - Retrieves payment details from the **local store** using the payment ID
   - Verifies ownership (security check)
   - Processes or cancels the mortgage payment
   - Cleans up the local variable
8. **Model Informed**: The model receives context about what happened via the `annotations: { audience: ['assistant'] }` content

**Why Local Store?**

This pattern uses the **local store** (Layer 3) instead of the global store (Layer 2) for important security and encapsulation reasons:

- **Isolation**: Payment data is isolated to the mortgage MCP server. Other MCP servers in the same thread cannot access or interfere with these payments.
- **Security**: Each MCP server has its own local store, preventing cross-contamination of sensitive transaction data.
- **Clarity**: It's immediately clear which MCP server owns and manages the payment data.
- **Transient Nature**: Payment confirmations are temporary operations that don't need to persist beyond the thread.

If we used the global store instead, all MCP servers in the conversation could potentially access and modify the payment data, creating security and data integrity risks.

**Important**: The model never has the ability to call the confirm/cancel tool directly. It can only prepare transactions and present them to users for explicit approval. See [Passing Context to Tools](PassingContextToTools.md) for more details on the three layers of context.

## Key Takeaways

The Transaction Pattern provides essential safeguards for customer care applications that handle sensitive operations:

- **Explicit User Consent**: Ensures customers explicitly approve transactions through UI interactions, not through conversational ambiguity
- **Zero Hallucination Risk**: The exact transaction the user approves is what gets executed, with no possibility of the model changing details
- **Model Cannot Auto-Confirm**: The `visibility: ['app']` setting prevents the model from bypassing user confirmation
- **Regulatory Compliance**: Provides clear audit trails and explicit consent mechanisms required in regulated industries
- **Customizable Experience**: Confirmation dialogs can be tailored with markdown to show transaction-specific details and warnings
- **Time-Limited Transactions**: Expiration windows prevent stale confirmations and ensure timely user action
- **Separation of Concerns**: Clear separation between transaction preparation (model-callable) and execution (user-only)

**When to use this pattern:**

- Financial transactions (payments, transfers, withdrawals)
- Account modifications (address changes, beneficiary updates)
- Data sharing or consent operations
- Any operation requiring explicit user approval for regulatory or risk mitigation reasons

**Trade-offs:**

- Adds an extra step to the user flow (prepare → confirm → execute)
- Requires UI support for confirmation widgets
- Slightly more complex implementation than direct tool execution

The Transaction Pattern is essential for customer care applications in regulated industries where explicit user consent, audit trails, and liability protection are paramount. Model instructions and hope are no way to run a business. This pattern provides the guarantees businesses need to feel confident their agents cannot execute unauthorized transactions.
