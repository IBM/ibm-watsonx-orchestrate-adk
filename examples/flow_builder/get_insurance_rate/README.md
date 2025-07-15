### Testing Flow inside an Agent

1. To test this example, we make use of the Decisions node to create a decisions table to calculate the insurance rate.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `insurance_assessment_agent`
5. Use the request: 
    
    `What would be the insurance rate for someone with credit rating 'A' and loan amount of 850000 dollars?`

### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`
