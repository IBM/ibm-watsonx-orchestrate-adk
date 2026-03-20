"""
Test program for FlowMCPClient

This example demonstrates how to use the FlowMCPClient to connect to an MCP server
and list available flow tools.

Usage:
    # First, activate your environment
    orchestrate env activate <env_name>
    
    # Then run the example
    python examples/flow_builder/flow_via_mcp/flow_mcp.py

Note:
    This example uses instantiate_client() which reads authentication from your
    active orchestrate environment configuration. Make sure you have activated
    an environment using 'orchestrate env activate' before running this example.
"""

import asyncio
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add the src directory to the path so we can import the client
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from ibm_watsonx_orchestrate.client.tools.flow_mcp_client import FlowMCPClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client

console = Console()


async def list_flow_tools():
    """
    Connect to the MCP server and list available flow tools.
    Uses instantiate_client() to get authentication from active environment.
    """
    print("Using authentication from active orchestrate environment")
    print("=" * 60)
    print()
    
    try:
        # Create the client using instantiate_client for proper authentication
        print("Creating FlowMCPClient with instantiate_client()...")
        client = instantiate_client(FlowMCPClient)
        
        print(f"MCP Endpoint: {client.get_mcp_endpoint()}")
        print()
        
        # Use async context manager to connect
        print("Connecting to MCP server...")
        async with client:
            print("✓ Connected successfully!")
            print()
            
            # List available tools
            print("Listing available flow tools...")
            tools = await client.list_tools()
            
            if tools:
                print(f"\n✓ Found {len(tools)} tools:\n")
                
                # Create a table for tools with row separators
                table = Table(
                    title="Available Flow Tools",
                    show_header=True,
                    header_style="bold magenta",
                    show_lines=True  # This adds lines between rows
                )
                table.add_column("#", style="bold blue", width=4, justify="right")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("Description", style="green")
                
                for i, tool in enumerate(tools, 1):
                    # Handle different tool object structures
                    if hasattr(tool, 'name'):
                        tool_name = tool.name
                        tool_desc = getattr(tool, 'description', 'No description')
                    elif isinstance(tool, dict):
                        tool_name = tool.get('name', 'Unknown')
                        tool_desc = tool.get('description', 'No description')
                    else:
                        tool_name = str(tool)
                        tool_desc = 'No description'
                    
                    table.add_row(str(i), tool_name, tool_desc)
                
                console.print(table)
            else:
                console.print("\n[yellow]⚠ No tools found on the MCP server[/yellow]")
            
            console.print("\n[green]✓ Test completed successfully![/green]")
            
    except ImportError as e:
        print(f"\n✗ Error: MCP SDK not installed")
        print(f"  {str(e)}")
        print("\nPlease install the MCP SDK:")
        print("  pip install mcp")
        sys.exit(1)
        
    except ConnectionError as e:
        print(f"\n✗ Connection Error: {str(e)}")
        print("\nMake sure the MCP server is running and accessible.")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}")
        print(f"  {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    Main entry point for the test program.
    Connects to Flow MCP server and lists available tools.
    """
    print("\n" + "=" * 60)
    print("FlowMCPClient Test Program")
    print("=" * 60)
    
    # Run the async test to list tools
    asyncio.run(list_flow_tools())


if __name__ == "__main__":
    main()

# Made with Bob
