### Testing Flow inside an Agent

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `hello_message_agent`
5. Type in something like `get me a hello message for John Doe`.
6. You can ask the agent to check the status of the flow with `what is the current status?`

### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`
