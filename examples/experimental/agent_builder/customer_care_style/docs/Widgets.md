# Widget Pattern

## Overview

The Widget Pattern demonstrates how to create rich, interactive user experiences that automatically adapt to different channels (web, mobile, voice) while simultaneously delivering significant performance optimizations. By using IBM Orchestrate's widget system, you can define interaction patterns once and have them intelligently rendered based on client capabilities—a date picker becomes a visual calendar on web/mobile but prompts for spoken input on voice channels, while numeric inputs can use DTMF on phone systems.

This pattern solves two critical challenges in customer care:

1. **Rich User Experiences**: Provides structured, intuitive interactions beyond free-form text (date pickers, account selectors, confirmation dialogs)
2. **Performance Optimization**: Eliminates unnecessary LLM calls by bypassing the model when presenting options and processing selections

The pattern leverages IBM Orchestrate's widget system, which follows the [MCP Apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/draft/apps.mdx). See [Widget Types Reference](./reference/WidgetTypes.md) for a complete list of supported widget types.

## Problems This Pattern Solves

### **Delivering Rich, Channel-Adapted Interactions**

Text-based question-and-answer interactions are often insufficient for optimal user experiences. Many customer interactions require structured input:

- Selecting dates for appointments or scheduled transactions
- Choosing from predefined options (accounts, products, services)
- Entering numeric values (amounts, quantities, PINs)
- Confirming transactions with explicit approval dialogs
- Interacting with domain-specific interfaces (seat selectors, floor plans)

**The Widget Pattern provides:**

- **Structured inputs** that guide users through complex workflows
- **Automatic channel adaptation** - the same widget definition renders optimally across web, mobile, and voice
- **Intuitive interfaces** - visual calendars on screens, spoken prompts on voice channels, DTMF for numeric entry
- **Consistent experiences** - define once, deploy everywhere

**Channel adaptation examples:**

- **Date Picker**: Visual calendar on web/mobile → Spoken date prompt on voice
- **Account Selector**: Dropdown list on web/mobile → Spoken menu with DTMF options on voice
- **Confirmation Dialog**: Button clicks on web/mobile → "Say yes to confirm or no to cancel" on voice
- **Numeric Input**: Text field on web/mobile → DTMF entry or speech recognition on voice

### **Eliminating Unnecessary LLM Processing**

In traditional conversational flows, every user interaction requires two LLM calls:

1. **Outbound**: The LLM processes the tool response and generates a natural language presentation
2. **Inbound**: The LLM interprets the user's selection and determines which tool to call next

For structured interactions where users are selecting from predefined options, these LLM calls add latency without providing value. The user is simply choosing an option—no natural language understanding is needed.

**Traditional flow:**

- User input → LLM interpretation → Tool call → Tool response → LLM formatting → User
- **Requires two LLM calls per interaction**

**Widget flow:**

- User input → Tool call → Tool response → User
- **Requires zero LLM calls per interaction**

**Performance impact:**

- **Voice channels**: Eliminates pauses that make customers think the call has dropped
- **Multi-step workflows**: A 4-step workflow saves 8 LLM calls (4 steps × 2 calls per step)
- **High-volume interactions**: Cumulative savings across thousands of daily interactions

### **Graceful Fallback to Natural Language**

A critical feature is that **users are never forced to use structured inputs**. They can always respond with natural language, and the system gracefully falls back to LLM processing when simple matchers fail.

**Examples:**

```typescript
// Date picker shown, but user types natural language
Widget: "When do you want to transfer?"
User: "tomorrow"
System: Falls back to LLM → Interprets "tomorrow" → Calls tool with date

// Account picker shown, but user describes the account
Widget: "Select account to transfer from:"
User: "my son's account"
System: Falls back to LLM → Looks up account → Calls tool with account ID
```

This provides the best of both worlds:

- **Maximum performance** when users follow structured prompts
- **Maximum flexibility** when users prefer natural language
- **No user training required** - the system adapts to user preferences

## Implementation Walkthrough

Below we walk through the money transfer implementation that demonstrates this pattern across multiple steps, showing both the rich interaction design and performance optimization.

**Note:** The business logic for personal banking operations is in [`src/personalBankingService.ts`](../src/personalBankingService.ts). The tool definitions in [`src/personalBanking.ts`](../src/personalBanking.ts) focus on the MCP interface while delegating business logic to the service layer.

### Widget Definition Structure

Widgets are returned in the tool response's `_meta` field:

