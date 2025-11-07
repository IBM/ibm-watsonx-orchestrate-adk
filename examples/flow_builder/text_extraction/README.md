# Document Processing Node with Text Extraction Task

## Using Flow Agent with `docproc` Node from WxO Chat

1. Ensure your ADK runtime environment is activated before testing this example.
2. Run `import-all.sh` to import the necessary flows and agents.
3. Launch the Chat UI with `orchestrate chat start`.
4. Select the `text_extraction_agent` from the available agents.
5. Type a request such as "extract text from a document with language English". The agent will prompt you to upload the document.

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

The output will be a document reference URL that you can use to download the text extraction results.

## Field Extraction Using a KVP Schema

You can use the same main.py program to send a `kvp_schema` parameter to the text extraction node. When using a KVP schema, the output will include extracted fields in addition to the extracted text.

### Steps:

1. Upload your document using `upload_document.sh` (see instructions above).

2. Run the extraction with a KVP schema:

   ```sh
   python examples/flow_builder/text_extraction/main.py $docref \
          examples/flow_builder/text_extraction/basic_kvp_schema_sample.json
   ```

   The output will be a document reference URL containing both the extracted text and structured field data.

For more details about KVP schemas and configuration options, see the comments in `tools/text_extraction_kvps_flow.py`.
