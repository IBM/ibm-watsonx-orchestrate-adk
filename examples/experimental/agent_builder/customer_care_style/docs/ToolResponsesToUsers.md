# Tool Responses to Users

## Overview

This pattern demonstrates how MCP tools can return responses that go directly to end users, bypassing the LLM entirely. This eliminates the risk of the LLM hallucinating, misinterpreting, or incorrectly transcribing critical information such as account balances, transaction details, or regulatory-required disclosures.

## Problems This Pattern Solves

### **Eliminating Hallucination Risk for Critical Data**

When a customer asks "What is my current bank balance?", the traditional flow sends the tool response to the LLM, which then generates a response to the user. While the risk may seem small, there is a non-zero chance that the LLM could:

- Incorrectly transcribe the balance amount
- Omit required regulatory information (e.g., in the UK, outstanding transactions MUST be displayed with balances)
- Format the response in a way that violates compliance requirements

In sensitive domains like financial services, healthcare, or legal services, even small transcription errors can result in significant liability. This pattern eliminates that risk by having the tool return a response that goes directly to the user, ensuring the exact information you provide is what the customer sees.

### **Improved Response Times**

When a tool provides a complete, user-ready response with `annotations: { audience: ['user'] }`, the LLM is bypassed entirely on the return path. This significantly reduces latency because:

- No LLM inference is required to format or rephrase the response
- The response goes directly from your tool to the user
- Token processing time is eliminated for the response generation

This is particularly valuable for voice channels where every millisecond of latency impacts the customer experience. For simple queries like "What's my balance?" or "When is my next payment due?", bypassing the LLM can reduce response time by hundreds of milliseconds or more.

## Implementation Walkthrough

Below we walk through a sample banking application that demonstrates this pattern. The sample shows how mortgage tools return user-targeted responses that bypass the LLM, while banking tools demonstrate a hybrid approach.

**Note:** The business logic for mortgage operations is in [`src/mortgageService.ts`](../src/mortgageService.ts). The tool definitions in [`src/mortgage.ts`](../src/mortgage.ts) focus on the MCP interface while delegating business logic to the service layer.

### Tool Response Structure with Audience Targeting

MCP tools can return responses with an `audience` field within the `annotations` object that specifies who should see the content. When `annotations: { audience: ['user'] }` is specified and no other content is available in the response, the content goes directly to the end user without passing through the LLM.

**User-Only Responses** - Content that bypasses the LLM and goes directly to users:

**Tool Definition:** [`src/mortgage.ts`](../src/mortgage.ts)
**Business Logic:** [`src/mortgageService.ts`](../src/mortgageService.ts)

```typescript
// In the tool handler (src/mortgage.ts)
handler: async ({ customerId }: { customerId: string }, extra: any) => {
  const output = MortgageService.getMortgageBalance(customerId);

  return {
    content: [
      {
        type: 'text',
        text: `Your current mortgage balance and details are displayed below:
Loan Number: ${output.loanNumber}
Original Amount: $${output.originalAmount.toLocaleString()}
Outstanding Balance: $${output.outstandingBalance.toLocaleString()}
Interest Rate: ${output.interestRate}%
Monthly Payment: $${output.monthlyPayment.toFixed(2)}
Next Payment Due: ${output.nextPaymentDate}
Remaining Term: ${output.remainingTermMonths} months (${Math.floor(output.remainingTermMonths / 12)} years)`,
        annotations: { audience: ['user'] },
      },
    ],
  };
};
```

## Key Takeaways

This sample demonstrates how the "Tool Responses to Users" pattern provides essential risk mitigation and performance benefits for customer care applications. The key advantages are:

- **Zero hallucination risk**: Responses bypass the LLM entirely, eliminating any possibility of transcription errors or incorrect information
- **Improved response times**: By skipping LLM processing on the return path, responses are delivered faster, which is critical for voice channels
- **Complete formatting control**: Your code determines the exact format and content shown to users, ensuring regulatory compliance
- **Liability protection**: Eliminates exposure from LLM-generated errors in sensitive financial or medical information

The pattern is essential for customer care applications in regulated industries where accuracy, compliance, and liability protection are paramount. Model instructions and hope are no way to run a business. This pattern provides the guarantees businesses need to feel confident in their agent's behavior.

## Trade-offs

While this pattern provides critical guarantees, there are important trade-offs to consider:

1. **Robotic feel**: Responses are pre-formatted rather than naturally generated, which can make interactions feel less conversational. The Hybrid Response pattern may feel less robotic while still providing the necessary guarantees and some latency benefits.

2. **Limited cross-tool reasoning**: When responses bypass the LLM with `annotations: { audience: ['user'] }`, the model does not see the output data. This limits its ability to reason across multiple tool outputs. For example, if a user asks "Did I spend more last month than my current balance?", the model cannot compare data from different tools—it can only display the outputs to the user.

   This limitation is actually a feature for accuracy: even if the model could see the data, allowing it to perform comparisons or calculations introduces risk of errors. By keeping the model from seeing user-targeted data, we prevent it from making potentially incorrect inferences. The user can see all the data they need to make their own informed decisions.
