"""
Example: Using FlowMCPClient with Elicitation Callback

This example demonstrates how to handle flow elicitation requests automatically
using a callback function. When a flow requires user input (e.g., form submission),
the callback will be invoked to handle the request.

Usage:
    # First, activate your environment
    orchestrate env activate <env_name>
    
    # Then run the example
    python examples/flow_builder/flow_mcp_tester/elicitation_example.py
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from ibm_watsonx_orchestrate.client.tools.flow_mcp_client import FlowMCPClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client

try:
    from mcp import types
except ImportError:
    print("MCP SDK not installed. Please install with: pip install ibm-watsonx-orchestrate[mcp]")
    sys.exit(1)


async def handle_flow_elicitation(
    context,  # Context parameter (not used in this example)
    params: types.ElicitRequestParams,
) -> types.ElicitResult | types.ErrorData:
    """
    Handle elicitation requests from flow execution.
    
    This callback is invoked when a flow requires user input during execution.
    For example, when a flow reaches a user input node with a form.
    
    Args:
        context: Request context from MCP
        params: Elicitation parameters including:
            - mode: The elicitation mode (e.g., "url", "form")
            - message: Description of what is being requested
            - elicitationId: Unique ID for this elicitation request
            - Additional mode-specific parameters
    
    Returns:
        ElicitResult with action and optional content, or ErrorData on error
    """
    print("\n" + "=" * 60)
    print("ELICITATION REQUEST RECEIVED")
    print("=" * 60)
    print(f"Mode: {params.mode}")
    print(f"Message: {params.message}")
    
    # Handle different elicitation modes
    if params.mode == "url":
        # URL mode - user needs to visit a URL
        url = getattr(params, "url", None)
        if url:
            print(f"URL: {url}")
            print("\nPlease visit the URL to complete the action.")
            
            # In a real application, you might:
            # 1. Open the URL in a browser
            # 2. Wait for user confirmation
            # 3. Return accept/decline based on user action
            
            response = input("\nDid you complete the action? (y/n): ").strip().lower()
            if response == 'y':
                return types.ElicitResult(action="accept")
            else:
                return types.ElicitResult(action="decline")
    
    elif params.mode == "form":
        # Form mode - user needs to fill out a form
        print("\nForm elicitation detected.")
        
        # In a real application, you would:
        # 1. Extract form schema from params
        # 2. Display form to user (CLI, GUI, web interface)
        # 3. Collect user input
        # 4. Return the form data
        
        # For this example, we'll simulate form submission
        print("Simulating form submission...")
        
        # Example form data structure
        form_data = {
            "field1": "example_value",
            "field2": "another_value"
        }
        
        # IMPORTANT: form_data must be a JSON string, not a dict
        import json
        return types.ElicitResult(
            action="accept",
            content={
                "form_data": json.dumps(form_data),
                "response_type": "form_operation",
                "form_operation": "submit"
            }
        )
    
    # Unsupported mode - return error
    return types.ErrorData(
        code=types.INVALID_REQUEST,
        message=f"Unsupported elicitation mode: {params.mode}"
    )


async def run_flow_with_elicitation():
    """
    Example of running a flow with automatic elicitation handling.
    """
    print("FlowMCPClient Elicitation Example")
    print("=" * 60)
    print()
    
    try:
        # Create client with elicitation callback
        print("Creating FlowMCPClient with elicitation callback...")
        
        # Use instantiate_client() to get authentication from active environment,
        # then set the elicitation callback before connecting
        client = instantiate_client(FlowMCPClient)
        client.set_elicitation_callback(handle_flow_elicitation)
        
        print(f"MCP Endpoint: {client.get_mcp_endpoint()}")
        print()
        
        async with client:
            print("✓ Connected to MCP server")
            print()
            
            # Example: Run a flow that requires user input
            # Replace with your actual flow name and arguments
            flow_name = "example_flow_with_user_input"
            flow_args = {
                "input_field": "test_value"
            }
            
            print(f"Running flow: {flow_name}")
            print(f"Arguments: {flow_args}")
            print()
            print("Note: If the flow requires user input, the elicitation callback")
            print("      will be invoked automatically.")
            print()
            
            # Run the flow - elicitations will be handled automatically
            result = await client.run_flow(flow_name, flow_args)
            
            print("\n" + "=" * 60)
            print("FLOW EXECUTION RESULT")
            print("=" * 60)
            print(f"Status: {result.get('status', {})}")
            if 'output' in result:
                print(f"Output: {result['output']}")
            print()
            
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    Main entry point for the elicitation example.
    """
    print("\n" + "=" * 60)
    print("FlowMCPClient Elicitation Callback Example")
    print("=" * 60)
    print()
    print("This example demonstrates automatic handling of flow elicitation")
    print("requests using a callback function.")
    print()
    
    asyncio.run(run_flow_with_elicitation())


if __name__ == "__main__":
    main()
