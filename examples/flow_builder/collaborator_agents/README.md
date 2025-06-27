### Testing Flow inside an Agent

1. Run `import-all.sh` 
2. Launch the Chat UI with `orchestrate chat start`
3. Pick the `get_city_fact_agents`
4. Type in something like `my city is San Jose`
5. You can ask the agent to check the status of the flow with `what is the current status?`

### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`
