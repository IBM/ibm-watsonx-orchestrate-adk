# Extending the Banking MCP Server

This guide shows you how to extend the existing banking MCP server with new tools, resources, and capabilities. Use this approach when you want to add functionality to the demonstration server.

## Overview

The banking MCP server is organized into modular components. Both TypeScript and Python implementations follow the same architectural patterns:

**TypeScript Implementation (`toolkits/banking_mcp_server/ts_server/`):**
- **Tool Modules**: `src/personalBanking.ts`, `src/mortgage.ts`, `src/creditCard.ts`
- **Service Modules**: `src/personalBankingService.ts`, `src/mortgageService.ts`, `src/creditCardService.ts`
- **Context Management**: `src/globalStore.ts`, `src/localStore.ts`
- **Server Entry Point**: `src/index.ts`

**Python Implementation (`toolkits/banking_mcp_server/py_server/`):**
- **Tool Modules**: `src/customercare/personal_banking.py`, `src/customercare/mortgage.py`, `src/customercare/credit_card.py`
- **Service Modules**: `src/customercare/personal_banking_service.py`, `src/customercare/mortgage_service.py`, `src/customercare/credit_card_service.py`
- **Context Management**: `src/customercare/global_store.py`, `src/customercare/local_store.py`
- **Server Entry Point**: `src/customercare/main.py`

This modular structure makes it easy to add new features without disrupting existing functionality.

## Adding a New Tool to an Existing Product Line

Let's add a "get recent transactions" tool to personal banking.

### Step 1: Add Business Logic to the Service

First, implement the business logic in the service layer.

**TypeScript: `toolkits/banking_mcp_server/ts_server/src/personalBankingService.ts`**

```typescript
export class PersonalBankingService {
  // ... existing methods ...

  /**
   * Get recent transactions for an account
   */
  static getRecentTransactions(
    customerId: string,
    accountId: string,
    limit: number = 10
  ): Transaction[] {
    const accounts = this.getAccounts(customerId);
    const account = accounts.find(acc => acc.accountId === accountId);
    
    if (!account) {
      throw new Error(`Account ${accountId} not found`);
    }

    // In a real implementation, this would query a database
    // For demo purposes, return mock data
    return [
      {
        transactionId: 'TXN001',
        date: '2026-01-14',
        description: 'Coffee Shop',
        amount: -4.50,
        balance: 1245.50,
      },
      {
        transactionId: 'TXN002',
        date: '2026-01-13',
        description: 'Salary Deposit',
        amount: 3000.00,
        balance: 1250.00,
      },
      // ... more transactions
    ].slice(0, limit);
  }
}

interface Transaction {
  transactionId: string;
  date: string;
  description: string;
  amount: number;
  balance: number;
}
```

**Python: `toolkits/banking_mcp_server/py_server/src/personal_banking_service.py`**

```python
from typing import List
from dataclasses import dataclass

@dataclass
class Transaction:
    transaction_id: str
    date: str
    description: str
    amount: float
    balance: float

class PersonalBankingService:
    # ... existing methods ...
    
    @staticmethod
    def get_recent_transactions(
        customer_id: str,
        account_id: str,
        limit: int = 10
    ) -> List[Transaction]:
        """Get recent transactions for an account."""
        accounts = PersonalBankingService.get_accounts(customer_id)
        account = next((acc for acc in accounts if acc.account_id == account_id), None)
        
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        # In a real implementation, this would query a database
        # For demo purposes, return mock data
        transactions = [
            Transaction(
                transaction_id="TXN001",
                date="2026-01-14",
                description="Coffee Shop",
                amount=-4.50,
                balance=1245.50,
            ),
            Transaction(
                transaction_id="TXN002",
                date="2026-01-13",
                description="Salary Deposit",
                amount=3000.00,
                balance=1250.00,
            ),
            # ... more transactions
        ]
        
        return transactions[:limit]
```

### Step 2: Create the Tool Definition

Add the tool definition to the appropriate module.

**TypeScript: `toolkits/banking_mcp_server/ts_server/src/personalBanking.ts`**

```typescript
import { PersonalBankingService } from './personalBankingService';

/**
 * Tool: Get Recent Transactions
 * Returns recent transactions for a specific account
 */
const getRecentTransactionsTool = {
  name: 'get_recent_transactions',
  config: {
    description: 'Get recent transactions for a customer account',
    inputSchema: {
      type: 'object',
      properties: {
        customerId: {
          type: 'string',
          description: 'Customer identifier (injected from global store)',
        },
        accountId: {
          type: 'string',
          description: 'The account ID to get transactions for',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of transactions to return (default: 10)',
          default: 10,
        },
      },
      required: ['customerId', 'accountId'],
    },
  },
  handler: async (
    args: {
      customerId: string;
      accountId: string;
      limit?: number;
    },
    extra: any,
  ) => {
    try {
      const transactions = PersonalBankingService.getRecentTransactions(
        args.customerId,
        args.accountId,
        args.limit || 10
      );

      // Format as a table for display
      const tableRows = transactions.map(txn => 
        `| ${txn.date} | ${txn.description} | $${txn.amount.toFixed(2)} | $${txn.balance.toFixed(2)} |`
      ).join('\n');

      const response = `## Recent Transactions

