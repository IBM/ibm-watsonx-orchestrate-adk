### Use Flow agent with `docproc` node from WxO Chat

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `utilities_extraction_agent`
5. Type in something like `I want to extract fields from a document and language is en`. Then, the agent will promt you to upload the document

### Testing Flow programmatically

1. Run the script `examples/flow_builder/text_extraction/upload_document.sh -f <ABSOLUTE PATH TO YOUR DOCUMENT YOU WANT TO TEST WITH THE FLOW>` and you will receive an url
2. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
3. Run `python3 main.py "<your URL goes here>"`
