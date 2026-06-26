# User Activity with Forms Example

This example demonstrates how to create flow tools with user forms in IBM watsonx Orchestrate. It includes three flow tools within a single agent:

## Flow Tools

### 1. Application Form (`user_flow_application_form`)
A comprehensive application form that demonstrates various field types:
- Single choice (dropdown)
- Boolean (checkbox)
- Text input
- Number input
- Multi-choice (dropdown and table)
- List input/output
- Field output
- Message output

### 2. Date/Time Form (`user_flow_application_form_date_time`)
A specialized form demonstrating comprehensive date, time, and datetime field variations with real-world examples:
- **Date fields**: Simple date input and date with min/max constraints (e.g., "Casual day off", "Employee vacation")
- **Time fields**: Simple time input and time with min/max constraints (e.g., "Lunch time", "Login time")
- **DateTime fields**: Simple datetime input and datetime with min/max constraints (e.g., "Release Cutoff", "Project submission period")
- **Date range fields**: Start and end date selection with constraints (e.g., "Employee probation period")
- **Time range fields**: Start and end time selection with constraints (e.g., "Working Hours")

### 3. Greetings (No Summarization) (`greetings_no_summarization`)
A simple greeting flow that demonstrates the `suppress_agent_summarization` flag:
- **Purpose**: Shows how to disable agent summarization for simple, straightforward flows
- **Feature**: Uses `suppress_agent_summarization=True` in the flow decorator
- **Content**: Displays a simple "Hello user" message
- **Use case**: Ideal for flows where summarization adds unnecessary overhead

## Project Structure

```
user_activity_with_forms/
├── agents/
│   └── user_activity_agent_forms.yaml       # Agent configuration with all tools
├── tools/
│   ├── user_flow_forms.py                   # Application form flow tool
│   ├── user_flow_forms_date_time.py         # Date/time form flow tool
│   └── greetings_no_summarization.py        # Simple greeting with suppressed summarization
├── generated/
│   ├── flow_with_user_form.json             # Generated application form spec
│   └── flow_with_user_form_date_time.json   # Generated date/time form spec
├── main.py                                   # Script to generate flow specs
├── import-all.sh                             # Script to import tools and agent
└── README.md                                 # This file
```

## Usage

### Generate Flow Specifications

Run the main script to generate JSON specifications for both flows:

```bash
cd wxo-clients/wxo-clients
PYTHONPATH=.:$PYTHONPATH python examples/flow_builder/user_activity_with_forms/main.py
```

This will create two files in the `generated/` directory:
- `flow_with_user_form.json` - Application form specification
- `flow_with_user_form_date_time.json` - Date/time form specification

### Testing Flow Forms inside an Agent

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh`
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `user_flow_forms_agent`
5. Type in something like:
   - `Create an application form` to test the normal form
   - `Create a date time form` to test the date/time form
   - `Show me a greeting` to test the simple greeting with suppressed summarization
   
   The agent will prompt you for inputs or display the appropriate form.

### Testing Flow Programmatically

1. Set `PYTHONPATH=.:$PYTHONPATH` from the `wxo-clients/wxo-clients` directory
2. Run `python main.py` to generate both flow specifications

### Import to Orchestrate Environment

To import both flow tools and the agent into your local Orchestrate environment:

```bash
cd examples/flow_builder/user_activity_with_forms
./import-all.sh
```

This script will:
1. Activate the local Orchestrate environment
2. Import all flow tools from their respective files:
   - `user_flow_forms.py` (Application form)
   - `user_flow_forms_date_time.py` (Date/time form)
   - `greetings_no_summarization.py` (Simple greeting with suppressed summarization)
3. Import the agent configuration that uses all tools

## Agent Configuration

The agent (`user_activity_agent_forms.yaml`) is configured to use all three flow tools:

```yaml
tools:
  - user_flow_application_form
  - user_flow_application_form_date_time
  - greetings_no_summarization
```

The agent can intelligently choose which form to present based on the user's needs:
- Use `user_flow_application_form` for general application data
- Use `user_flow_application_form_date_time` for date and time input
- Use `greetings_no_summarization` for a simple greeting (demonstrates suppressed summarization)

## Feature Highlight: Suppress Agent Summarization

The `greetings_no_summarization` flow demonstrates the `suppress_agent_summarization` flag:

```python
@flow(
    name="greetings_no_summarization",
    display_name="Greetings (No Summarization)",
    description="A simple greeting flow with agent summarization suppressed.",
    suppress_agent_summarization=True  # Disables agent summarization
)
def build_greeting_flow(aflow: Flow = None) -> Flow:
    # ... flow implementation
```

**When to use `suppress_agent_summarization=True`:**
- Simple, straightforward flows where summarization adds unnecessary overhead
- Flows with minimal user interaction
- Flows where the output is already clear and concise
- Performance-sensitive scenarios where you want to reduce processing time

**Default behavior (`suppress_agent_summarization=False`):**
- Agent generates summaries during flow execution
- Useful for complex flows with multiple steps
- Helps users understand what happened during flow execution


