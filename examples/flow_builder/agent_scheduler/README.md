### Testing Flow inside an Agent

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `agent_scheduler`
5. Use the sample support request: 
    
    `I want to schedule agent "<some agent id>" to run everyday at 7am EST for 3 days`
    
6. You can ask the agent to check the status of the flow with `what are the current schedules?`

### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`
