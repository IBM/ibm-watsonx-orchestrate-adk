 /**
 * Personal Banking Tools Module
 *
 * Contains tool definitions for personal banking operations
 */

import { z } from 'zod';
import { PersonalBankingService } from './personalBankingService';
import {
  deleteLocalVariable,
  getLocalVariable,
  setLocalVariable,
} from './localStore';

/**
 * Get account balance tool definition
 */
export const getAccountBalanceTool = {
  name: 'get_account_balance',
  config: {
    title: 'Get Account Balance',
    description:
      'Retrieve current account balance for the authenticated customer',
    inputSchema: {
      accountType: z.enum(['checking', 'savings']).describe('Type of account'),
    },
    outputSchema: {
      customerId: z.string(),
      accountType: z.string(),
      balance: z.number(),
      currency: z.string(),
      asOfDate: z.string(),
    },
  },
  handler: async (
    {
      customerId,
      accountType,
    }: {
      customerId: string;
      accountType: string;
    },
    extra: any,
  ) => {
    const accountBalance = PersonalBankingService.getAccountBalance(
      customerId,
      accountType,
    );

    return {
      content: [
        {
          type: 'text',
          text: `Account Balance:\nCustomer ID: ${accountBalance.customerId}\nAccount Type: ${accountBalance.accountType}\nBalance: $${accountBalance.balance.toFixed(2)} ${accountBalance.currency}\nAs of: ${accountBalance.asOfDate}`,
        },
      ],
      structuredContent: accountBalance,
    };
  },
};

/**
 * Get account statement tool definition
 */
export const getAccountStatementTool = {
  name: 'get_account_statement',
  config: {
    title: 'Get Account Statement',
    description:
      'Retrieve recent account statement with transactions for the authenticated customer',
    inputSchema: {
      accountType: z.enum(['checking', 'savings']).describe('Type of account'),
      days: z
        .number()
        .optional()
        .describe('Number of days to retrieve (default: 30)'),
    },
    outputSchema: {
      customerId: z.string(),
      accountType: z.string(),
      startDate: z.string(),
      endDate: z.string(),
      transactions: z.array(
        z.object({
          date: z.string(),
          description: z.string(),
          amount: z.number(),
          balance: z.number(),
        }),
      ),
    },
  },
  handler: async (
    {
      customerId,
      accountType,
      days = 30,
    }: {
      customerId: string;
      accountType: string;
      days?: number;
    },
    extra: any,
  ) => {
    const accountStatement = PersonalBankingService.getAccountStatement(
      customerId,
      accountType,
      days,
    );

    const transactionText = accountStatement.transactions
      .map(
        t =>
          `  ${t.date} | ${t.description.padEnd(35)} | ${t.amount >= 0 ? '+' : ''}$${t.amount.toFixed(2).padStart(10)} | Balance: $${t.balance.toFixed(2)}`,
      )
      .join('\n');

    return {
      content: [
        {
          type: 'text',
          text: `Account Statement:\nCustomer ID: ${accountStatement.customerId}\nAccount Type: ${accountStatement.accountType}\nPeriod: ${accountStatement.startDate} to ${accountStatement.endDate}\n\nRecent Transactions:\n${transactionText}`,
        },
      ],
      structuredContent: accountStatement,
    };
  },
};

/**
 * Prepare money transfer tool definition
 *
 * This is the FIRST STEP in a two-step transaction pattern.
 * It collects transfer details through interactive widgets (account pickers, date picker)
 * and then presents a confirmation dialog with the transfer details.
 *
 * The confirmation dialog uses IBM Orchestrate's built-in widget to display
 * transfer details and capture explicit user intent with Confirm/Cancel buttons.
 */
