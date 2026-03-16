# User Activity with Forms Example

This example demonstrates how to create flow tools with user forms in IBM watsonx Orchestrate. It includes two flow tools within a single agent:

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

## Project Structure

```
user_activity_with_forms/
├── agents/
│   └── user_activity_agent_forms.yaml       # Agent configuration with both tools
├── tools/
│   ├── user_flow_forms.py                   # Application form flow tool
│   └── user_flow_forms_date_time.py         # Date/time form flow tool
├── generated/
│   ├── flow_with_user_form.json             # Generated application form spec
│   └── flow_with_user_form_date_time.json   # Generated date/time form spec
├── main.py                                   # Script to generate both flow specs
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
4. Pick the `user_activity_agent_forms`
5. Type in something like `Create an application form` to test the normal form, or `Create a date time form` to test the date/time form. The agent will prompt you for inputs.

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
2. Import both flow tools from their respective files:
   - `user_flow_forms.py` (Application form)
   - `user_flow_forms_date_time.py` (Date/time form)
3. Import the agent configuration that uses both tools

## Agent Configuration

The agent (`user_activity_agent_forms.yaml`) is configured to use both flow tools:

```yaml
tools:
  - user_flow_application_form
  - user_flow_application_form_date_time
```

The agent can intelligently choose which form to present based on the user's needs:
- Use `user_flow_application_form` for general application data
- Use `user_flow_application_form_date_time` for date and time input


