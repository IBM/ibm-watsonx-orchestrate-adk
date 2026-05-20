# Flow Callback Handler Example

This example demonstrates how to use the Flow Callback Handler to track and store flow events in AstraDB.

## Overview

The Flow Callback Handler is a tool that captures flow events (like flow start, flow end, task wait, etc.) and stores them in an AstraDB table for tracking, auditing, and analysis purposes.

## Components

### Tools
- **flow_callback_handler.py** - The main tool that handles flow events and stores them in AstraDB (called automatically by the flow engine)
- **query_flow_events.py** - Query tool for retrieving stored flow events from AstraDB (used by agents to check events)
- **greeting_tool.py** - Simple greeting tool used in the example flow
- **example_flow_with_callbacks.py** - Example flow demonstrating callback configuration
- **flow_callback_types.py** - Pydantic models for flow callback event payloads

### Agent
- **agents/flow_callback_agent.yaml** - Sample agent that can execute flows with callbacks and query stored events

### Scripts
- **flow_callback_tester.py** - Interactive CLI tool to test the handler and retrieve stored events
- **setup_astra_table.sh** - Script to create the required AstraDB table and indexes
- **delete_astra_table.sh** - Script to delete the AstraDB table
- **import-all.sh** - Script to import tools and agent into watsonx Orchestrate

## Setup

### 1. Configure AstraDB

First, copy the example environment file and configure your AstraDB credentials:

```bash
cp .env.example .env
```

Edit `.env` and set your AstraDB credentials:

```bash
ASTRA_TOKEN=AstraCS:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ASTRA_URL=https://<your-astra-endpoint>
ASTRA_KEYSPACE=default_keyspace
```

You can get your AstraDB token from: https://astra.datastax.com/settings/tokens

### 2. Create the Database Table

Run the setup script to create the `flow_events` table in AstraDB:

```bash
./setup_astra_table.sh
```

This will create:
- A `flow_events` table with all necessary columns
- Indexes on `instance_id`, `event_type`, and `timestamp` for efficient querying

### 3. Import Tools and Agent

To use the tools and agent in watsonx Orchestrate, run:

```bash
./import-all.sh
```

This will:
- Create a connection named `flow_callback_app` with your AstraDB credentials
- Import the `flow_callback_handler` tool (called automatically by flows)
- Import the `query_flow_events` tool (used by agents to retrieve events)
- Import the `greeting_tool` tool
- Import the `example_flow_with_callbacks` flow
- Import the `flow_callback_agent` agent

## Debugging in VSCode

The workspace includes VSCode debug configurations in the root `.vscode/launch.json` for easy debugging:

### Available Debug Configurations

1. **Flow Callback Tester (Interactive)** - Run the interactive tester with full debugging support
   - Launches the interactive menu
   - Set breakpoints in the tester code
   - Step through event sending and retrieval

2. **Flow Callback Tester - Send Event** - Quick debug for sending a test event
   - Automatically sends a `flow:on_flow_start` event
   - Useful for debugging the send flow

3. **Flow Callback Tester - Retrieve Events** - Quick debug for retrieving events
   - Automatically retrieves events
   - Useful for debugging the retrieval flow

4. **Flow Callback Tester - Test Connection** - Quick debug for connection testing
   - Automatically tests the AstraDB connection
   - Useful for debugging connection issues

5. **Flow Callback Handler - Direct Test** - Debug the handler directly
   - Bypasses the tester and calls the handler directly
   - Useful for debugging the core handler logic

### How to Use

1. Open the workspace root folder in VSCode (where the `.vscode` directory is located)
2. Press `F5` or go to Run → Start Debugging
3. Select one of the "Flow Callback" debug configurations
4. Set breakpoints as needed in the tester or handler code
5. Step through the code to debug

### Tips

- Use the "Flow Callback Tester (Interactive)" for full interactive debugging
- Use the quick debug configs for faster iteration on specific features
- Set breakpoints in `flow_callback_handler.py` to debug the core logic
- Set breakpoints in `flow_callback_tester.py` to debug the CLI interface

## Testing the Handler

The `flow_callback_tester.py` script provides an **interactive CLI experience** to test the handler without setting up a full flow.

### Launch the Interactive Tester

Simply run:

```bash
python flow_callback_tester.py
```

You'll be presented with a menu:

```
================================================================================
                    Flow Callback Handler Tester
================================================================================

What would you like to do?

  1. Send a test event
  2. Retrieve stored events
  3. Test AstraDB connection
  4. Exit
```

### Send Test Events

Select option 1 to send a test event. The interactive CLI will guide you through:

1. **Selecting event type** - Choose from flow or task events
2. **Providing instance ID** - Auto-generated or custom
3. **Flow details** - Flow name and ID
4. **Task details** - For task events (task ID, name, assignee)
5. **Error details** - For error events (message and code)
6. **Optional metadata** - Custom key-value pairs

After sending, you can immediately verify the event was stored.

### Retrieve Stored Events

Select option 2 to retrieve events. You can:

1. **View all events** - Latest 10 events
2. **Filter by instance ID** - See all events for a specific flow instance
3. **Filter by event type** - See all events of a specific type
4. **Custom filter** - Combine filters and set custom limits

Choose how to display results:
- **Summary view** - Compact table format
- **Detailed view** - Full event details with colors
- **JSON output** - Raw JSON for programmatic use

### Test Connection

Select option 3 to verify your AstraDB connection is working correctly.

## Supported Event Types

### Flow Events
- `flow:on_flow_start` - Flow execution started
- `flow:on_flow_end` - Flow execution completed successfully
- `flow:on_flow_error` - Flow execution failed with an error

### Task Events
- `task:on_task_wait` - Task is waiting for user input
- `task:on_task_error` - Task execution failed with an error
- `task:on_task_message` - Task generated a message

