### Testing Flow programmatically(RECOMMEND)
Since the flow is complicated and it will take a long time to complete, running the `main.py` is prefered comparing to using the agent

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`

If you run into some issue in the first run, retry it.

### Testing Flow inside an Agent

1. Run `import-all.sh` 
2. Launch the Chat UI with `orchestrate chat start`
3. Pick the `get_tuition_reimbursed`
4. Type in something like `employees id are 1,2`.
5. You can ask the agent to check the status of the flow with `what is the current status?`
