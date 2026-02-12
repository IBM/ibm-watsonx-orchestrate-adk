/**
 * Mortgage Tools Module
 *
 * Contains tool definitions for mortgage operations
 */

import { z } from 'zod';
import { MortgageService } from './mortgageService';
import {
  deleteLocalVariable,
  getLocalVariable,
  setLocalVariable,
} from './localStore';

/**
 * Get mortgage balance tool definition
 *
 * This is a TOOL RESPONSE TO USER example that bypasses the LLM entirely,
 * eliminating hallucination risk for critical data. The response
 * goes directly to the user, ensuring exact balance amounts and regulatory
 * compliance while reducing latency.
 */
export const getMortgageBalanceTool = {
  name: 'get_mortgage_balance',
  config: {
    title: 'Get Mortgage Outstanding Balance',
    description:
      'Retrieve current outstanding mortgage balance for the authenticated customer. Response bypasses LLM to ensure data accuracy.',
    inputSchema: {},
    outputSchema: {
      loanNumber: z.string(),
      originalAmount: z.number(),
      outstandingBalance: z.number(),
      interestRate: z.number(),
      monthlyPayment: z.number(),
      nextPaymentDate: z.string(),
      remainingTermMonths: z.number(),
    },
  },
  handler: async ({ customerId }: { customerId: string }, extra: any) => {
    const output = MortgageService.getMortgageBalance(customerId);

    return {
      content: [
        {
          type: 'text',
          text: `Your current mortgage balance and details are displayed below:\nLoan Number: ${output.loanNumber}\nOriginal Amount: $${output.originalAmount.toLocaleString()}\nOutstanding Balance: $${output.outstandingBalance.toLocaleString()}\nInterest Rate: ${output.interestRate}%\nMonthly Payment: $${output.monthlyPayment.toFixed(2)}\nNext Payment Due: ${output.nextPaymentDate}\nRemaining Term: ${output.remainingTermMonths} months (${Math.floor(output.remainingTermMonths / 12)} years)`,
          annotations: { audience: ['user'] },
        },
      ],
    };
  },
};

/**
 * Get mortgage payments tool definition
 *
 * This is a HYBRID RESPONSE example that demonstrates how to have the model
 * formulate part of the response while ensuring critical data comes directly
 * from your code. This provides natural interaction while preventing the model
 * from hallucinating incorrect payment data.
 *
 * The tool uses the audience annotation to:
 * - Send context to the model (annotations: { audience: ['assistant'] }) about what data is available
 * - Send formatted payment data directly to the user (annotations: { audience: ['user'] }) as a markdown table
 */
export const getMortgagePaymentsTool = {
  name: 'get_mortgage_payments',
  config: {
    title: 'Get Recent Mortgage Payments',
    description:
      'Retrieve recent mortgage payment history for the authenticated customer.',
    inputSchema: {
      count: z
        .number()
        .optional()
        .describe('Number of recent payments to retrieve (default: 6)'),
    },
    outputSchema: {
      customerId: z.string(),
      loanNumber: z.string(),
      payments: z.array(
        z.object({
          paymentDate: z.string(),
          amount: z.number(),
          principal: z.number(),
          interest: z.number(),
          escrow: z.number(),
          balanceAfter: z.number(),
        }),
      ),
    },
  },
  handler: async (
    {
      customerId,
      count = 6,
    }: {
      customerId: string;
      count?: number;
    },
    extra: any,
  ) => {
    const output = MortgageService.getMortgagePayments(customerId, count);

    // Create markdown table for user display
    const markdownTable = [
      '| Payment Date | Total Amount | Principal | Interest | Escrow | Balance After |',
      '|--------------|--------------|-----------|----------|--------|---------------|',
      ...output.payments.map(
        p =>
          `| ${p.paymentDate} | $${p.amount.toFixed(2)} | $${p.principal.toFixed(2)} | $${p.interest.toFixed(2)} | $${p.escrow.toFixed(2)} | $${p.balanceAfter.toLocaleString()} |`,
      ),
    ].join('\n');

    return {
      content: [
        {
          type: 'text',
          text: `The last ${count} months of mortgage payment data has been retrieved and will be displayed to the user in a table format immediately following your response.`,
          annotations: { audience: ['assistant'] },
        },
        {
          type: 'text',
          text: `**Recent Mortgage Payments**\n\n**Loan Number:** ${output.loanNumber}\n\n${markdownTable}`,
          annotations: { audience: ['user'] },
        },
      ],
      structuredContent: output,
    };
  },
};

