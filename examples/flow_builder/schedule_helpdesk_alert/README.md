### Testing Flow inside an Agent

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `schedule_alert_agent`
5. Use the sample support request: 
    
    `I want to schedule a call to alert_helpdesk_flow everyday at 8:33PM PST for today for product CRM`
    
6. You can ask the agent to check the status of the flow with `what is the current status?`

### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`
