# This project includes two examples of using agent nodes, the first in a pro-code python flow and the second in a low-code flow-builder flow.
# In both the pro-code and low-code examples the flow runs four agent nodes in sequence. To achieve this in low-code each agent node is wrapped in
# a pro-code flow. Once the individual pro-code flows are imported into the agent runtime then they were included in the low-code flow as tools.

### Testing Flow inside an Agent

1. Run `import-all.sh` 
2. Launch the Chat UI with `orchestrate chat start`
3. Pick the `get_city_fact_agents`
4. Type in something like `my city is San Jose`
5. You can ask the agent to check the status of the flow with `what is the current status?`

### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`

### Testing Low-code Flow inside an Agent

1. Run `import-all.sh` 
2. Launch the Chat UI with `orchestrate chat start`
3. Pick the `get_city_facts_agent_low_code`
4. Type in something like `my city is San Jose`
5. You can ask the agent to check the status of the flow with `what is the current status?`
