import asyncio
import logging
from pathlib import Path

from examples.flow_builder.triage_workflow_agent_swarm.tools.triage_issue_flow import build_triage_issue_flow

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
    my_flow_definition = await build_triage_issue_flow().compile_deploy()
    generated_folder = f"{Path(__file__).resolve().parent}/generated"
    my_flow_definition.dump_spec(f"{generated_folder}/build_triage_issue_flow.json")
    
    global flow_run
    # As the Flow Client API currently does not yet support HITL (Flow itself does), one must provide the customer id or the billing_agent will ask for one.
    # flow_run = await my_flow_definition.invoke({"original_issue": "What is my current subscription status? my customer id is ABC123"}, on_flow_end_handler=on_flow_end, on_flow_error_handler=on_flow_error, debug=True)
    flow_run = await my_flow_definition.invoke({"original_issue": "I want to remove my subscription? my customer id is ABC123"}, on_flow_end_handler=on_flow_end, on_flow_error_handler=on_flow_error, debug=True)

if __name__ == "__main__":
    asyncio.run(main())
