import asyncio
import logging
from pathlib import Path

from examples.flow_builder.get_insurance_rate.tools.get_insurance_rate import build_get_insurance_rate

logger = logging.getLogger(__name__)

flow_run = None

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
    my_flow_definition = await build_get_insurance_rate().compile_deploy()
    # my_flow_definition = build_get_insurance_rate().compile()

    current_folder = f"{Path(__file__).resolve().parent}"
    generated_folder = f"{current_folder}/generated"
    my_flow_definition.dump_spec(f"{generated_folder}/get_insurance_rate.json")
    
    global flow_run
    flow_run = await my_flow_definition.invoke({"grade": "B",
                                                "loan_amount": 300000},
                                               on_flow_end_handler=on_flow_end,
                                               on_flow_error_handler=on_flow_error,
                                               debug=True)

if __name__ == "__main__":
    asyncio.run(main())
