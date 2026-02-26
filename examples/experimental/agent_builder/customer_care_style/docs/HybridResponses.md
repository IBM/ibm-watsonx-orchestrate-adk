# Hybrid Responses

## Overview

This pattern demonstrates how MCP tools can return hybrid responses that combine natural language generation from the LLM with guaranteed accurate data from your code. The tool uses the audience annotation to send different content to the model versus the user, providing a more natural conversational experience while eliminating hallucination risk for critical data.

## Problems This Pattern Solves

### **Natural Interaction with Data Accuracy Guarantees**

The "Tool Responses to Users" pattern eliminates hallucination risk by bypassing the LLM entirely, but this can make interactions feel robotic since responses are pre-formatted. The Hybrid Response pattern provides the best of both worlds:

- The LLM generates natural, conversational responses that feel human
- Critical data comes directly from your code with zero hallucination risk
- The user experience feels more engaging and less mechanical

For example, when a customer asks "Show me my recent mortgage payments," the model can provide a natural introduction and context, while the actual payment data (amounts, dates, balances) is guaranteed to be accurate because it comes directly from your tool.

### **Optimized Performance for Complex Queries**

Hybrid responses offer a performance sweet spot:

- **Faster than full LLM processing**: By sending formatted data directly to the user, you avoid the token processing time required for the LLM to parse and reformat large datasets
- **Slightly slower than direct responses**: There is still an LLM call to generate the conversational wrapper, but this is minimal compared to processing the full dataset
- **Ideal for data-heavy responses**: When returning tables, lists, or structured data, the LLM only needs to generate a brief introduction rather than processing hundreds or thousands of tokens

This is particularly valuable for voice channels where latency matters, but you still want to maintain a natural conversational flow.

### **Safe Handling of Calculation Requests**

One of the most powerful use cases for hybrid responses is handling requests that involve calculations or data analysis. Consider the question: "How much have I paid in total over the last 6 months?"

Without proper safeguards, the LLM might attempt to:

- Sum up payment amounts (risking calculation errors)
- Filter data incorrectly
- Provide an answer with false confidence

The Hybrid Response pattern solves this by:

1. **Prompting the model to politely decline calculations**: The model is instructed to explain that it cannot perform calculations to ensure accuracy
2. **Providing the necessary data**: The tool returns all the relevant data in a clear, structured format (e.g., a table)
3. **Empowering the user**: The customer can see all the data they need to make the calculation themselves or use their own tools

This approach maintains trust by being transparent about limitations while still being helpful by providing the exact data needed.

## Implementation Walkthrough

Below we walk through the mortgage payments tool that demonstrates this pattern.

**Note:** The business logic for mortgage operations is in [`src/mortgageService.ts`](../src/mortgageService.ts). The tool definitions in [`src/mortgage.ts`](../src/mortgage.ts) focus on the MCP interface while delegating business logic to the service layer.

### Hybrid Response Structure with Audience Targeting

The key to hybrid responses is using the `audience` field within `annotations` to send different content to different recipients:

**Tool Definition:** [`src/mortgage.ts`](../src/mortgage.ts)
**Business Logic:** [`src/mortgageService.ts`](../src/mortgageService.ts)

```typescript
// In the tool handler (src/mortgage.ts)
handler: async ({
  customerId,
  count = 6,
}: {
  customerId: string;
  count?: number;
}) => {
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
};
```

**How it works:**

1. **Model Context** (`annotations: { audience: ['assistant'] }`): Informs the LLM that payment data has been retrieved and will be displayed. This allows the model to:
   - Acknowledge the data in its response
   - Provide helpful context or guidance
   - Politely decline to perform calculations while explaining the data is available

2. **User Data** (`annotations: { audience: ['user'] }`): Sends the formatted markdown table directly to the user, ensuring:
   - Payment amounts are exactly as returned from your system
   - Dates and balances cannot be hallucinated or misinterpreted
   - The data is presented in a clear, structured format

### Example Interaction

**User:** "How much have I paid in total over the last 6 months?"

**Model Response:** "I can see your payment history for the last 6 months. To ensure accuracy, I won't calculate the total myself, but I've displayed all your payments in the table below."

**Data Displayed to User:**
| Payment Date | Total Amount | Principal | Interest | Escrow | Balance After |
|--------------|--------------|-----------|----------|--------|---------------|
| 2025-12-01 | $1,620.50 | $722.15 | $898.35 | $0.00 | $287,450.32 |
| 2025-11-01 | $1,620.50 | $719.88 | $900.62 | $0.00 | $288,172.47 |
| ... | ... | ... | ... | ... | ... |

## Key Takeaways

The Hybrid Response pattern provides an optimal balance for many customer care scenarios:

- **Natural conversational flow**: The LLM generates contextual, human-like responses that feel engaging
- **Zero hallucination risk for data**: Critical information comes directly from your code with guaranteed accuracy
- **Performance optimization**: Faster than full LLM processing of large datasets, while maintaining conversational quality
- **Safe calculation handling**: Model politely declines calculations while providing users the data they need
- **Regulatory compliance**: Ensures required data is displayed exactly as specified, while allowing natural language context

**When to use this pattern:**

- Displaying structured data (tables, lists) where accuracy is critical
- Responding to requests that might involve calculations or data analysis
- Balancing natural interaction with data accuracy requirements
- Optimizing performance for data-heavy responses

## Trade-offs

While this pattern provides an excellent balance, there are important trade-offs to consider:

1. **Slightly slower than direct responses**: The pattern is slightly slower than the direct "Tool Responses to Users" pattern due to the LLM call needed to generate the conversational wrapper around the data.

2. **Limited cross-tool reasoning**: When data is sent with `annotations: { audience: ['user'] }`, the model does not see that output. This limits its ability to reason across multiple tool outputs. For example, if a user asks "Did I spend more last month than my current balance?", the model cannot compare data from different tools—it can only display the outputs to the user.

   This limitation is actually a feature for accuracy: even if the model could see the data, allowing it to perform comparisons or calculations introduces risk of errors. By keeping the model from seeing user-targeted data, we prevent it from making potentially incorrect inferences. The user can see all the data they need to make their own informed decisions.

The Hybrid Response pattern is ideal when you need the engagement of natural conversation combined with the accuracy guarantees that businesses require for critical data.
