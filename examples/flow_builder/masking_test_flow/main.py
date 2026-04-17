"""
Main entry point for testing the masking test flow locally.
"""

from tools.masking_test_flow import build_masking_test_flow
import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

flow_run = None

doc_ref= None

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

async def main():
    '''A function demonstrating how to build a flow and save it to a file.'''
    my_flow_definition = await build_masking_test_flow().compile_deploy()
    generated_folder = f"{Path(__file__).resolve().parent}/generated"
    my_flow_definition.dump_spec(f"{generated_folder}/masking_test_flow.json")
    # global flow_run
    # flow_run = await my_flow_definition.invoke({}, on_flow_end_handler=on_flow_end, on_flow_error_handler=on_flow_error, debug=True)

if __name__ == "__main__":
    asyncio.run(main())
