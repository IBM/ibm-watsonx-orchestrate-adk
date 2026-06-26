import asyncio
import logging
import sys
from pathlib import Path
from time import sleep

from examples.flow_builder.user_activity_with_forms.tools.user_flow_forms import build_user_form
from examples.flow_builder.user_activity_with_forms.tools.user_flow_forms_date_time import build_user_form_date_time
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.tools.tempus_client import TempusClient


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
    '''A function demonstrating how to build flows that contain forms and save them to files.'''
 
    # Build and save the original application form
    my_flow_definition = await build_user_form().compile_deploy()
    generated_folder = f"{Path(__file__).resolve().parent}/generated"
    my_flow_definition.dump_spec(f"{generated_folder}/flow_with_user_form.json")
    print(f"Generated: {generated_folder}/flow_with_user_form.json")
    
    # Build and save the date/time form
    my_flow_definition_date_time = await build_user_form_date_time().compile_deploy()
    my_flow_definition_date_time.dump_spec(f"{generated_folder}/flow_with_user_form_date_time.json")
    print(f"Generated: {generated_folder}/flow_with_user_form_date_time.json")
    
    # global flow_run
    # flow_run = await my_flow_definition.invoke({}, on_flow_end_handler=on_flow_end, on_flow_error_handler=on_flow_error, debug=True)
    """
    # Test the new TempusClient methods: abort_flow and delete_flow
    print("\n" + "="*60)
    print("Testing TempusClient methods: abort_flow() and delete_flow()")
    print("="*60)
    
    # Start a flow instance using invoke_events to get control
    print("\nStarting flow instance...", flush=True)
    global flow_run
    flow_run = None
    
    # Use invoke_events to get the flow_run object with instance ID
    async for event, run in my_flow_definition.invoke_events({}, debug=False):
        if not flow_run:
            flow_run = run
            print(f"Got flow_run object with instance ID: {flow_run.id}", flush=True)
            break  # Exit after getting the first event with instance ID
    
    if not flow_run or not flow_run.id:
        print("ERROR: Could not get flow instance ID", flush=True)
        return
    
    print(f"\nFlow instance started:", flush=True)
    print(f"  - Instance ID: {flow_run.id}", flush=True)
    print(f"  - Name: {flow_run.name}", flush=True)
    print(f"  - Status: {flow_run.status}", flush=True)
    
    # Initialize TempusClient
    tempus_client: TempusClient = instantiate_client(client=TempusClient)
    
    # Test 1: abort_flow()
    print(f"\n--- Testing abort_flow() ---", flush=True)
    print(f"Aborting flow instance: {flow_run.id}", flush=True)
    try:
        abort_result = tempus_client.abort_flow(flow_run.id)
        print(f"✓ abort_flow() succeeded", flush=True)
        print(f"  Result: {abort_result}", flush=True)
    except Exception as e:
        print(f"✗ abort_flow() failed: {str(e)}", flush=True)
    
    # Test 2: delete_flow() - Start a new flow instance, abort it, then delete it
    print(f"\n--- Testing delete_flow() ---", flush=True)
    print(f"Starting a new flow instance for delete test...", flush=True)
    
    flow_run2 = None
    async for event, run in my_flow_definition.invoke_events({}, debug=False):
        if not flow_run2:
            flow_run2 = run
            print(f"New flow instance created: {flow_run2.id}", flush=True)
            break
    if flow_run2 and flow_run2.id:
        # First abort the flow (required before delete)
        print(f"Aborting flow instance {flow_run2.id} before delete...", flush=True)
        try:
            abort_result2 = tempus_client.abort_flow(flow_run2.id)
            print(f"✓ Flow aborted successfully", flush=True)
        except Exception as e:
            print(f"✗ Abort failed: {str(e)}", flush=True)

        sleep(2)
        # Now delete the aborted flow
        print(f"Deleting aborted flow instance: {flow_run2.id}", flush=True)
        try:
            delete_result = tempus_client.delete_flow(flow_run2.id)
            print(f"✓ delete_flow() succeeded", flush=True)
            print(f"  Result: {delete_result}", flush=True)
        except Exception as e:
            print(f"✗ delete_flow() failed: {str(e)}", flush=True)
    else:
        print(f"✗ Could not create second flow instance for delete test", flush=True)
    
    print("\n" + "="*60, flush=True)
    print("Testing completed!", flush=True)
    print("="*60, flush=True)
    """

if __name__ == "__main__":
    asyncio.run(main())