| Date | Description | Amount | Balance |
|------|-------------|--------|---------|
${tableRows}

Showing ${transactions.length} most recent transactions.`;

      return {
        content: [
          {
            type: 'text',
            text: response,
          },
        ],
        // Send directly to user, bypassing LLM
        _meta: {
          audience: ['user'],
        },
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: 'text',
            text: `Error retrieving transactions: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  },
};

// Export the tool in the tools array
export const personalBankingTools = [
  getAccountBalanceTool,
  getAccountStatementTool,
  getRecentTransactionsTool,  // Add new tool here
  prepareTransferTool,
  confirmOrCancelTransferTool,
];
```

**Python: `toolkits/banking_mcp_server/py_server/src/personal_banking.py`**

```python
from mcp.types import Tool, TextContent
from .personal_banking_service import PersonalBankingService

def get_recent_transactions_tool():
    """Tool: Get Recent Transactions
    Returns recent transactions for a specific account.
    """
    return Tool(
        name="get_recent_transactions",
        description="Get recent transactions for a customer account",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer identifier (injected from global store)",
                },
                "account_id": {
                    "type": "string",
                    "description": "The account ID to get transactions for",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of transactions to return (default: 10)",
                    "default": 10,
                },
            },
            "required": ["customer_id", "account_id"],
        },
    )

async def handle_get_recent_transactions(arguments: dict) -> list[TextContent]:
    """Handler for get_recent_transactions tool."""
    try:
        transactions = PersonalBankingService.get_recent_transactions(
            arguments["customer_id"],
            arguments["account_id"],
            arguments.get("limit", 10)
        )
        
        # Format as a table for display
        table_rows = "\n".join([
            f"| {txn.date} | {txn.description} | ${txn.amount:.2f} | ${txn.balance:.2f} |"
            for txn in transactions
        ])
        
        response = f"""## Recent Transactions

| Date | Description | Amount | Balance |
|------|-------------|--------|---------|
{table_rows}

Showing {len(transactions)} most recent transactions."""
        
        return [
            TextContent(
                type="text",
                text=response,
                annotations={"audience": ["user"]},
            )
        ]
        
    except Exception as error:
        return [
            TextContent(
                type="text",
                text=f"Error retrieving transactions: {str(error)}",
            )
        ]

# Export the tool in the tools list
personal_banking_tools = [
    get_account_balance_tool(),
    get_account_statement_tool(),
    get_recent_transactions_tool(),  # Add new tool here
    prepare_transfer_tool(),
    confirm_or_cancel_transfer_tool(),
]
```

### Step 3: Test the New Tool

The tool is automatically registered when the server starts. Test it:

**TypeScript:**
1. Restart the MCP server: `cd ts_server && npm run dev`
2. Start the agent: `cd agent_runtime/examples/banking_agent && ./start.sh`

**Python:**
1. Restart the MCP server: `cd py_server && uv run customercare-server`
2. Start the agent: `cd agent_runtime/examples/banking_agent && ./start.sh`

**Test Query:**
3. Try: "Show me recent transactions for my checking account"

## Adding a New Product Line

Let's add a "Loans" product line with loan management tools.

### Step 1: Create the Service Module

**File: `src/loanService.ts`**

```typescript
export interface Loan {
  loanId: string;
  loanType: 'personal' | 'auto' | 'student';
  principal: number;
  balance: number;
  interestRate: number;
  monthlyPayment: number;
  nextPaymentDate: string;
}

export class LoanService {
  private static loans: Record<string, Loan[]> = {
    CUST001: [
      {
        loanId: 'LOAN001',
        loanType: 'auto',
        principal: 25000,
        balance: 18500,
        interestRate: 4.5,
        monthlyPayment: 450,
        nextPaymentDate: '2026-02-01',
      },
    ],
    CUST002: [
      {
        loanId: 'LOAN002',
        loanType: 'personal',
        principal: 10000,
        balance: 7500,
        interestRate: 8.9,
        monthlyPayment: 325,
        nextPaymentDate: '2026-02-01',
      },
    ],
  };

  static getLoans(customerId: string): Loan[] {
    return this.loans[customerId] || [];
  }