## Database Schema

The `flow_events` table stores the following information:

| Column | Type | Description |
|--------|------|-------------|
| event_id | text | Unique event identifier (PRIMARY KEY) |
| event_type | text | Type of flow event (INDEXED) |
| timestamp | text | ISO 8601 timestamp (INDEXED) |
| instance_id | text | Flow instance identifier (INDEXED) |
| task_id | text | Task identifier |
| flow_id | text | Flow definition identifier |
| thread_id | text | Thread identifier |
| correlation_id | text | Correlation identifier |
| tenant_id | text | Tenant identifier |
| task_name | text | Internal task name |
| task_display_name | text | Human-readable task name |
| task_kind | text | Type of task |
| assignee | text | Assignee user ID |
| flow_name | text | Name of the flow |
| context_data | text | JSON string with flow data |
| metadata | text | JSON string with metadata |
| error | text | JSON string with error info |

## Using the Agent

Once imported, you can interact with the `flow_callback_agent` to:

1. **Execute flows with callbacks**:
   ```
   User: "Run the example flow with callbacks"
   Agent: [Executes example_flow_with_callbacks which automatically triggers callback events]
   ```

2. **Query recent flow events**:
   ```
   User: "Show me the recent flow events"
   Agent: [Uses query_flow_events to retrieve and display recent events from AstraDB]
   ```

3. **Check events for a specific flow instance**:
   ```
   User: "Show me events for flow instance flow-inst-abc123"
   Agent: [Queries events filtered by instance_id]
   ```

4. **Monitor for errors**:
   ```
   User: "Are there any flow errors?"
   Agent: [Queries for flow:on_flow_error and task:on_task_error events]
   ```

5. **Learn about callback functionality**:
   ```
   User: "Explain how flow callbacks work"
   Agent: [Provides detailed explanation of the callback system]
   ```

The agent has access to:
- `example_flow_with_callbacks` - Flow demonstrating callback configuration (callbacks are triggered automatically by the flow engine)
- `query_flow_events` - Tool to retrieve and analyze stored events from AstraDB

**Note**: The `flow_callback_handler` is called automatically by the flow engine when events occur - the agent doesn't need to call it directly.

## Usage in Flows

Once imported, you can configure callbacks in your flows. Callbacks are part of the FlowSpec and are configured using the `add_callback()` method on the Flow object during flow construction:

```python
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow,
    flow,
    START,
    END
)
from ibm_watsonx_orchestrate.flow_builder.flow_callback_types import FlowCallbackEventKind

@flow(
    name="my_flow",
    display_name="My Flow",
    input_schema=InputSchema,
    output_schema=OutputSchema
)
def build_my_flow(aflow: Flow) -> Flow:
    """
    Example flow with callback configuration.
    
    Callbacks are part of the FlowSpec and will be invoked by the flow engine
    when the specified events occur during flow execution.
    """
    # Add your flow nodes
    node1 = aflow.tool(my_tool)
    
    # Connect the flow
    aflow.sequence(START, node1, END)
    
    # Add callbacks to the FlowSpec - these will be invoked by the flow engine
    aflow.add_callback(
        tool="flow_callback_handler",
        events=[
            FlowCallbackEventKind.ON_FLOW_START,
            FlowCallbackEventKind.ON_FLOW_END,
            FlowCallbackEventKind.ON_FLOW_ERROR
        ]
    )
    
    return aflow
```

**Important**: Callbacks are part of the FlowSpec, not the Flow runtime object. They are configured during flow construction and stored in the flow specification. When the flow executes, the flow engine automatically invokes the configured callback tools when the specified events occur.

See `tools/example_flow_with_callbacks.py` for a complete working example.

## Example Workflow

Here's a typical testing workflow:

1. **Start the tester**
   ```bash
   python flow_callback_tester.py
   ```

2. **Test connection** (option 3)
   - Verify your AstraDB credentials are working

3. **Send a flow start event** (option 1)
   - Select `flow:on_flow_start`
   - Use auto-generated instance ID (e.g., `flow-inst-abc123`)
   - Set flow name to "Test Flow"

4. **Send a task wait event** (option 1)
   - Select `task:on_task_wait`
   - Use the same instance ID from step 3
   - Add task details (name, assignee)

5. **Send a flow end event** (option 1)
   - Select `flow:on_flow_end`
   - Use the same instance ID

6. **Retrieve events** (option 2)
   - Filter by the instance ID
   - View in detailed format to see the complete flow lifecycle

## Cleanup

To delete the AstraDB table:

```bash
./delete_astra_table.sh
```

## Troubleshooting

### Connection Issues

If you get connection errors, verify:
1. Your `ASTRA_TOKEN` is valid and not expired
2. Your `ASTRA_URL` is correct (should include the full API endpoint)
3. Your `ASTRA_KEYSPACE` exists in your database

Use the "Test AstraDB connection" option in the interactive tester to diagnose issues.

### Import Errors

If the import fails, make sure:
1. You have the watsonx Orchestrate CLI installed
2. You're logged in: `orchestrate login`
3. You have the correct environment activated: `orchestrate env activate local`

### Table Not Found

If you get "table not found" errors:
1. Run `./setup_astra_table.sh` to create the table
2. Wait a few seconds for the table to be fully created
3. Verify the table exists in the AstraDB console
4. Use the "Test AstraDB connection" option to verify

### Interactive Tester Issues

If the interactive tester doesn't work:
1. Make sure you have Python 3.10+ installed
2. Install required dependencies: `pip install -r tools/requirements.txt`
3. Verify your `.env` file is properly configured

## License

This example is part of the watsonx Orchestrate SDK and follows the same license.

---

Made with Bob