**Tool Definition:** [`src/personalBanking.ts`](../src/personalBanking.ts)
**Business Logic:** [`src/personalBankingService.ts`](../src/personalBankingService.ts)

```typescript
// In the tool handler (src/personalBanking.ts)
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
      type: 'options_selector',
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

  // Additional steps follow the same pattern...
  // Final step: Store transaction in local variables and show confirmation
};
```

**How this works across channels:**

1. **Web/Mobile**: Renders as a dropdown or list with clickable options showing account names and descriptions
2. **Voice**: Reads the title and description, then presents options as a spoken menu (e.g., "Press 1 for Personal Checking, Press 2 for Savings Account")
3. **Selection Processing**: When user selects (click, DTMF, or speech), the system matches against provided options and calls the tool directly—no LLM needed

### Multi-Step Workflow Example

The money transfer flow demonstrates the pattern across multiple sequential steps, leveraging local variable storage for the confirmation step:

```typescript
// Step 1: Select source account
if (!args.fromAccountId) {
  return { _meta: { 'com.ibm.orchestrate/widget': fromAccountPicker } };
}

// Step 2: Select destination account
if (!args.toAccountId) {
  // Filter accounts that can receive transfers AND exclude the fromAccountId
  const toAccounts = allAccounts.filter(
    acc => acc.canTransferTo && acc.accountId !== args.fromAccountId,
  );
  return { _meta: { 'com.ibm.orchestrate/widget': toAccountPicker } };
}

// Step 3: Select transfer date
if (!args.scheduledDate) {
  const datePickerWidget = {
    type: 'datetime',
    collection_type: 'date',
    title: 'Select Transfer Date',
    description: 'Choose when you want the transfer to occur:',
    min_date: minDate.toISOString().split('T')[0],
    max_date: maxDate.toISOString().split('T')[0],
    on_event: {
      tool: 'prepare_money_transfer',
      parameters: { ...args },
      map_input_to: 'scheduledDate',
    },
  };
  return { _meta: { 'com.ibm.orchestrate/widget': datePickerWidget } };
}

// Step 4: All info collected - validate and store in local store
const { fromAccount, toAccount } = PersonalBankingService.validateTransfer(
  args.customerId,
  args.fromAccountId,
  args.toAccountId,
  args.amount,
);

const transactionId = `TXN-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;

// Store transaction in LOCAL STORE (Layer 3)
// This enables the two-step confirmation pattern while maintaining
// encapsulation - the transaction data is isolated to this MCP server
if (threadId) {
  setLocalVariable(threadId, `transaction_${transactionId}`, {
    transactionId,
    customerId: args.customerId,
    fromAccountId: args.fromAccountId,
    fromAccountName: fromAccount.accountName,
    toAccountId: args.toAccountId,
    toAccountName: toAccount.accountName,
    amount: args.amount,
    scheduledDate: args.scheduledDate,
    memo: args.memo,
    createdAt: new Date().toISOString(),
  });
}

// Step 5: Show confirmation widget
const confirmationWidget = {
  type: 'confirmation',
  confirmation_text: 'Please review the transfer details below:',
  description: 'Additional context or instructions',
  confirmation_details: {
    label: 'Confirm',
    value: 'confirm'
  },
  cancelation_details: {
    label: 'Cancel',
    value: 'cancel'
  },
  on_event: {
    tool: 'confirm_or_cancel_money_transfer',
    parameters: { transactionId },
    map_input_to: 'action'
  },
};
return { _meta: { 'com.ibm.orchestrate/widget': confirmationWidget } };
```

**Local Store Enables the Transaction Pattern:**

The widget pattern works seamlessly with local store to enable secure two-step transactions:

1. **Prepare step** collects all required information through widgets, then stores transaction details in local store
2. **Confirm/cancel step** retrieves transaction details from local store, verifies ownership, and processes or cancels

This combination provides both excellent UX (through widgets) and security (through local store isolation per MCP server). See [Transactions.md](Transactions.md) and [Passing Context to Tools](PassingContextToTools.md) for more details.

**User experience across channels:**

**Web/Mobile:**

1. Dropdown to select source account
2. Dropdown to select destination account (filtered to exclude source)
3. Visual calendar to pick date
4. Confirmation dialog with Confirm/Cancel buttons

**Voice:**

1. "Select account to transfer from. Press 1 for Personal Checking, Press 2 for Savings..."
2. "Select account to transfer to. Press 1 for..."
3. "When do you want to transfer? You can say a date or press 1 for tomorrow, 2 for next week..."
4. "Please confirm: Transfer $100 from Personal Checking to Savings on January 15th. Say yes to confirm or no to cancel."

**Performance impact:**

- **Traditional flow**: 4 steps × 2 LLM calls per step = 8 LLM calls total
- **Widget flow**: 4 steps × 0 LLM calls per step = 0 LLM calls total
- **Total savings**: 8 LLM calls eliminated per transaction

### Important Implementation Details

**Filtering Options Between Steps:**

When implementing multi-step workflows, ensure each step filters options appropriately:

```typescript
// Step 1: Filter accounts that can transfer from AND exclude toAccountId if already selected
const fromAccounts = allAccounts.filter(
  acc => acc.canTransferFrom && acc.accountId !== args.toAccountId,
);

