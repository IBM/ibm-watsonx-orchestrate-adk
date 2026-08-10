# MultiTurnWidget Examples

This directory contains examples demonstrating how to use the `MultiTurnWidget` class for creating conversational, multi-turn interactions in WatsonX Orchestrate.

## Overview

The `MultiTurnWidget` class enables tools to collect user input through a series of conversational turns, maintaining state and context throughout the interaction. Each widget focuses on a single field per turn, creating a more natural conversational flow compared to multi-field forms.

**Important:** MultiTurnWidget completely reuses FormInput components from FormWidget. This means any future changes to form widgets (TextInput, NumberInput, etc.) automatically apply to multi-turn flows as well, ensuring consistency and reducing maintenance overhead.

## Key Features

- **Single-field focus**: Each turn collects one piece of information
- **State persistence**: Maintains state across multiple turns
- **Context tracking**: Tracks conversation history and metadata
- **Complete widget reuse**: Fully leverages all FormWidget input types (TextInput, NumberInput, etc.)
- **Automatic updates**: Changes to FormWidget components automatically apply to multi-turn flows
- **Validation support**: Handles validation errors and retry logic
- **Session management**: Supports session-based and context-based state

## Examples

### basic_example.py

Comprehensive examples covering:

1. **Basic Text Input Widget**: Simple single-turn interaction
2. **Multi-Turn Conversation**: Multiple widgets in sequence
3. **Validation and Error Handling**: Handling invalid input and retries
4. **Context and State Management**: Working with conversation context
5. **Response Format Validation**: Validating against Arch.Guide specifications

## Running the Examples

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the basic examples
python examples/multiturn_widgets/basic_example.py
```

## Quick Start

### Basic Usage

```python
from ibm_watsonx_orchestrate.run.widgets import (
    MultiTurnWidget,
    TextInput,
)

# Create a multi-turn widget
# Note: Title goes on the TextInput, not on MultiTurnWidget
widget = MultiTurnWidget(
    name="username_input",
    input=TextInput(
        name="username",
        title="Enter your username",  # Title is on the input component
        required=True
    )
)

# Initialize the widget
widget.initialize(session_id="my_session")

# Generate response for user
response = widget.to_response()
# Send response to chat interface...

# After user provides input
widget.update_state(user_input="john.doe")

# Mark as complete when done
widget.mark_complete()
widget.cleanup()
```

### Multi-Turn Conversation

```python
# Turn 1: Collect name
name_widget = MultiTurnWidget(
    input=TextInput(
        name="name",
        title="Your Name"  # Title on the input
    )
)
name_widget.initialize(session_id="registration")
response1 = name_widget.to_response()
# ... user responds ...
name_widget.update_state("John Doe")

# Turn 2: Collect email
email_widget = MultiTurnWidget(
    input=TextInput(
        name="email",
        title="Your Email"  # Title on the input
    )
)
email_widget.initialize(session_id="registration")
response2 = email_widget.to_response()
# ... user responds ...
email_widget.update_state("john@example.com")
```

### Validation and Error Handling

```python
widget = MultiTurnWidget(
    input=TextInput(
        name="email",
        title="Email",  # Title on the input
        required=True
    )
)
widget.initialize()

# Invalid input
widget.update_state(
    user_input="invalid-email",
    is_valid=False,
    validation_errors=["Invalid email format"]
)