export const prepareTransferTool = {
  name: 'prepare_money_transfer',
  config: {
    title: 'Prepare Money Transfer',
    description:
      'Prepare a transfer between your accounts. IMPORTANT: When the user specifies an account by name (e.g., "my son\'s account" or "my checking account"), use the "Available Accounts" resource to look up and confirm the account ID.',
    inputSchema: {
      fromAccountId: z
        .string()
        .optional()
        .describe(
          'Account ID to transfer from. If not provided, a picker will be shown after the tool has been called. If user specifies by name, look up in "Available Accounts" resource.',
        ),
      toAccountId: z
        .string()
        .optional()
        .describe(
          'Account ID to transfer to. If not provided, a picker will be shown after the tool has been called. If user specifies by name, look up in "Available Accounts" resource.',
        ),
      amount: z.number().min(0.01).describe('Amount to transfer in USD'),
      scheduledDate: z
        .string()
        .optional()
        .describe(
          'Date to schedule the transfer in YYYY-MM-DD format (e.g., 2025-04-15)',
        ),
      memo: z
        .string()
        .optional()
        .describe('Optional memo or description for the transfer'),
    },
    // No outputSchema - this tool returns widgets and user-facing messages, not structured data for the model
  },
  _meta: {
    ui: {
      // Reference IBM Orchestrate's built-in widget
      resourceUri: 'ui://ibm.com/orchestrate/widget',
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
    const threadId =
      extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;

    if (!threadId) {
      throw new Error('Thread ID is required');
    }
    const allAccounts = PersonalBankingService.getAccounts(args.customerId);

    // Step 1: If fromAccountId is missing, show picker for "from" account
    if (!args.fromAccountId) {
      // Filter accounts that can transfer from AND exclude the toAccountId if already selected
      const fromAccounts = allAccounts.filter(
        acc => acc.canTransferFrom && acc.accountId !== args.toAccountId,
      );

      const pickerOptions = fromAccounts.map(acc => {
        const holder = acc.accountHolder ? ` (${acc.accountHolder})` : '';
        return {
          value: acc.accountId,
          label: `${acc.accountName}${holder}`,
          description: `${acc.accountType} - ${acc.accountId}`,
        };
      });

      const pickerWidget = {
        type: 'options',
        title: 'Select Account to Transfer From',
        description: 'Choose the account you want to transfer money from:',
        options: pickerOptions,
        on_event: {
          tool: 'prepare_money_transfer',
          parameters: {
            ...args,
          },
          map_input_to: 'fromAccountId',
        },
      };

      return {
        _meta: {
          'com.ibm.orchestrate/widget': pickerWidget,
        },
      };
    }

    // Step 2: Check if the from account is locked (once fromAccountId is present)
    const selectedFromAccount = allAccounts.find(
      acc => acc.accountId === args.fromAccountId,
    );

    if (selectedFromAccount?.isLocked) {
      return {
        content: [
          {
            type: 'text',
            text: `I'm sorry, but your ${selectedFromAccount.accountName} account (${selectedFromAccount.accountId}) is currently locked. You'll need to speak with a customer service agent to resolve this issue before you can transfer funds from this account.`,
            annotations: { audience: ['user'] },
          },
        ],
        _meta: {
          nextTool: {
            name: 'request_agent_handoff',
            arguments: {
              reason: `Customer attempted to transfer from locked account: ${selectedFromAccount.accountName} (${selectedFromAccount.accountId})`,
            },
          },
        },
      };
    }

    // Step 3: If toAccountId is missing, show picker for "to" account
    if (!args.toAccountId) {
      // Filter accounts that can receive transfers AND exclude the fromAccountId
      const toAccounts = allAccounts.filter(
        acc => acc.canTransferTo && acc.accountId !== args.fromAccountId,
      );

      const pickerOptions = toAccounts.map(acc => {
        const holder = acc.accountHolder ? ` (${acc.accountHolder})` : '';
        return {
          value: acc.accountId,
          label: `${acc.accountName}${holder}`,
          description: `${acc.accountType} - ${acc.accountId}`,
        };
      });

      const pickerWidget = {
        type: 'options',
        title: 'Select Account to Transfer To',
        description: 'Choose the account you want to transfer money to:',
        options: pickerOptions,
        on_event: {
          tool: 'prepare_money_transfer',
          parameters: {
            ...args,
          },
          map_input_to: 'toAccountId',
        },
      };

      return {
        _meta: {
          'com.ibm.orchestrate/widget': pickerWidget,
        },
      };
    }

    // Step 4: If scheduledDate is missing, show date picker
    if (!args.scheduledDate) {
      // Calculate date range: 3 days from now to 30 days from now
      const today = new Date();
      const minDate = new Date(today);
      minDate.setDate(today.getDate() + 3);
      const maxDate = new Date(today);
      maxDate.setDate(today.getDate() + 30);

      const datePickerWidget = {
        type: 'datetime',
        collection_type: 'date',
        title: 'Select Transfer Date',
        description:
          'Choose when you want the transfer to occur (must be at least 3 days from now, within 30 days):',
        min_datetime: minDate.toISOString().split('T')[0], // Format: YYYY-MM-DD
        max_datetime: maxDate.toISOString().split('T')[0], // Format: YYYY-MM-DD
        on_event: {
          tool: 'prepare_money_transfer',
          parameters: {
            ...args,
          },
          map_input_to: 'scheduledDate',
        },
      };

      return {
        _meta: {
          'com.ibm.orchestrate/widget': datePickerWidget,
        },
      };
    }

    // Step 5: All required info collected, validate the transfer
    const { fromAccount, toAccount } = PersonalBankingService.validateTransfer(
      args.customerId,
      args.fromAccountId,
      args.toAccountId,
      args.amount,
    );

    // Generate transaction ID in the tool (not in service)
    const transactionId = `TXN-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Create transaction details object
    const transactionDetails = {
      customerId: args.customerId,
      transactionId,
      fromAccountId: args.fromAccountId,
      fromAccountName: fromAccount.accountName,
      toAccountId: args.toAccountId,
      toAccountName: toAccount.accountName,
      amount: args.amount,
      scheduledDate: args.scheduledDate,
      memo: args.memo,
      createdAt: new Date().toISOString(),
    };

    // Store transaction details in LOCAL STORE
    // This is transient data that only matters during the confirmation flow
    // and is specific to this MCP server within the thread
    setLocalVariable(
      threadId,
      `transaction_${transactionId}`,
      transactionDetails,
    );

    const scheduleText = args.scheduledDate
      ? `\n- **Scheduled Date:** ${args.scheduledDate}`
      : '\n- **Processing:** Immediate';
    const memoText = args.memo ? `\n- **Memo:** ${args.memo}` : '';

    // Confirmation widget definition
    const confirmationWidget = {
      type: 'confirmation',
      title: 'Confirm Transfer',
      confirmation_text: `## Confirm Transfer\n\nPlease review the transfer details below and confirm to proceed:\n\n**Transfer Details:**\n- **From Account:** ${fromAccount.accountName} (${args.fromAccountId})\n- **To Account:** ${toAccount.accountName} (${args.toAccountId})\n- **Amount:** $${args.amount.toFixed(2)}${scheduleText}${memoText}\n\n**Transaction ID:** ${transactionId}`,
      on_confirm: {
        tool: 'confirm_or_cancel_money_transfer',
        parameters: {
          transactionId,
          action: 'confirm',
        },
      },
      on_cancel: {
        tool: 'confirm_or_cancel_money_transfer',
        parameters: {
          transactionId,
          action: 'cancel',
        },
      },
    };

    return {
      _meta: {
        'com.ibm.orchestrate/widget': confirmationWidget,
      },
    };
  },
};

