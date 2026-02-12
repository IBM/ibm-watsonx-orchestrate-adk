# Widget Reference

This document provides a reference for the supported widget types in IBM watsonx Orchestrate. All widgets use the same component (`com.ibm.orchestrate/widget`) with different `type` values to trigger various interaction behaviors. Rendering these widgets is the responsibility of the user channel.

All widgets are interactive. This means that a widget provides details on how to collect data from the user and how to get that data back to the related tool. Each widget defines all the following:

- The tool that will handle the response from the wiget.
- Variable names to map input from the user to tool input variable names.
- Channel specific override information.

## Overview

The native widgets described in this document can be included with tool definition using the `_meta.ui.resourceUri`. Here is an example of what to add to your tool definition to take advantage of all the watsonx Orchestrate defined widget types:

```typescript
_meta: {
  ui: {
    resourceUri: "ui://com.ibm.orchestrate/widget",
  }
}
```

---

## Widget Schema

Widget has a `type` field which specifies the type of widget. There are a number of pre-existing types of widgets supported natively by the watsonx Orchestrate platform. These are defined below.

### Widget Metadata Interface

The `_meta` section of a tool result contains widget configuration using the `com.ibm.orchestrate/widget` key:

```typescript
interface Widget {
  'com.ibm.orchestrate/widget':
    | ConfirmationWidget
    | DatetimeWidget
    | NumberWidget
    | OptionsWidget
    | TextWidget;
}
```

---
## ConfirmationWidget

Provides a way for the user to select either a yes or no to confirm a transaction.

### Use Cases

- Transaction confirmations (payments, transfers)
- Irreversible actions requiring explicit approval

### Interface

```typescript
interface ConfirmationWidget {
  type: 'confirmation';
  title: string;
  confirmation_text?: string;
  on_confirm: {
    tool: string;
    parameters: { [key: string]: unknown };
  };
  on_cancel: {
    tool: string;
    parameters: { [key: string]: unknown };
  };
  channel_adaptation?: {
    voice?: {
      show_options?: boolean;
    };
  };
}
```

### Fields

| Field                     | Description                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `type`                    | Must be `"confirmation"`                                                             |
| `title`                   | Title displayed above the options                                                    |
| `confirmation_text`       | (Optional) Text to display with the confirmation buttons                                        |
| `on_confirm`              | Action to take when user clicks the Confirm button                                   |
| `on_confirm.tool`         | Name of the tool to call when confirmation event occurs                              |
| `on_confirm.parameters`   | Parameters to pass to the confirm tool                                               |
| `on_cancel`               | Action to take when user clicks the Cancel button                                    |
| `on_cancel.tool`          | Name of the tool to call when the cancelation event occurs                           |
| `on_cancel.parameters`    | Parameters to pass to the cancelation tool                                           |
| `channel_adaptation`      | (Optional) Channel specific information needed to render the widget                             |

Here are the channel adaptation specific properties:

| Field                                       | Description                                                                                 |
| ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `channel_adaptation.voice.show_options`     | (Optional) Certain options such as `yes`/`no` confirmations should not be rendered in voice as a menu. |


### Channel Adaptation

- **Web/Mobile:** Renders two buttons for user confirmation.
- **Voice:** Reads options and accepts verbal selection or DTMF input.
- **SMS:** Lists confirmation options with numbers for selection

---

## DatetimeWidget

Presents an interface for collecting one of the following:
- **date** - Date delivered in `YYYY-MM-DD` format (ISO 8601).
- **time** - Time delivered in `hh:mm` format (ISO 8601).
- **datetime** - Datetime delivered in `YYYY-MM-DDThh:mm` format (ISO 8601).

### Use Cases

- Scheduling payments or transfers
- Appointment booking
- Any scenario requiring date or time input

### Interface

```typescript
interface DatetimeWidget {
  type: 'datetime';
  collection_type: 'date' | 'time' | 'datetime';
  title: string;
  description?: string;
  min_datetime?: string;
  max_datetime?: string;
  on_event: {
    tool: string;
    parameters: { [key: string]: unknown };
    map_input_to: string;
  };
}
```

### Fields

| Field                     | Description                                  |
| ------------------------- | -------------------------------------------- |
| `type`            | Must be `"datetime"`                      |
| `collection_type` | Must be `"date"`, `"time"`, or `"datetime"` |
| `title`                   | Title displayed above the widget. If no associated text content block is included this title will be read back to the caller for voice.        |
| `description`             | (Optional) Additional context or instructions           |
| `min_datetime`                 | (Optional) Minimum selectable datetime. Format is dependent on the collection_type field. It will be either in YYYY-MM-DD format for `date`, hh:mm format for `time` and YYYY-MM-DDThh:mm for `datetime`. |
| `max_datetime`                 | (Optional) Maximum selectable datetime. It will be either in YYYY-MM-DD format for `date`, hh:mm format for `time` and YYYY-MM-DDThh:mm for `datetime`. |
| `on_event`                | Action to take when user selects a date      |
| `on_event.tool`       | Name of the tool to call with the selection  |
| `on_event.parameters`     | Base parameters to pass to the tool          |
| `on_event.map_input_to` | Name of the input parameter to set the date/time value on.|

