### Use Flow agent with structured `docext` node from WxO Chat

This example demonstrates document extraction with structured output, including table extraction capabilities.

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh`
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `document_extractor_agent`


### Testing Flow programmatically

1. Run the script `examples/flow_builder/text_extraction/upload_document.sh -f <ABSOLUTE PATH TO YOUR DOCUMENT YOU WANT TO TEST WITH THE FLOW>` and you will receive an url
2. Set `PYTHONPATH=<ADK>/src:<ADK>`  where `<ADK>` is the directory where you downloaded the ADK.
3. Run `python3 main.py "<your URL goes here>"`

### Key Differences from Classic Document Extractor

- Uses `document_extractor_with_tables` tool for enhanced structured extraction
- Supports table extraction and structured data output
- **Extraction Method**: Structured document extraction is selected when the `field_extraction_method` is set to `layout` in the document extractor node. If not specified, it defaults to `classic` extraction method.