/**
 * Confirm or cancel money transfer tool definition
 *
 * This is the SECOND STEP in a two-step transaction pattern.
 * It handles user actions (confirm or cancel) for a previously prepared money transfer.
 *
 * IMPORTANT: This tool is hidden from the model (visibility: ["app"]) to ensure
 * that only the user can explicitly confirm or cancel transfers through the UI widget.
 * The model should never be able to automatically confirm financial transactions
 * without direct user interaction.
 */
export const confirmOrCancelTransferTool = {
  name: 'confirm_or_cancel_money_transfer',
  config: {
    title: 'Confirm or Cancel Money Transfer',
    description:
      'Handle user action (confirm or cancel) for a previously prepared money transfer using the transaction ID.',
    inputSchema: {
      transactionId: z
        .string()
        .describe('Transaction ID from prepare_money_transfer'),
      action: z
        .enum(['confirm', 'cancel'])
        .describe('User action: confirm to process transfer, cancel to abort'),
    },
    // No outputSchema - this tool returns user-facing messages, not structured data
    _meta: {
      ui: {
        visibility: ['app'], // 🔒 Hidden from model - only callable by UI widget for explicit user confirmation
      },
    },
  },
  handler: async (
    params: {
      customerId: string;
      transactionId: string;
      action: 'confirm' | 'cancel';
    },
    extra: any,
  ) => {
    const { customerId, transactionId, action } = params;
    const threadId =
      extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;

    if (!threadId) {
      throw new Error('Thread ID is required');
    }

    // Retrieve transaction from LOCAL STORE
    const transaction = getLocalVariable(
      threadId,
      `transaction_${transactionId}`,
    );

    if (!transaction) {
      throw new Error(
        `Transaction ${transactionId} not found. It may have expired or been processed already.`,
      );
    }

    // Verify transaction belongs to this customer (security check)
    if (transaction.customerId !== customerId) {
      throw new Error('Transaction does not belong to this customer');
    }

    // Clean up local variable (transaction is being processed or cancelled)
    deleteLocalVariable(threadId, `transaction_${transactionId}`);

    if (action === 'cancel') {
      // Handle cancellation
      const scheduleText = transaction.scheduledDate
        ? `\n- Scheduled Date: ${transaction.scheduledDate}`
        : '';
      return {
        content: [
          {
            type: 'text',
            text: `Transfer Cancelled\n\nTransaction ID: ${transactionId}\n\nThe transfer has been cancelled and no funds were moved.\n\nTransfer Details:\n- From Account: ${transaction.fromAccountName} (${transaction.fromAccountId})\n- To Account: ${transaction.toAccountName} (${transaction.toAccountId})\n- Amount: $${transaction.amount.toFixed(2)}${scheduleText}`,
            annotations: { audience: ['user'] },
          },
          {
            type: 'text',
            text: `The transfer with transaction ID ${transactionId} has been cancelled by the user.`,
            annotations: { audience: ['assistant'] },
          },
        ],
      };
    }

    // Handle confirmation - process the actual transfer
    const transferResult = PersonalBankingService.transferMoney(
      transaction.customerId,
      transaction.fromAccountId,
      transaction.toAccountId,
      transaction.amount,
      transaction.scheduledDate,
      transaction.memo,
    );

    const scheduleText = transaction.scheduledDate
      ? `\n- Scheduled Date: ${transaction.scheduledDate}\n- Status: Scheduled`
      : '\n- Status: Completed immediately';

    return {
      content: [
        {
          type: 'text',
          text: `✅ Transfer Confirmed Successfully!\n\nConfirmation Number: ${transferResult.transferId}\nTransaction ID: ${transactionId}\n\nTransfer Details:\n- From Account: ${transaction.fromAccountName} (${transaction.fromAccountId})\n- To Account: ${transaction.toAccountName} (${transaction.toAccountId})\n- Amount: $${transaction.amount.toFixed(2)}${scheduleText}\n- Confirmed At: ${new Date(transferResult.timestamp).toLocaleString()}\n\nYour transfer has been processed successfully.`,
          annotations: { audience: ['user'] },
        },
      ],
    };
  },
};