### Example

```typescript
const today = new Date();
const minDate = new Date(today);
minDate.setDate(today.getDate() + 3);
const maxDate = new Date(today);
maxDate.setDate(today.getDate() + 30);

const datePickerWidget = {
  type: 'datetime',
  collection_type: 'date',
  title: 'Select Transfer Date',
  description: 'Choose when you want the transfer to occur (must be at least 3 days from now, within 30 days):',
  min_datetime: minDate.toISOString().split('T')[0], // Format: YYYY-MM-DD
  max_datetime: maxDate.toISOString().split('T')[0], // Format: YYYY-MM-DD
  on_event: {
    tool: 'prepare_money_transfer',
    parameters: {
      from_account_id: 'acc_checking_001',
      to_account_id: 'acc_savings_001',
      amount: 500
    },
    map_input_to: 'scheduled_date'
  },
};
```

### Channel Adaptation

- **Web/Mobile:** Renders as a visual calendar picker for date or a visual time picker for time (or both).
- **Voice:** Renders the title into voice if no content block is set with **user: audience**. The voice response from the user is transcribed and converted into the right date/time value format.
- **All other channels:** Renders the title into text if no content block is set with **user: audience**. The date/time value is converted into a string in the right format and passed as a parameter.

---

## NumberWidget

Presents an interface for collecting one of the following:
- **number** - Number captured in a standard number format.
- **currency** - Number captured as any standard currency.

### Use Cases

- Collecting payment or transfer amounts
- Gathering numeric data (account numbers, quantities)
- Any scenario requiring numeric input

### Interface

```typescript
interface NumberWidget {
  type: 'number';
  collection_type:  'integer' | 'currency' | 'percentage' | 'decimal' | 'phone' | 'zip_code';
  title?: string;
  description?: string;
  min_number?: number;
  max_number?: number;
  min_digits?: number;
  max_digits?: number;
  on_event: {
    tool: string;
    parameters: { [key: string]: unknown };
    map_input_to: string;
  };
}
```

### Fields

| Field                     | Description                                  |
| ------------------------- | -------------------------------------------- |
| `type`            | Must be `"number"`                      |
| `collection_type` | Must be `integer`, `currency`, `percentage`, `decimal`, `phone` or `zip_code`
| `title`                   | (Optional) Title displayed above the widget. If no associated text content block is included this title will be read back to the caller for voice.        |
| `description`             | (Optional) Additional context or instructions           |
| `min_number`             | (Optional) Minimum number allowed                      |
| `max_number`             | (Optional) Maximum number allowed                      |
| `min_digits`             | (Optional) Minimum number of digits allowed                      |
| `max_digits`             | (Optional) Maximum number of digits allowed                      |
| `on_event`                | Action to take when user inputs the number      |
| `on_event.tool`       | Name of the tool to call with the number  |
| `on_event.parameters`     | Base parameters to pass to the tool          |
| `on_event.map_input_to` | Name of the input parameter to set the number on.|

### Example

```typescript
const currencyCollectorWidget = {
  type: 'number',
  collection_typpe: 'currency',
  title: 'How much do you want to transfer?',
  min_number: 1.00, // Any supported currency value
  max_number: 10000.00, // Any supported currency value
  on_event: {
    tool: 'prepare_money_transfer',
    parameters: {
      from_account_id: 'acc_checking_001',
      to_account_id: 'acc_savings_001'
    },
    map_input_to: 'amount_to_transfer'
  },
};
```

### Channel Adaptation

- **Web/Mobile:** Renders as a currency collector or may just rely on the text input field to collect the number.
- **Voice:** enders the title into voice if no content block is set with **user: audience**. The voice response from the user is transcribed and converted into either formatted currency or the specified number (assuming it falls within the configured range).
- **All other channels:** The number value is converted into the right format and passed as a parameter. 

---

## OptionsWidget

Presents a list of options for user selection with flexible display preferences. The selector can be used for single choice or multi-choice scenarios.

### Use Cases

- Menu selections
- Multiple choice questions
- Preference selection
- Category browsing
- Any scenario requiring user choice from options
- Regulatory compliance scenarios

### Interface

