### Use Flow agent with `docext` node from WxO Chat

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `user_activity_agent`
5. Type in something like `invoke user flow`. Then, the agent will promt you for inputs


### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py "<your URL goes here>"`