# Flow Callback Handler Example (No Database)

This example demonstrates how to use Flow Callbacks. 

## Overview

The Flow Callback Handler is a **Flow tool**  that receives flow events when they occur during flow execution.

## Components

### Tools
- **flow_callback_handler.py** - A Flow tool that receives and processes flow callback events (called automatically by the flow engine)
- **task_callback_handler.py** - A Flow tool that receives and processes taskWait callback events (called automatically by the flow engine)
- **example_flow_with_callback.py** - Example flow demonstrating callback configuration

### Agent
- **agents/flow_callback_agent.yaml** - Sample agent that can execute flows with callbacks

### Scripts
- **import-all.sh** - Script to import tools and agent into watsonx Orchestrate


## Setup

### Import Tools and Agent

To use the tools and agent in watsonx Orchestrate, run:

```bash
cd examples/flow_builder/flow_callback_no_db
./import-all.sh
```

This will:
- Import the `flow_as_callback_handler` (Flow tool)
- Import the `callback_handler_on_task_wait` (Flow tool)
- Import the `flow_with_callbacks_tool` (example flow with callbacks configured)
- Import the `flow_callback_agent` agent

## How It Works

### The Callback Handler Flow

The callback handler is defined as a Flow tool in `flow_callback_handler.py`:

```python
from ibm_watsonx_orchestrate.flow_builder.flow_callback_types import (
    FlowCallbackEventsPayload
)

@flow(
    name="flow_as_callback_handler",
    display_name="Flow as Tool Callback",
    description="A flow that receives callback events from other flows",
    input_schema=FlowCallbackEventsPayload
)
def build_example_flow_callbacks(aflow: Flow) -> Flow:
    # Script node that processes events
    script_node = aflow.script(
        name="process_events",
        output_schema=ScriptOutputSchema,
        script="""
# Process the received callback events
print(f"Received {len(flow.input.events)} callback events")
for event_payload in flow.input.events:
    event = event_payload['event']
    print(f"Event: {event['kind']} - Flow: {event['flow_name']} - State: {event['state']}")

# Set the output to return the events
self.output.outEvents = flow.input.events
"""
    )
    
    aflow.sequence(START, script_node, END)
    return aflow
```

**Key Points:**
- Accepts `FlowCallbackEventsPayload` as input (array of callback events)
- Each event contains:
  - `event`: Metadata (id, kind, created_at, instance_id, flow_name, state, etc.)
  - `output`: Optional output data (when flow completes)
  - `elicitation`: Optional elicitation details (when user input required)
- Returns the events in `outEvents` field

### Configuring Callbacks in a Flow

In `example_flow_with_callback.py`, callbacks are configured using `add_callback()`:

```python
@flow(
    name="flow_with_callbacks_tool",
    display_name="Flow with Tool as Callback",
    input_schema=FlowInput,
    output_schema=FlowOutput
)
def build_example_flow_with_callbacks(aflow: Flow) -> Flow:
    # Build your flow nodes
    user_flow = aflow.userflow()
    greeting_node = aflow.tool(greeting_tool)
    aflow.sequence(START, user_flow, greeting_node, END)
    
    # Add callback configuration
    aflow.add_callback(
        tool="flow_as_callback_handler",  # Name of the callback handler flow
        events=[
            FlowCallbackEventKind.ON_FLOW_START,
            FlowCallbackEventKind.ON_FLOW_END,
            FlowCallbackEventKind.ON_FLOW_ERROR,
            FlowCallbackEventKind.ON_TASK_WAIT,
            FlowCallbackEventKind.ON_TASK_ERROR
        ]
    )
    
    return aflow
```

## Supported Event Types

### Flow Events
- `FlowCallbackEventKind.ON_FLOW_START` - Flow execution started
- `FlowCallbackEventKind.ON_FLOW_END` - Flow execution completed successfully
- `FlowCallbackEventKind.ON_FLOW_ERROR` - Flow execution failed with an error

### Task Events
- `FlowCallbackEventKind.ON_TASK_WAIT` - Task is waiting for user input
- `FlowCallbackEventKind.ON_TASK_ERROR` - Task execution failed with an error
- `FlowCallbackEventKind.ON_TASK_MESSAGE` - Task generated a message

## Using the Agent

Once imported, you can interact with the `flow_callback_agent` to:

1. **Execute flows with callbacks**:
   ```
   User: "Run the example flow with callbacks"
   Agent: [Executes flow_with_callbacks_tool which automatically triggers callback events]
   ```

**Note**: The `flow_as_callback_handler` is called automatically by the flow engine when events occur - the agent doesn't need to call it directly.

## Event Payload Structure

When the callback handler receives events, each event has this structure:

```python
{
    "event": {
        "id": "unique-event-id",
        "kind": "flow:on_flow_start",  # Event type
        "created_at": "2026-04-28T18:35:12.706Z",
        "instance_id": "flow-instance-id",
        "flow_name": "flow_with_callbacks_tool",
        "environment_id": "draft",
        "state": "working",  # or "completed", "failed"
        "parent_instance_id": "parent-flow-id",  # if nested
        "parent_flow_name": "parent-flow-name",  # if nested
        "task_id": "task-id",  # for task events
        "task_name": "task_name",  # for task events
        "task_display_name": "Task Display Name",  # for task events
        "error": {...}  # for error events
    },
    "output": {...},  # Present when flow completes
    "elicitation": {...}  # Present when user input required
}
```

## Troubleshooting

### Import Errors

If the import fails, make sure:
1. You have the watsonx Orchestrate CLI installed
2. You're logged in: `orchestrate login`
3. You have the correct environment activated: `orchestrate env activate local`


### Callback Not Triggering

If callbacks aren't being invoked:
1. Verify the callback handler tool name matches exactly: `flow_as_callback_handler`
2. Check that the flow with callbacks was imported successfully
3. Ensure the event types are valid `FlowCallbackEventKind` values


## License

This example is part of the watsonx Orchestrate SDK and follows the same license.
