# Document Extractor Node 

## Using Flow Agent with `docext` Node from WxO Chat

1. Ensure your ADK runtime environment is activated before testing this example.
2. Run `import-all.sh` to import the necessary flows and agents.
3. Launch the Chat UI with `orchestrate chat start`.
4. Select the `document_extractor_agent` from the available agents.
5. Type a request such as "extract entities from a document". The agent will prompt you to upload the document.


## Testing Flow Programmatically

### Step 1: Upload Your Document

Run the upload script to get a document reference URL:

```sh
examples/flow_builder/text_extraction/upload_document.sh -f <ABSOLUTE_PATH_TO_YOUR_DOCUMENT>
```

**Tip:** You can assign the output to an environment variable for easier use:

```sh
docref=$(examples/flow_builder/text_extraction/upload_document.sh -f PATH/TO/YOUR/DOCUMENT.pdf)
```

### Step 2: Set Python Path

Set the `PYTHONPATH` environment variable to include the ADK source directory:

```sh
export PYTHONPATH=<ADK>/src:<ADK>
```

Replace `<ADK>` with the directory where you downloaded the ADK.

### Step 3: Run the Main Script

Execute the main.py script with the document reference:

```sh
python examples/flow_builder/text_extraction/main.py $docref
```