/**
 * Available Accounts Resource
 * Provides a list of accounts the customer can transfer money between
 */
export const availableAccountsResource = {
  uri: 'banking://accounts/available',
  name: 'Available Accounts',
  description:
    'List of accounts you can transfer money between, including account IDs, names, types, and transfer capabilities',
  mimeType: 'application/json',
  handler: async (
    args: {
      customerId: string;
    },
    extra: any,
  ) => {
    const accounts = PersonalBankingService.getAccounts(args.customerId);

    // Format accounts for display
    const accountList = accounts
      .map(acc => {
        const holder = acc.accountHolder ? ` (${acc.accountHolder})` : '';
        const transferFrom = acc.canTransferFrom ? '✓' : '✗';
        const transferTo = acc.canTransferTo ? '✓' : '✗';
        return `• ${acc.accountId} - ${acc.accountName}${holder}\n  Type: ${acc.accountType} | Transfer From: ${transferFrom} | Transfer To: ${transferTo}`;
      })
      .join('\n\n');

    return {
      contents: [
        {
          uri: 'banking://accounts/available',
          mimeType: 'application/json',
          text: `Available Accounts for Transfers:\n\n${accountList}\n\nNote: Use these account IDs when transferring money.`,
        },
      ],
      structuredContent: accounts,
    };
  },
};

/**
 * Get all personal banking tools
 */
export const personalBankingTools = [
  getAccountBalanceTool,
  getAccountStatementTool,
  prepareTransferTool,
  confirmOrCancelTransferTool,
];

/**
 * Get all personal banking resources
 */
export const personalBankingResources = [availableAccountsResource];