// Step 2: Filter accounts that can receive transfers AND exclude the fromAccountId
const toAccounts = allAccounts.filter(
  acc => acc.canTransferTo && acc.accountId !== args.fromAccountId,
);
```

This prevents users from selecting the same account as both source and destination, and ensures the UI only shows valid options at each step.

## Custom Widgets

While this documentation focuses on IBM Orchestrate's built-in widgets (date pickers, account selectors, confirmation dialogs, etc.), the platform also supports **customer-supplied custom widgets** for domain-specific interactions.

**Examples of custom widgets:**

- **Seat selectors** for airlines or theaters
- **Floor plan pickers** for real estate or office space
- **Product configurators** with visual customization options
- **Interactive maps** for location selection
- **Calendar views** with availability indicators

Custom widgets can be seamlessly combined with IBM's out-of-the-box widgets in a single interaction flow. For example, an airline booking flow might use:

1. Built-in date picker for travel dates
2. Built-in dropdown for number of passengers
3. Custom seat selector widget for choosing seats
4. Built-in confirmation dialog for final approval

To support this, we have extended the MCP Apps specification with [multiple widget support per tool](specChanges/MultipleWidgetsPerTool.md). This extension allows tools to return multiple widget definitions, enabling rich, multi-step interactions that combine standard and custom widgets. This proposal is tracked as [issue #191](https://github.com/modelcontextprotocol/ext-apps/issues/191).

**Note:** This sample implementation demonstrates IBM's built-in widgets. Custom widget implementation is supported but not included in this sample.

## Key Takeaways

The Widget Pattern provides dual benefits for customer care applications:

**Rich User Experiences:**

- **Channel-adapted interfaces**: Same definition renders optimally on web, mobile, and voice
- **Intuitive interactions**: Visual controls on screens, spoken prompts on voice, DTMF for numeric entry
- **Structured workflows**: Guide users through complex multi-step processes
- **Consistent experiences**: Define once, deploy everywhere

**Performance Optimization:**

- **Eliminates LLM calls**: Zero LLM processing for widget presentation and selection processing
- **Essential for voice**: Delivers near real-time responsiveness customers expect
- **Scales with complexity**: Savings multiply with each step in multi-step workflows
- **Graceful fallback**: Users can always use natural language when preferred

**When to use this pattern:**

- Multi-step wizards with sequential selections (account pickers, date pickers)
- Confirmation dialogs requiring explicit user approval
- Any interaction where users choose from predefined options
- Voice channels where latency and intuitive prompts are critical
- High-volume interactions where cumulative performance matters

**Perfect use cases:**

- Account transfers with source/destination selection
- Appointment scheduling with date/time pickers
- Product selection from catalogs
- Form filling with dropdown selections
- Transaction confirmations
- Any structured data entry workflow

## When to Use Widgets vs. Free-Form Conversation

Widgets excel at task-oriented interactions where users need to make selections, enter structured data, or confirm actions. They provide the fastest, most intuitive experience for:

- Selecting from known options (accounts, dates, products)
- Multi-step workflows with sequential decisions
- Transactions requiring explicit confirmation
- Data entry with validation requirements

Free-form conversation remains valuable for:

- Exploratory questions where the user doesn't know what they're looking for
- Complex problem-solving requiring back-and-forth dialogue
- Situations where the user needs to explain context or nuances

The Widget Pattern is essential for customer care applications where both user experience and response time directly impact customer satisfaction. By providing rich, channel-adapted interactions while eliminating unnecessary LLM processing, this pattern transforms task-oriented workflows from frustratingly slow and awkward to satisfyingly responsive and intuitive.
