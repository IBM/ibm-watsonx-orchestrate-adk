import asyncio
import logging
from pathlib import Path

from examples.flow_builder.agent_scheduler.tools.agent_run import build_agent_run_flow
from ibm_watsonx_orchestrate.flow_builder.flows.flow import FlowRunStatus
from ibm_watsonx_orchestrate.flow_builder.types import FlowEventType

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
    my_flow_definition =  await build_agent_run_flow().compile_deploy()

    current_folder = f"{Path(__file__).resolve().parent}"
    generated_folder = f"{current_folder}/generated"
    my_flow_definition.dump_spec(f"{generated_folder}/agent_run_flow.json")

    
    global flow_run
    flow_run = await my_flow_definition.invoke({"agent_id": "pet_agent",
                                                "request": "tell me about dog"}, 
                                               on_flow_end_handler=on_flow_end, 
                                               on_flow_error_handler=on_flow_error, 
                                               debug=True)
    

if __name__ == "__main__":
    asyncio.run(main())
