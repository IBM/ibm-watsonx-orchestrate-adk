/**
 * Credit Card Tools Module
 *
 * Contains tool definitions for credit card operations
 */

import { z } from 'zod';
import { CreditCardService } from './creditCardService';

/**
 * Localized message templates for credit card balance display
 * Templates use {variable} placeholders that get replaced with actual values
 */
const messageTemplates: Record<string, string> = {
  'en-US': `Credit Card Balance:
Card: {cardNumber} ({cardType})
Current Balance: {currentBalance}
Available Credit: {availableCredit}
Credit Limit: {creditLimit}
Minimum Payment: {minimumPayment}
Payment Due: {paymentDueDate}`,

  'es-MX': `Saldo de Tarjeta de Crédito:
Tarjeta: {cardNumber} ({cardType})
Saldo Actual: {currentBalance}
Crédito Disponible: {availableCredit}
Límite de Crédito: {creditLimit}
Pago Mínimo: {minimumPayment}
Fecha de Pago: {paymentDueDate}`,

  'fr-FR': `Solde de Carte de Crédit:
Carte: {cardNumber} ({cardType})
Solde Actuel: {currentBalance}
Crédit Disponible: {availableCredit}
Limite de Crédit: {creditLimit}
Paiement Minimum: {minimumPayment}
Date d'Échéance: {paymentDueDate}`,

  'de-DE': `Kreditkartensaldo:
Karte: {cardNumber} ({cardType})
Aktueller Saldo: {currentBalance}
Verfügbares Guthaben: {availableCredit}
Kreditlimit: {creditLimit}
Mindestzahlung: {minimumPayment}
Fälligkeitsdatum: {paymentDueDate}`,
};

/**
 * Get credit card balance tool definition
 *
 * This tool demonstrates:
 * 1. Using JWT token from CONTEXT VARIABLES (customer-provided via API)
 * 2. Using locale from SYSTEM CONTEXT (provided by Watson Orchestrate)
 */
export const getCreditCardBalanceTool = {
  name: 'get_credit_card_balance',
  config: {
    title: 'Get Credit Card Balance',
    description:
      'Retrieve current credit card balance and details for the authenticated customer',
    inputSchema: {},
    // outputSchema: {
    //   cardNumber: z.string(),
    //   cardType: z.string(),
    //   currentBalance: z.number(),
    //   availableCredit: z.number(),
    //   creditLimit: z.number(),
    //   minimumPayment: z.number(),
    //   paymentDueDate: z.string(),
    //   lastStatementDate: z.string(),
    //   lastStatementBalance: z.number(),
    // },
  },
  handler: async (args: any, extra: any) => {
    // Extract JWT token from CONTEXT VARIABLES (passed by API caller)
    const jwtToken = extra?._meta?.['com.ibm.orchestrate/context']?.jwtToken;

    if (!jwtToken) {
      throw new Error(
        'JWT token is required. It must be provided in context variables by the API caller.',
      );
    }

    // Use JWT token to authenticate with backend service
    const cardBalance = CreditCardService.getCreditCardBalance(jwtToken);

    // Extract locale from SYSTEM CONTEXT with fallback to en-US
    const locale =
      extra?._meta?.['com.ibm.orchestrate/systemcontext']?.locale || 'en-US';

    // Get message template for locale, fallback to en-US if locale not supported
    const template = messageTemplates[locale] || messageTemplates['en-US'];

    // Fill in template with actual values
    const message = template
      .replace('{cardNumber}', cardBalance.cardNumber)
      .replace('{cardType}', cardBalance.cardType)
      .replace('{currentBalance}', `$${cardBalance.currentBalance.toFixed(2)}`)
      .replace(
        '{availableCredit}',
        `$${cardBalance.availableCredit.toFixed(2)}`,
      )
      .replace('{creditLimit}', `$${cardBalance.creditLimit.toFixed(2)}`)
      .replace('{minimumPayment}', `$${cardBalance.minimumPayment.toFixed(2)}`)
      .replace('{paymentDueDate}', cardBalance.paymentDueDate);

    return {
      content: [
        {
          type: 'text' as const,
          text: message,
          annotations: { audience: ['user'] },
        },
      ],
    };
  },
};

/**
 * Export all credit card tools
 */
export const creditCardTools = [getCreditCardBalanceTool];
