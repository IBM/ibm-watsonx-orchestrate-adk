# Count Tracker Flow

Demonstrates using an **AgentNode** inside a pro-code flow — a flow step that
delegates work to another registered WXO agent.

## Overview

The flow contains a single AgentNode that delegates the message
`"What is the current count?"` to `count_tracker_agent`.  
The agent increments its running counter and returns the current value, which
the flow maps to the output and returns to the user.

## Structure

```
count_tracker_flow/
├── agents/
│   ├── count_tracker_agent.yaml       # inner agent called by the AgentNode
│   └── count_tracker_flow_agent.yaml  # top-level agent that exposes the flow
├── tools/
│   └── count_tracker_flow.py          # flow definition
├── main.py                            # run the flow programmatically
├── import-all.sh                      # one-shot import script
└── README.md
```

## Key concepts

### AgentNode

An `AgentNode` delegates a step of the flow to another registered WXO agent.

```python
agent_node: AgentNode = aflow.agent(
    name="count_tracker",
    agent="count_tracker_agent",
    message="What is the current count?",
    output_schema=AgentNodeOutput,
    thread_control_policy="REUSE_AND_CORRELATE",
)
```

### Thread control policies

| Policy | Behaviour |
|---|---|
| `REUSE_AND_CORRELATE` | Reuses a correlated thread if one exists, otherwise creates one |
| `CREATE_ALWAYS` | Always creates a new isolated thread for the agent on every run |

## Setup

### Option 1: Import and use with the Chat UI

```bash
bash examples/flow_builder/count_tracker_flow/import-all.sh
```

Imports in order:
1. `count_tracker_agent` — the inner agent
2. `count_tracker_flow` — the flow tool
3. `count_tracker_flow_agent` — the top-level agent

Then start the chat UI:

```bash
orchestrate chat start
```

Pick **`count_tracker_flow_agent`** and type:

```
What is the current count?
```

### Option 2: Run programmatically

```bash
# Set PYTHONPATH to the repo root first
PYTHONPATH=. python examples/flow_builder/count_tracker_flow/main.py
```