  static getLoanDetails(customerId: string, loanId: string): Loan {
    const loans = this.getLoans(customerId);
    const loan = loans.find(l => l.loanId === loanId);
    
    if (!loan) {
      throw new Error(`Loan ${loanId} not found`);
    }
    
    return loan;
  }
}
```

### Step 2: Create the Tool Module

**File: `src/loan.ts`**

```typescript
import { LoanService } from './loanService';

/**
 * Tool: Get Loan Details
 */
const getLoanDetailsTool = {
  name: 'get_loan_details',
  config: {
    description: 'Get details about a customer loan including balance, payment amount, and next payment date',
    inputSchema: {
      type: 'object',
      properties: {
        customerId: {
          type: 'string',
          description: 'Customer identifier (injected from global store)',
        },
        loanId: {
          type: 'string',
          description: 'The loan ID to get details for',
        },
      },
      required: ['customerId', 'loanId'],
    },
  },
  handler: async (
    args: {
      customerId: string;
      loanId: string;
    },
    extra: any,
  ) => {
    try {
      const loan = LoanService.getLoanDetails(args.customerId, args.loanId);

      const response = `## Loan Details

**Loan ID**: ${loan.loanId}
**Type**: ${loan.loanType.charAt(0).toUpperCase() + loan.loanType.slice(1)} Loan
**Original Amount**: $${loan.principal.toLocaleString()}
**Current Balance**: $${loan.balance.toLocaleString()}
**Interest Rate**: ${loan.interestRate}%
**Monthly Payment**: $${loan.monthlyPayment.toLocaleString()}
**Next Payment Due**: ${loan.nextPaymentDate}`;

      return {
        content: [
          {
            type: 'text',
            text: response,
          },
        ],
        _meta: {
          audience: ['user'],
        },
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: 'text',
            text: `Error retrieving loan details: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  },
};

export const loanTools = [getLoanDetailsTool];
```

### Step 3: Update Customer Database

Add loan entitlements to the customer database:

**File: `src/customerDatabase.ts`**

```typescript
export interface CustomerProducts {
  hasPersonalBanking: boolean;
  hasMortgage: boolean;
  hasCreditCard: boolean;
  hasLoan: boolean;  // Add new product
}

const customerDatabase: Record<string, CustomerProducts> = {
  CUST001: {
    hasPersonalBanking: true,
    hasMortgage: false,
    hasCreditCard: true,
    hasLoan: true,  // CUST001 has a loan
  },
  CUST002: {
    hasPersonalBanking: true,
    hasMortgage: true,
    hasCreditCard: false,
    hasLoan: true,  // CUST002 has a loan
  },
  // ... other customers
};

export function getCustomerProducts(customerId: string): CustomerProducts {
  return (
    customerDatabase[customerId] ?? {
      hasPersonalBanking: false,
      hasMortgage: false,
      hasCreditCard: false,
      hasLoan: false,
    }
  );
}
```

### Step 4: Register Tools in Server

Update the server to register loan tools:

**File: `src/index.ts`**

```typescript
import { loanTools } from './loan';

function createCustomerServer(customerId: string | undefined): McpServer {
  const server = new McpServer({
    name: 'customercare-banking-server',
    version: '1.0.0',
  });

  // ... existing tool registration ...

  if (!customerId) {
    return server;
  }

  const products = getCustomerProducts(customerId);

  // ... existing product registrations ...

  // Register loan tools if customer has loans
  if (products.hasLoan) {
    registerToolsWithCustomerId(server, loanTools);
  }

  return server;
}
```

### Step 5: Test the New Product Line

1. Restart the MCP server
2. Start the agent with CUST001 or CUST002
3. Try: "What's the status of my loan?"

## Adding a Widget-Based Tool

Let's add a tool that uses widgets for rich interaction.

**File: `src/personalBanking.ts`**

```typescript
/**
 * Tool: Schedule Payment
 * Uses widgets for date selection and confirmation
 */
const schedulePaymentTool = {
  name: 'schedule_payment',
  config: {
    description: 'Schedule a bill payment from a customer account',
    inputSchema: {
      type: 'object',
      properties: {
        customerId: {
          type: 'string',
          description: 'Customer identifier',
        },
        accountId: {
          type: 'string',
          description: 'Account to pay from',
        },
        payee: {
          type: 'string',
          description: 'Who to pay',
        },
        amount: {
          type: 'number',
          description: 'Payment amount',
        },
        paymentDate: {
          type: 'string',
          description: 'When to make the payment (YYYY-MM-DD)',
        },
      },
      required: ['customerId', 'payee', 'amount'],
    },
  },
  handler: async (args: any, extra: any) => {
    // Step 1: Select account if not provided
    if (!args.accountId) {
      const accounts = PersonalBankingService.getAccounts(args.customerId);
      const options = accounts.map(acc => ({
        value: acc.accountId,
        label: acc.accountName,
        description: `Balance: $${acc.balance.toLocaleString()}`,
      }));

      return {
        _meta: {
          'com.ibm.orchestrate/widget': {
            responseType: 'single-choice',
            title: 'Select Payment Account',
            description: 'Choose the account to pay from:',
            options,
            onChange: {
              toolName: 'schedule_payment',
              parameters: { ...args },
              mapSelectionTo: 'accountId',
            },
          },
        },
      };
    }

    // Step 2: Select payment date if not provided
    if (!args.paymentDate) {
      const today = new Date();
      const maxDate = new Date();
      maxDate.setDate(maxDate.getDate() + 90);

      return {
        _meta: {
          'com.ibm.orchestrate/widget': {
            responseType: 'date-picker',
            title: 'Select Payment Date',
            description: 'When should this payment be made?',
            minDate: today.toISOString().split('T')[0],
            maxDate: maxDate.toISOString().split('T')[0],
            onChange: {
              toolName: 'schedule_payment',
              parameters: { ...args },
              mapSelectionTo: 'paymentDate',
            },
          },
        },
      };
    }

    // Step 3: Show confirmation
    const account = PersonalBankingService.getAccounts(args.customerId)
      .find(acc => acc.accountId === args.accountId);

    return {
      _meta: {
        'com.ibm.orchestrate/widget': {
          responseType: 'confirmation',
          confirmationText: `## Confirm Payment

**Payee**: ${args.payee}
**Amount**: $${args.amount.toLocaleString()}
**From**: ${account?.accountName}
**Date**: ${args.paymentDate}

Do you want to schedule this payment?`,
          onConfirm: {
            tool: 'confirm_payment',
            parameters: { ...args, action: 'confirm' },
          },
          onCancel: {
            tool: 'confirm_payment',
            parameters: { ...args, action: 'cancel' },
          },
        },
      },
    };
  },
};
```

## Adding Resources

Resources provide data that the agent can read. Let's add a resource for loan information.

**File: `src/loan.ts`**

```typescript
/**
 * Resource: Customer Loans
 * Provides information about all loans for a customer
 */
const customerLoansResource = {
  name: 'Customer Loans',
  uri: 'banking://loans',
  description: 'Information about customer loans',
  mimeType: 'text/plain',
  handler: async (args: { customerId: string }, extra: any) => {
    const loans = LoanService.getLoans(args.customerId);

    if (loans.length === 0) {
      return {
        contents: [
          {
            uri: 'banking://loans',
            mimeType: 'text/plain',
            text: 'Customer has no active loans.',
          },
        ],
      };
    }

    const loanInfo = loans.map(loan => 
      `- ${loan.loanType.toUpperCase()} Loan (${loan.loanId}): $${loan.balance.toLocaleString()} balance, $${loan.monthlyPayment} monthly payment`
    ).join('\n');

    return {
      contents: [
        {
          uri: 'banking://loans',
          mimeType: 'text/plain',
          text: `Customer has ${loans.length} active loan(s):\n\n${loanInfo}`,
        },
      ],
    };
  },
};

export const loanResources = [customerLoansResource];
```

Register resources in `src/index.ts`:

```typescript
import { loanTools, loanResources } from './loan';

// In createCustomerServer function:
if (products.hasLoan) {
  registerToolsWithCustomerId(server, loanTools);
  registerResourcesWithCustomerId(server, loanResources);
}
```

## Best Practices

### 1. Separate Business Logic from MCP Interface

Keep business logic in service modules (`*Service.ts`) and MCP interface in tool modules (`*.ts`). This makes testing easier and keeps concerns separated.

### 2. Use Appropriate Context Layers

- **Context Variables**: For per-request data like JWT tokens
- **Global Store**: For conversation-wide data like customer ID
- **Local Store**: For MCP server-specific state like pending transactions

### 3. Provide Clear Tool Descriptions

The LLM uses tool descriptions to decide when to call them. Be specific:

```typescript
// Good
description: 'Get the current balance for a specific checking or savings account'

// Too vague
description: 'Get balance'
```

### 4. Handle Errors Gracefully

Always catch errors and return helpful messages:

```typescript
try {
  // Tool logic
} catch (error: any) {
  return {
    content: [{ type: 'text', text: `Error: ${error.message}` }],
    isError: true,
  };
}
```

### 5. Use Widgets for Structured Input

When users need to select from options or enter structured data, use widgets instead of relying on the LLM to parse free-form text.

### 6. Test with Multiple Customer Profiles

Create test customers with different product combinations to ensure tools are properly gated.

## Next Steps

- Read [Creating New Servers](CreatingNewServers.md) to build a completely new MCP server
- Study the [pattern documentation](../) for advanced techniques
- Explore the existing code in `src/` for more examples
- Experiment with different widget types and configurations