/**
 * Prepare mortgage payment tool definition
 *
 * This is the FIRST STEP in a two-step transaction pattern.
 * It prepares a payment and returns a structured confirmation dialog that
 * presents the user with payment details and two action buttons:
 * - Confirm: Calls confirm_or_cancel_mortgage_payment with action='confirm'
 * - Cancel: Calls confirm_or_cancel_mortgage_payment with action='cancel'
 *
 * The confirmation dialog uses IBM Orchestrate's built-in widget
 * (ui://ibm.com/orchestrate/widget) to display payment details
 * and capture explicit user intent. This ensures financial transactions
 * require direct user interaction and cannot be automatically confirmed by the model.
 *
 * The widget handles calling confirm_or_cancel_mortgage_payment with the
 * appropriate action based on which button the user clicks, completing
 * the two-step confirmation flow.
 */
export const prepareMortgagePaymentTool = {
  name: 'prepare_mortgage_payment',
  config: {
    title: 'Prepare Mortgage Payment',
    description:
      'Prepare a mortgage payment for the authenticated customer. Amount must be less than $10,000. Payment date must be in the future but not more than 30 days out.',
    inputSchema: {
      amount: z
        .number()
        .positive()
        .max(10000, 'Payment amount must be less than $10,000')
        .describe('Payment amount in dollars (required, max $10,000)'),
      paymentDate: z
        .string()
        .describe('Payment date in YYYY-MM-DD format (required)'),
    },
    outputSchema: {
      transactionId: z.string(),
      loanNumber: z.string(),
      amount: z.number(),
      paymentDate: z.string(),
      currentBalance: z.number(),
      expiresAt: z.string(),
    },
  },
  _meta: {
    ui: {
      // Reference IBM Orchestrate's built-in confirmation widget
      // This widget will display the payment details and allow the user
      // to explicitly confirm or cancel the transaction
      resourceUri: 'ui://ibm.com/orchestrate/widget',
    },
  },
  handler: async (args: any, extra: any) => {
    const { customerId, amount, paymentDate } = args;
    const threadId =
      extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;

    if (!threadId) {
      throw new Error('Thread ID is required');
    }
    /**
     * Validation errors are sent directly to the user (annotations: { audience: ['user'] })
     * without involving the model. This approach:
     * - Improves performance by avoiding unnecessary LLM processing
     * - Reduces latency for simple validation feedback
     * - Saves tokens/costs
     * - Provides immediate, consistent error messages
     *
     * The model's natural language doesn't add value for straightforward
     * validation errors, so we bypass it entirely.
     */

    // Validate payment date
    const validation = MortgageService.validatePaymentDate(paymentDate);
    if (!validation.isValid) {
      // Note: No structuredContent is returned, so the UI widget will NOT be rendered.
      // This ensures validation errors are handled quickly without launching the widget.
      return {
        content: [
          {
            type: 'text',
            text: validation.errorMessage,
            annotations: { audience: ['user'] },
          },
        ],
        isError: true,
      };
    }

    const preparedPayment = MortgageService.preparePayment(
      customerId,
      amount,
      paymentDate,
    );

    // Store payment details in LOCAL STORE
    // This is transient data specific to this MCP server within the thread
    setLocalVariable(
      threadId,
      `payment_${preparedPayment.transactionId}`,
      preparedPayment,
    );

    // Confirmation widget definition - goes in _meta so model doesn't see it
    const confirmationWidget = {
      type: 'confirmation',
      title: 'Confirm Mortgage Payment',
      confirmation_text: `## Confirm Mortgage Payment\n\nPlease review the payment details below and confirm to proceed:\n\n**Payment Details:**\n- **Loan Number:** ${preparedPayment.loanNumber}\n- **Amount:** $${preparedPayment.amount.toFixed(2)}\n- **Payment Date:** ${preparedPayment.paymentDate}\n- **Current Balance:** $${preparedPayment.currentBalance.toLocaleString()}\n\n**Transaction ID:** ${preparedPayment.transactionId}\n\n⚠️ This transaction will expire in 5 minutes at ${new Date(preparedPayment.expiresAt).toLocaleString()}`,
      on_confirm: {
        tool: 'confirm_or_cancel_mortgage_payment',
        parameters: {
          transactionId: preparedPayment.transactionId,
          action: 'confirm',
        },
      },
      on_cancel: {
        tool: 'confirm_or_cancel_mortgage_payment',
        parameters: {
          transactionId: preparedPayment.transactionId,
          action: 'cancel',
        },
      },
    };

    return {
      // Note: When using Orchestrate widgets, a content block is not necessary.
      // IBM Orchestrate automatically exposes the necessary information to the model
      // (e.g., that a confirmation dialog is being shown) without requiring explicit
      // content with annotations: { audience: ['assistant'] }.
      _meta: {
        'com.ibm.orchestrate/widget': confirmationWidget,
      },
    };
  },
};

