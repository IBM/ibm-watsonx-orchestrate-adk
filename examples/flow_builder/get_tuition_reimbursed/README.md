### Testing Flow programmatically(RECOMMEND)
Since the flow is complicated and it will take a long time to complete, running the `main.py` is prefered comparing to using the agent

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`

If you run into some issue in the first run, retry it.

### Testing Flow inside an Agent

1. To test this example, make sure the Flow runtime is activated by starting the server with the `--with-flow-runtime` option.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `get_tuition_reimbursed`
5. Type in something like `1, 2`.
6. You can ask the agent to check the status of the flow with `what is the current status?`
