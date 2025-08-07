import asyncio
import logging
import sys
import json
from pathlib import Path

from examples.flow_builder.text_extraction.tools.text_extraction_flow import build_docproc_flow

logger = logging.getLogger(__name__)


def on_flow_end(result):
    """
    Callback function to be called when the flow is completed.
    """
    print(f"Custom Handler: flow `{flow_run.name}` completed with result: {result}")


def on_flow_error(error):
    """
    Callback function to be called when the flow fails.
    """
    print(f"Custom Handler: flow `{flow_run.name}` failed: {error}")


async def main(doc_ref: str, kvp_schema_path):
    '''A function demonstrating how to build a flow and save it to a file.'''
    my_flow_definition = await build_docproc_flow().compile_deploy()
    global flow_name
    flow_name = my_flow_definition.flow.spec.display_name
    generated_folder = f"{Path(__file__).resolve().parent}/generated"
    my_flow_definition.dump_spec(f"{generated_folder}/docproc_flow_spec.json")

    with open(kvp_schema_path, 'r') as file:
        # Load the JSON data from the file into a Python dictionary
        schema_json = json.load(file)

    global flow_run
    flow_run = await my_flow_definition.invoke(
        {
          "document_ref": doc_ref, 
          "language": "en",
          "kvp_schemas": [ schema_json ]
        }, 
        on_flow_end_handler=on_flow_end, on_flow_error_handler=on_flow_error, debug=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        logger.error(f"Usage: {sys.argv[0]} file_store_path kvp_schema_path")
    else:
        asyncio.run(main(sys.argv[1], sys.argv[2]))
