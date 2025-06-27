### Testing Flow inside an Agent

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `ticket_processing_agent`
5. Use the sample support request: 
    
    `Can you help process the following support request: Date: Thu, 3 Apr 2025 16:46:52 -0400 From: Jane Stevensonjs@acme.com To: customer_support@jacket.com I recently ordered a lather jacket from you, but it's been 2 weeks and I have yet to received it. Here is my order number: 2025-03-02-ABC34343. Can you find out what's the current status? Regards, Jane`

### Testing Flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`