/**
 * Confirm or cancel mortgage payment tool definition
 *
 * This is the SECOND STEP in a two-step transaction pattern.
 * It handles user actions (confirm or cancel) for a previously prepared payment.
 * This demonstrates explicit user confirmation for financial transactions.
 *
 * IMPORTANT: This tool is hidden from the model (visibility: ["app"]) to ensure
 * that only the user can explicitly confirm or cancel payments through the UI widget.
 * The model should never be able to automatically confirm financial transactions
 * without direct user interaction. This provides an additional security layer
 * and ensures regulatory compliance for payment confirmations.
 */
export const confirmOrCancelMortgagePaymentTool = {
  name: 'confirm_or_cancel_mortgage_payment',
  config: {
    title: 'Confirm or Cancel Mortgage Payment',
    description:
      'Handle user action (confirm or cancel) for a previously prepared mortgage payment using the transaction ID.',
    inputSchema: {
      transactionId: z
        .string()
        .describe('Transaction ID from prepare_mortgage_payment'),
      action: z
        .enum(['confirm', 'cancel'])
        .describe('User action: confirm to process payment, cancel to abort'),
    },
    // No outputSchema - this tool returns user-facing messages, not structured data
    _meta: {
      ui: {
        visibility: ['app'], // 🔒 Hidden from model - only callable by UI widget for explicit user confirmation
      },
    },
  },
  handler: async (args: any, extra: any) => {
    const { customerId, transactionId, action } = args;
    const threadId =
      extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;

    if (!threadId) {
      throw new Error('Thread ID is required');
    }

    // Retrieve payment from LOCAL STORE
    const payment = getLocalVariable(threadId, `payment_${transactionId}`);

    if (!payment) {
      throw new Error(
        `Payment ${transactionId} not found. It may have expired or been processed already.`,
      );
    }

    // Verify payment belongs to this customer (security check)
    if (payment.customerId !== customerId) {
      throw new Error('Payment does not belong to this customer');
    }

    // Clean up local variable (payment is being processed or cancelled)
    deleteLocalVariable(threadId, `payment_${transactionId}`);

    if (action === 'cancel') {
      // Handle cancellation
      return {
        content: [
          {
            type: 'text',
            text: `Payment Cancelled\n\nTransaction ID: ${transactionId}\n\nThe mortgage payment has been cancelled and no charges were processed.\n\nPayment Details:\n- Loan Number: ${payment.loanNumber}\n- Amount: $${payment.amount.toFixed(2)}\n- Payment Date: ${payment.paymentDate}`,
            annotations: { audience: ['user'] },
          },
          {
            type: 'text',
            text: `The mortgage payment with transaction ID ${transactionId} has been cancelled by the user.`,
            annotations: { audience: ['assistant'] },
          },
        ],
      };
    }

    // Handle confirmation - process the actual payment
    const confirmationNumber = MortgageService.processMortgagePayment(
      payment.customerId,
      payment.loanNumber,
      payment.amount,
      payment.paymentDate,
    );
    const confirmedAt = new Date().toISOString();

    return {
      content: [
        {
          type: 'text',
          text: `✅ Payment Confirmed Successfully!\n\nConfirmation Number: ${confirmationNumber}\nTransaction ID: ${transactionId}\n\nPayment Details:\n- Loan Number: ${payment.loanNumber}\n- Amount Paid: $${payment.amount.toFixed(2)}\n- Payment Date: ${payment.paymentDate}\n- Confirmed At: ${new Date(confirmedAt).toLocaleString()}\n\nYour payment has been processed and your mortgage balance has been updated.`,
          annotations: { audience: ['user'] },
        },
        {
          type: 'text',
          text: `The mortgage payment has been confirmed with confirmation number ${confirmationNumber}. The payment has been processed successfully.`,
          annotations: { audience: ['assistant'] },
        },
      ],
    };
  },
};

/**
 * Get all mortgage tools
 */
export const mortgageTools = [
  getMortgageBalanceTool,
  getMortgagePaymentsTool,
  prepareMortgagePaymentTool,
  confirmOrCancelMortgagePaymentTool,
];
