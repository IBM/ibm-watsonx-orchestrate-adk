import asyncio
import logging
import sys
from pathlib import Path

from examples.flow_builder.parallel_flow.tools.parallel_flow import build_feature_delivery_flow


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
    '''A function demonstrating how to build a parallel flow and save it to a file.'''
    
    # Build and deploy the feature delivery workflow
    my_flow_definition = await build_feature_delivery_flow().compile_deploy()
    
    # Save the flow specification to a file
    generated_folder = f"{Path(__file__).resolve().parent}/generated"
    Path(generated_folder).mkdir(parents=True, exist_ok=True)
    my_flow_definition.dump_spec(f"{generated_folder}/feature_delivery_workflow.json")
    
    print("\n" + "="*80)
    print("Feature Delivery Workflow - Parallel Flow Example")
    print("="*80)
    
    # Test Case 1: Both design and architecture needed
    print("\n--- Test Case 1: Design and Architecture both needed ---")
    global flow_run
    flow_run = await my_flow_definition.invoke(
        {
            "feature_name": "User Authentication",
            "design_needed": True,
            "arch_needed": True
        },
        on_flow_end_handler=on_flow_end,
        on_flow_error_handler=on_flow_error,
        debug=True
    )
    
    # Wait a bit for the flow to complete
    await asyncio.sleep(2)
    
    # Test Case 2: Only design needed
    print("\n--- Test Case 2: Only Design needed ---")
    flow_run = await my_flow_definition.invoke(
        {
            "feature_name": "UI Redesign",
            "design_needed": True,
            "arch_needed": False
        },
        on_flow_end_handler=on_flow_end,
        on_flow_error_handler=on_flow_error,
        debug=True
    )
    
    # Wait a bit for the flow to complete
    await asyncio.sleep(2)
    
    # Test Case 3: Neither design nor architecture needed
    print("\n--- Test Case 3: Skip Phase 1 (no design or architecture) ---")
    flow_run = await my_flow_definition.invoke(
        {
            "feature_name": "Bug Fix",
            "design_needed": False,
            "arch_needed": False
        },
        on_flow_end_handler=on_flow_end,
        on_flow_error_handler=on_flow_error,
        debug=True
    )
    
    # Wait for completion
    await asyncio.sleep(2)
    
    print("\n" + "="*80)
    print("All test cases completed!")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