```typescript
interface OptionsWidget {
  type: 'options';
  title: string;
  description?: string;
  is_multi_selection?: boolean;
  options: Option[];
  on_event: {
    tool: string;
    parameters: { [key: string]: unknown };
    map_input_to: string;
  };
  channel_adaptation?: {
    chat?: {
      preference?: 'button' | 'dropdown' | 'list';
    };
    voice?: {
      show_options?: boolean;
    };
  };
}

interface Option {
  label: string;
  value: string;
}
```

### Fields

| Field                     | Description                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `type`                    | Must be `"options"`                                                         |
| `title`                   | Title displayed above the options                                                    |
| `description`             | (Optional) Additional context or instructions                                                   |
| `is_multi_selection`      | (Optional) If `true`, allows multiple selections. Defaults to `false`                           |
| `options`                 | Array of option objects with `label` and `value` properties                          |
| `on_event`                | Action to take when user selects an option                                           |
| `on_event.tool`           | Name of the tool to call with the selection                                          |
| `on_event.parameters`     | Base parameters to pass to the tool                                                  |
| `on_event.map_input_to`   | Parameter name to map the selected value to. Will contain the option value for the single selection or a comma separated list of values for multi selection |
| `channel_adaptation`      | (Optional) Channel specific information needed to render the widget                             |

Here are the channel adaptation specific properties:

| Field                                       | Description                                                                                 |
| ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `channel_adaptation.type`                   | Type of channel adaptation. Currently only `chat` and `voice` are supported.                |
| `channel_adaptation.chat`                   | (Optional) Dictionary object for chat related adaptations.                                             |
| `channel_adaptation.chat.preference`        | (Optional) Display preference: `button`, `dropdown`, or `list`                                         |
| `channel_adaptation.voice`                  | (Optional) Dictionary object for voice related adaptations.                                            |
| `channel_adaptation.voice.show_options`     | (Optional) Certain options such as `yes`/`no` confirmations should not be rendered in voice as a menu. |


### Example

```typescript
_meta: {
  'com.ibm.orchestrate/widget':{
    type: 'options',
    title: 'Choose an action',
    description: 'What would you like to do?',
    options: [
      {
        label: 'Check Balance',
        value: 'check_balance'
      },
      {
        label: 'Transfer Money',
        value: 'transfer_money'
      },
      {
        label: 'View Transactions',
        value: 'view_transactions'
      }
    ],
    on_event: {
      tool: 'handle_user_action',
      parameters: {
        user_id: 'user_12345'
      },
      map_input_to: 'selection'
    },
    channel_adaptation: {
      chat: {
        preference: 'button'
      }
    }
  }
}
```

### Channel Adaptation

- **Web/Mobile:** Renders according to preference (buttons, dropdown, or list)
- **Voice:** Reads options and accepts verbal selection or DTMF input.
- **SMS:** Lists options with numbers for selection

---

## TextWidget

This widget collects a string of text from the user. Many variations of text input are supported, including:

- Free-form text
- Email input
- URL input
- Alphanumeric input

The collection can be of a string or a regex expression can be provided to capture a specific pattern.

### Use Cases

- Collecting customer IDs or account numbers
- Gathering free-form text responses
- Capturing structured data with regex patterns
- Email or URL collection
- Any scenario requiring text input from the user

### Interface

```typescript
interface TextWidget {
  type: 'text';
  collection_type: 'text' | 'regex';
  title: string;
  regex_expression?: string;
  on_event: {
    tool: string;
    parameters: { [key: string]: unknown };
    map_input_to: string;
  };
}
```

### Fields

| Field                     | Description                                  |
| ------------------------- | -------------------------------------------- |
| `type`            | Must be `"text"`                      |
| `collection_type` | Must be `"text"` or `"regex"` |
| `title`                   | If no associated text content block is included this title will be rendered on the channel.        |
| `regex_expression` | (Optional) Only used if `collection_type` is `"regex"`. Defines the pattern to match |
| `on_event`                | Action to take when user provides text input      |
| `on_event.tool`       | Name of the tool to call with the text input  |
| `on_event.parameters`     | Base parameters to pass to the tool          |
| `on_event.map_input_to` | Name of the input parameter to set the text value on.|

### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "What is your customer ID?",
      annotations: {audience: ["user"]},
    }
  ],
  _meta: {
    com.ibm.orchestrate/widget: {
      type: "text",
      collector_type: "regex"
      regex_expression: "\b[ABC]\d{8}\b",
      on_event: {
        tool: 'get_account_balance',
        parameters: {
          account_id: 'acc_checking_001'
        },
        map_input_to: 'customer_id'
      }
    },
  }          
};
```

### Channel Adaptation

- **Voice:** Renders the title into voice if no content block is set with **user: audience**. The voice input from the user is transcribed and converted into text input to the tool.
- **All other channels:** Typically, the content block will contain the phrase requesting the text input. The input from the user is converted into text input to the tool. If no regex expression is included the full text response is sent to the tool.

