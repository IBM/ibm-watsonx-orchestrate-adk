### Agent nodes are currently supported directly in pro-code flows. However, it is possible to add pro-code flows that include agent nodes to low-code flows. This sample includes examples of both.

### Testing pro-code Flow inside an Agent

1. Run `import-all.sh` 
2. Launch the Chat UI with `orchestrate chat start`
3. Pick the `get_city_fact_agents`
4. Type in something like `my city is San Jose`
5. You can ask the agent to check the status of the flow with `what is the current status?`

### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`

### Testing Low-Code Flows

1. Run `import-all.sh` 
2. Launch the Chat UI with `orchestrate chat start`
3. Pick the `get_city_facts_agent_low_code`
4. Type in something like `my city is San Jose`
5. You can ask the agent to check the status of the flow with `what is the current status?`

