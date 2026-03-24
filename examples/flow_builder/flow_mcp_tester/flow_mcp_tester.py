"""
Interactive Test Program for FlowMCPClient

This example demonstrates how to use the FlowMCPClient to connect to an MCP server,
list available flow tools, and interactively inspect or call them.

Usage:
    # First, activate your environment
    orchestrate env activate <env_name>
    
    # Then run the example
    python examples/flow_builder/flow_via_mcp/flow_mcp_tester.py

Note:
    This example uses instantiate_client() which reads authentication from your
    active orchestrate environment configuration. Make sure you have activated
    an environment using 'orchestrate env activate' before running this example.
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm

# Add the src directory to the path so we can import the client
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from ibm_watsonx_orchestrate.client.tools.flow_mcp_client import FlowMCPClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client

console = Console()


def mcp_to_dict(obj):
    """Convert MCP objects to JSON-serializable dictionaries."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {k: mcp_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [mcp_to_dict(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # Convert object with attributes to dict
        return {k: mcp_to_dict(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    else:
        return str(obj)


def display_tool_schema(tool):
    """Display the tool's input and output schema in a formatted way."""
    console.print("\n[bold cyan]Tool Specification:[/bold cyan]")
    
    # Tool name and description
    tool_name = tool.name if hasattr(tool, 'name') else tool.get('name', 'Unknown')
    tool_desc = tool.description if hasattr(tool, 'description') else tool.get('description', 'No description')
    
    console.print(Panel(f"[bold]{tool_name}[/bold]\n{tool_desc}", title="Tool Info", border_style="cyan"))
    
    # Input schema
    if hasattr(tool, 'inputSchema'):
        input_schema = tool.inputSchema
    elif isinstance(tool, dict) and 'inputSchema' in tool:
        input_schema = tool['inputSchema']
    else:
        input_schema = None
    
    if input_schema:
        console.print("\n[bold green]Input Schema:[/bold green]")
        schema_json = json.dumps(input_schema, indent=2)
        syntax = Syntax(schema_json, "json", theme="monokai", line_numbers=True)
        console.print(syntax)
    
    # Output schema (if available)
    output_schema = None
    if hasattr(tool, 'outputSchema'):
        output_schema = tool.outputSchema
    elif isinstance(tool, dict) and 'outputSchema' in tool:
        output_schema = tool['outputSchema']
    
    if output_schema:
        console.print("\n[bold yellow]Output Schema:[/bold yellow]")
        schema_json = json.dumps(output_schema, indent=2)
        syntax = Syntax(schema_json, "json", theme="monokai", line_numbers=True)
        console.print(syntax)


async def call_tool_interactive(client, tool):
    """Interactively call a tool by prompting for arguments."""
    tool_name = tool.name if hasattr(tool, 'name') else tool.get('name', 'Unknown')
    
    console.print(f"\n[bold cyan]Calling tool: {tool_name}[/bold cyan]")
    
    # Get input schema
    if hasattr(tool, 'inputSchema'):
        input_schema = tool.inputSchema
    elif isinstance(tool, dict) and 'inputSchema' in tool:
        input_schema = tool['inputSchema']
    else:
        input_schema = {}
    
    # Show required and optional parameters
    properties = input_schema.get('properties', {})
    required = input_schema.get('required', [])
    
    if properties:
        console.print("\n[bold]Parameters:[/bold]")
        for param_name, param_info in properties.items():
            param_type = param_info.get('type', 'any')
            param_desc = param_info.get('description', 'No description')
            is_required = param_name in required
            req_label = "[red]*required[/red]" if is_required else "[dim]optional[/dim]"
            console.print(f"  • {param_name} ({param_type}) {req_label}")
            console.print(f"    {param_desc}")
    
    # Prompt for arguments as JSON
    console.print("\n[bold]Enter arguments as JSON (or press Enter for empty object):[/bold]")
    console.print("[dim]Example: {\"instance_id\": \"flow-123\", \"name\": \"my_flow\"}[/dim]")
    
    args_input = Prompt.ask("Arguments", default="{}")
    
    try:
        arguments = json.loads(args_input)
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON: {e}[/red]")
        return
    
    # Call the tool
    try:
        console.print(f"\n[yellow]Calling {tool_name}...[/yellow]")
        
        # Use specific client methods for known tools instead of generic _call_tool
        if tool_name == "list_flows":
            mcp_result = await client.list_flows(**arguments)
        elif tool_name == "cancel_flow":
            mcp_result = await client.cancel_flow(**arguments)
        elif tool_name == "replay_flow_pending_elicitation":
            mcp_result = await client.replay_flow_pending_elicitation(**arguments)
        elif tool_name == "submit_flow_elicitation":
            mcp_result = await client.submit_flow_elicitation(**arguments)
        elif tool_name.startswith("query_flow__"):
            # Extract flow name from tool name (query_flow__<flow_name>)
            flow_name = tool_name.replace("query_flow__", "")
            instance_id = arguments.get("instance_id")
            if not instance_id:
                raise ValueError("instance_id is required for query_flow")
            mcp_result = await client.query_flow(flow_name, instance_id)
        elif tool_name.startswith("run_flow__") and not tool_name.startswith("run_flow_async__"):
            # Extract flow name from tool name (run_flow__<flow_name>)
            flow_name = tool_name.replace("run_flow__", "")
            # Separate _context from other arguments if present
            context = arguments.pop("_context", None)
            mcp_result = await client.run_flow(flow_name, arguments, context)
        elif tool_name.startswith("run_flow_async__"):
            # Extract flow name from tool name (run_flow_async__<flow_name>)
            flow_name = tool_name.replace("run_flow_async__", "")
            # Separate _context from other arguments if present
            context = arguments.pop("_context", None)
            mcp_result = await client.arun_flow(flow_name, arguments, context)
        else:
            # Fall back to generic _call_tool for other tools
            mcp_result = await client._call_tool(tool_name, arguments)
        
        console.print("\n[bold green]✓ Tool call successful![/bold green]")
        
        # Extract data from MCP response
        # Prioritize structuredContent, fall back to content
        result = None
        if hasattr(mcp_result, 'structuredContent') and mcp_result.structuredContent is not None:
            result = mcp_result.structuredContent
            console.print(f"[dim]Using structuredContent[/dim]")
        elif hasattr(mcp_result, 'content') and mcp_result.content:
            result = mcp_result.content
            console.print(f"[dim]Using content array[/dim]")
        else:
            result = mcp_result
            console.print(f"[dim]Using raw result[/dim]")
        
        # Show debug info about result type
        console.print(f"[dim]Result type: {type(result).__name__}[/dim]")
        if isinstance(result, (list, dict)):
            if isinstance(result, list):
                console.print(f"[dim]List length: {len(result)}[/dim]")
            elif isinstance(result, dict):
                console.print(f"[dim]Dict keys: {list(result.keys())}[/dim]")
        elif isinstance(result, str):
            console.print(f"[dim]String length: {len(result)}[/dim]")
        
        console.print("\n[bold]Result:[/bold]")
        
        # Format result - special handling for lists of objects
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
            # Display as a table for list of objects
            console.print(f"\n[cyan]Found {len(result)} item(s)[/cyan]\n")
            
            # Create table with common keys
            all_keys = set()
            for item in result:
                all_keys.update(item.keys())
            
            # Prioritize certain keys for flow results
            priority_keys = ['instance_id', 'name', 'state', 'created_at', 'updated_at']
            sorted_keys = [k for k in priority_keys if k in all_keys]
            sorted_keys.extend([k for k in sorted(all_keys) if k not in priority_keys])
            
            # Limit columns for readability
            display_keys = sorted_keys[:6]  # Show first 6 columns
            
            table = Table(show_header=True, header_style="bold magenta", show_lines=True)
            table.add_column("#", style="bold blue", width=4, justify="right")
            
            for key in display_keys:
                table.add_column(key, style="cyan")
            
            for i, item in enumerate(result, 1):
                row_values = [str(i)]
                for key in display_keys:
                    value = item.get(key, '')
                    # Truncate long values
                    str_value = str(value)
                    if len(str_value) > 50:
                        str_value = str_value[:47] + "..."
                    row_values.append(str_value)
                table.add_row(*row_values)
            
            console.print(table)
            
            # Also show full JSON for detailed inspection
            if Confirm.ask("\n[dim]Show full JSON details?[/dim]", default=False):
                result_dict = mcp_to_dict(result)
                result_json = json.dumps(result_dict, indent=2)
                syntax = Syntax(result_json, "json", theme="monokai", line_numbers=True)
                console.print("\n[bold]Full JSON:[/bold]")
                console.print(syntax)
        elif isinstance(result, (dict, list)):
            # Display as JSON for dicts or simple lists
            result_dict = mcp_to_dict(result)
            result_json = json.dumps(result_dict, indent=2)
            syntax = Syntax(result_json, "json", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            # For other types, try to convert and display
            try:
                result_dict = mcp_to_dict(result)
                result_json = json.dumps(result_dict, indent=2)
                syntax = Syntax(result_json, "json", theme="monokai", line_numbers=True)
                console.print(syntax)
            except:
                console.print(result)
            
    except Exception as e:
        console.print(f"\n[red]✗ Tool call failed: {type(e).__name__}[/red]")
        console.print(f"[red]{str(e)}[/red]")


async def interactive_tool_menu(client, tools):
    """Display interactive menu for tool selection and actions."""
    while True:
        console.print("\n" + "=" * 60)
        console.print("[bold cyan]Select a tool to interact with:[/bold cyan]")
        console.print("=" * 60)
        
        # Create a table for tools
        table = Table(
            show_header=True,
            header_style="bold magenta",
            show_lines=True
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
            
            # Truncate long descriptions
            if len(tool_desc) > 80:
                tool_desc = tool_desc[:77] + "..."
            
            table.add_row(str(i), tool_name, tool_desc)
        
        console.print(table)
        console.print("\n[dim]Enter tool number, 'q' to quit, or 'r' to refresh tool list[/dim]")
        
        choice = Prompt.ask("Your choice", default="q")
        
        if choice.lower() == 'q':
            console.print("\n[yellow]Exiting...[/yellow]")
            break
        elif choice.lower() == 'r':
            console.print("\n[yellow]Refreshing tool list...[/yellow]")
            return 'refresh'
        
        try:
            tool_index = int(choice) - 1
            if 0 <= tool_index < len(tools):
                selected_tool = tools[tool_index]
                
                # Show action menu for selected tool
                while True:
                    console.print("\n" + "-" * 60)
                    tool_name = selected_tool.name if hasattr(selected_tool, 'name') else selected_tool.get('name', 'Unknown')
                    console.print(f"[bold cyan]Selected Tool: {tool_name}[/bold cyan]")
                    console.print("-" * 60)
                    console.print("\n[bold]Actions:[/bold]")
                    console.print("  1. Show tool specification")
                    console.print("  2. Call tool")
                    console.print("  3. Back to tool list")
                    
                    action = Prompt.ask("Choose action", choices=["1", "2", "3"], default="3")
                    
                    if action == "1":
                        display_tool_schema(selected_tool)
                    elif action == "2":
                        await call_tool_interactive(client, selected_tool)
                    elif action == "3":
                        break
            else:
                console.print(f"[red]✗ Invalid tool number. Please enter 1-{len(tools)}[/red]")
        except ValueError:
            console.print("[red]✗ Invalid input. Please enter a number, 'q', or 'r'[/red]")
    
    return 'quit'


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
            
            while True:
                # List available tools
                print("Listing available flow tools...")
                tools = await client.list_tools()
                
                if tools:
                    console.print(f"\n[green]✓ Found {len(tools)} tools[/green]\n")
                    
                    # Enter interactive menu
                    result = await interactive_tool_menu(client, tools)
                    
                    if result == 'quit':
                        break
                    # If result is 'refresh', loop continues to refresh tool list
                else:
                    console.print("\n[yellow]⚠ No tools found on the MCP server[/yellow]")
                    break
            
            console.print("\n[green]✓ Session completed![/green]")
            
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
    Main entry point for the interactive test program.
    Connects to Flow MCP server, lists available tools, and provides
    an interactive menu to inspect tool specifications or call them.
    """
    print("\n" + "=" * 60)
    print("FlowMCPClient Interactive Tester")
    print("=" * 60)
    
    # Run the async test to list tools
    asyncio.run(list_flow_tools())


if __name__ == "__main__":
    main()
