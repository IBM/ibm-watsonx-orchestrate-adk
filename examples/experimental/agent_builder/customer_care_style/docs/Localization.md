# Localization

## Overview

Watson Orchestrate provides built-in support for multi-lingual customer interactions. The platform automatically handles localization in most scenarios, but there are specific cases where your tools need to implement localization directly.

## When Localization is Automatic

**The model automatically localizes content that passes through it.** When your tool returns content that goes to the model (the default behavior), the model will translate and adapt that content to the user's language. This includes:

- Tool responses without `annotations.audience` field
- Content intended for the assistant to process and present
- Natural language descriptions and explanations

In these cases, you don't need to implement localization in your tools—the model handles it automatically.

## When You Need to Implement Localization

**You must implement localization when sending content directly to users**, bypassing the model. This occurs in two scenarios:

### 1. User Audience Annotation

When using `annotations: { audience: ['user'] }` to send content directly to users (bypassing the LLM for accuracy or performance), you must localize the content yourself:

```typescript
return {
  content: [
    {
      type: 'text',
      text: 'Your localized message here',
      annotations: { audience: ['user'] }, // Bypasses model - you must localize
    },
  ],
};
```

### 2. Widget Content

When returning widgets (date pickers, account selectors, confirmation dialogs), all user-facing text must be localized:

```typescript
return {
  _meta: {
    'com.ibm.orchestrate/widget': {
      responseType: 'single-choice',
      title: 'Localized title', // Must be localized
      description: 'Localized text', // Must be localized
      options: [
        {
          label: 'Localized label', // Must be localized
          description: 'Localized', // Must be localized
        },
      ],
    },
  },
};
```

## Accessing User Locale

Watson Orchestrate provides the user's locale through system context variables. See [Context Variables](reference/Context.md) for complete details on how context variables are passed.

```typescript
handler: async ({
  customerId,
  _meta,
}: {
  customerId: string;
  _meta?: {
    'com.ibm.orchestrate/systemcontext'?: {
      locale?: string;
    };
  };
}) => {
  // Extract locale with fallback
  const locale =
    _meta?.['com.ibm.orchestrate/systemcontext']?.locale || 'en-US';

  // Use locale for localization
  // ...
};
```

The locale follows the BCP 47 format (e.g., `en-US`, `es-MX`, `fr-FR`, `de-DE`).

## Implementation Pattern: Template-Based Localization

The recommended approach is to use message templates with placeholders that get filled with actual values. This is the standard i18n pattern used across the industry.

### Example: Credit Card Balance Tool

See the complete implementation in:
- **TypeScript**: [`ts_server/src/creditCard.ts`](../toolkits/banking_mcp_server/ts_server/src/creditCard.ts)
- **Python**: [`py_server/src/credit_card.py`](../toolkits/banking_mcp_server/py_server/src/credit_card.py)

**Step 1: Define Message Templates**

Create templates for each supported locale with `{placeholder}` syntax:

```typescript
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
```

**Step 2: Get Locale and Select Template**

```typescript
// Extract locale from system context with fallback to en-US
const locale = _meta?.['com.ibm.orchestrate/systemcontext']?.locale || 'en-US';

// Get message template for locale, fallback to en-US if locale not supported
const template = messageTemplates[locale] || messageTemplates['en-US'];
```

**Step 3: Fill Template with Values**

```typescript
// Fill in template with actual values
const message = template
  .replace('{cardNumber}', cardBalance.cardNumber)
  .replace('{cardType}', cardBalance.cardType)
  .replace('{currentBalance}', `$${cardBalance.currentBalance.toFixed(2)}`)
  .replace('{availableCredit}', `$${cardBalance.availableCredit.toFixed(2)}`)
  .replace('{creditLimit}', `$${cardBalance.creditLimit.toFixed(2)}`)
  .replace('{minimumPayment}', `$${cardBalance.minimumPayment.toFixed(2)}`)
  .replace('{paymentDueDate}', cardBalance.paymentDueDate);
```

**Step 4: Return Localized Content**

```typescript
return {
  content: [
    {
      type: 'text' as const,
      text: message,
      annotations: { audience: ['user'] },
    },
  ],
};
```

## When to Localize vs. When to Let the Model Handle It

| Scenario                                | Who Localizes | Why                                                    |
| --------------------------------------- | ------------- | ------------------------------------------------------ |
| Tool response to model                  | Model         | Model automatically translates when presenting to user |
| Tool response with `annotations: { audience: ['user'] }` | Your tool     | Content bypasses model, goes directly to user          |
| Widget titles and labels                | Your tool     | Widgets render directly in UI, bypass model            |
| Widget option descriptions              | Your tool     | Displayed directly to user in UI                       |
| Error messages to model                 | Model         | Model can translate and contextualize errors           |
| Structured data (numbers, dates)        | Your tool     | Format according to locale conventions                 |

## Key Takeaways

- **Model handles most localization**: Content that passes through the model is automatically localized
- **You must localize direct-to-user content**: When using `annotations: { audience: ['user'] }` or widgets
- **Use template-based approach**: Define message templates with placeholders for each locale
- **Access locale from system context**: `_meta['com.ibm.orchestrate/systemcontext'].locale`
- **Always provide fallbacks**: e.g. Default to `en-US` if requested locale not supported

By following these patterns, your tools can provide seamless multi-lingual experiences that adapt to each user's language preference automatically.