# Valid input
widget.update_state(
    user_input="user@example.com",
    is_valid=True
)
```

## Supported Widget Types

All FormWidget input types are fully supported and reused:

- **Text Inputs**: `TextInput`, `TextArea`
- **Selection**: `RadioButton`, `Checkbox`, `ComboBox`
- **Numbers**: `NumberInput`
- **Dates**: `DatePicker`, `DateRangePicker`
- **Files**: `FileUpload`, `FileDownload`
- **Tables**: `Table`

**Note:** These components are completely reused from FormWidget, so any enhancements or fixes to these widgets automatically benefit multi-turn flows.

## Response Format

The `MultiTurnWidget` generates responses in the format specified by the Arch.Guide:

```json
{
  "response_type": "multiturn_form",
  "name": "widget_id",
  "json_schema": {
    "type": "object",
    "title": "Widget Title",
    "properties": { ... },
    "required": [ ... ]
  },
  "ui_schema": {
    "field_name": {
      "ui:widget": "TextWidget"
    }
  },
  "form_data": {
    "field_name": "default_value"
  },
  "session_id": "session_123",
  "context": {
    "conversation_id": "conv_456",
    "turn_number": 1,
    "is_complete": false
  }
}
```

## State Management

The `MultiTurnWidget` supports three state management strategies:

1. **Session-based**: Stores state in memory (or external store like Redis)
2. **Context-based**: Embeds state in conversation context
3. **Hybrid** (default): Uses session storage with context fallback

```python
from ibm_watsonx_orchestrate.run.widgets import (
    MultiTurnWidget,
    SessionStateManager,
    ContextStateManager,
    HybridStateManager,
)

# Use session-based state management
widget = MultiTurnWidget(
    input=TextInput(name="field", title="Field"),
    state_manager=SessionStateManager(ttl=3600)
)

# Use context-based state management
widget = MultiTurnWidget(
    input=TextInput(name="field", title="Field"),
    state_manager=ContextStateManager()
)

# Use hybrid state management (default)
widget = MultiTurnWidget(
    input=TextInput(name="field", title="Field"),
    state_manager=HybridStateManager(ttl=3600)
)
```

## Context Tracking

Access conversation context and history:

```python
# Get current context
context = widget.get_context()
print(f"Conversation ID: {context['conversation_id']}")
print(f"Turn Number: {context['turn_number']}")
print(f"History: {context['turn_history']}")

# Set context (for restoration)
widget.set_context({
    "turn_number": 3,
    "is_complete": False
})

# Get conversation summary
summary = widget.get_summary()
print(f"Total Turns: {summary['conversation_summary']['total_turns']}")
print(f"Completed: {summary['conversation_summary']['completed_turns']}")
```

## Lifecycle Methods

```python
# Initialize widget
widget.initialize(session_id="optional_session_id")

# Update state after user input
widget.update_state(
    user_input="value",
    metadata={"source": "web"},
    is_valid=True
)

# Mark interaction as complete
widget.mark_complete()

# Cleanup resources
widget.cleanup(delete_state=True)  # Optionally delete persisted state
```

## Best Practices

1. **Always initialize**: Call `initialize()` before using the widget
2. **Use session IDs**: Provide consistent session IDs for related turns
3. **Handle validation**: Use `is_valid` and `validation_errors` for user feedback
4. **Track metadata**: Add metadata to turns for debugging and analytics
5. **Cleanup properly**: Call `cleanup()` when interaction is complete
6. **Check context**: Use `get_context()` to understand conversation state

## Architecture

The MultiTurnWidget implementation follows the architecture specified in the Arch.Guide:

- **Complete component reuse**: Fully reuses FormInput components from FormWidget
- **Automatic updates**: Changes to FormWidget components automatically apply to multi-turn flows
- **No duplication**: Zero code duplication between FormWidget and MultiTurnWidget input handling
- Uses `response_type: "multiturn_form"` to distinguish from multi-field forms
- Supports all 14+ widget types from FormWidget
- Maintains state across multiple conversational turns
- Tracks context and conversation history
- Title parameter removed from MultiTurnWidget (titles go on individual inputs)

## Related Documentation

- [Arch.Guide](../../Arch.Guide) - Architecture decision record
- [FormWidget Documentation](../../src/ibm_watsonx_orchestrate/run/widgets/forms/types.py)
- [MultiTurnWidget Implementation](../../src/ibm_watsonx_orchestrate/run/widgets/multiturn/types.py)

## Support

For questions or issues, please refer to the main project documentation or contact the ADK team.