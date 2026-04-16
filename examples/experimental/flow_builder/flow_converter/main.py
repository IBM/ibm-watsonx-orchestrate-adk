"""
JSON Flow Model to Python Code Converter - CLI Entry Point

This module provides the command-line interface for converting JSON Flow models
to equivalent Python code using the wxO ADK Flow programming model.

Usage:
    python main.py -f input.json -o output_dir [-n new_name] [-d "New Display Name"]
    python main.py -o output_dir  # Interactive mode: select from available flow tools
    python main.py  # Interactive mode with default output directory

Options:
    -f, --file              Path to input JSON file (if not provided, interactive mode)
    -o, --output-dir        Output directory for generated files (default: ./output)
    -n, --name              Rename the top-level flow (must be a valid Python identifier)
    -d, --display-name      Set a new display name for the top-level flow
    -v, --verbose           Enable verbose output
    --validate-only         Only validate the JSON model without generating code
    --remove-tool-uuid      Remove the tool UUID from the generated code to make the flow portable across tenants
    --debug                 Enable debug output for troubleshooting
    -V, --version           Show version information and exit
"""

import argparse
import sys
import tempfile
import zipfile
import json
import os
import shutil
from pathlib import Path

from flow_converter import convert


# Version information
__version__ = "1.0.0"


def print_version():
    """Print version information."""
    print(f"JSON Flow Model to Python Code Converter v{__version__}")
    print("Copyright (c) IBM Corporation")
    print("Licensed under the MIT License")


def select_flow_tool_interactive() -> tuple[str, str, dict]:
    """
    Interactive mode to select a flow tool from the wxO environment.
    
    Returns:
        Tuple of (tool_name, temp_json_file_path, interactive_options)
        where interactive_options is a dict with keys: flow_name, display_name, remove_tool_uuid
    """
    try:
        from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController, ToolKind
        from ibm_watsonx_orchestrate.client.utils import instantiate_client
        from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
    except ImportError as e:
        print(f"Error: Required wxO SDK modules not available: {e}", file=sys.stderr)
        print("Please ensure ibm-watsonx-orchestrate is installed", file=sys.stderr)
        sys.exit(1)
    
    print("Fetching flow tools from wxO environment...")
    
    # Get list of tools
    tools_controller = ToolsController()
    client = instantiate_client(ToolClient)
    all_tools = client.get()
    
    # Filter for flow tools only
    flow_tools = []
    for tool_spec in all_tools:
        if tool_spec.get("binding", {}).get("flow") is not None:
            flow_tools.append(tool_spec)
    
    if not flow_tools:
        print("No flow tools found in the current wxO environment.", file=sys.stderr)
        sys.exit(1)
    
    # Display available flow tools in a table format
    print(f"\nFound {len(flow_tools)} flow tool(s):\n")
    
    # Calculate column widths
    max_name_len = max(len(tool.get("name", "")) for tool in flow_tools)
    max_display_len = max(len(tool.get("display_name", "")) for tool in flow_tools)
    max_desc_len = 60  # Limit description length for readability
    
    # Ensure minimum widths
    name_width = max(max_name_len, 20)
    display_width = max(max_display_len, 20)
    
    # Print table header
    header = f"{'#':<4} {'Name':<{name_width}} {'Display Name':<{display_width}} {'Description':<{max_desc_len}}"
    print(header)
    print("-" * len(header))
    
    # Print table rows
    for idx, tool in enumerate(flow_tools, 1):
        name = tool.get("name", "Unknown")
        display_name = tool.get("display_name", "")
        description = tool.get("description", "")
        
        # Truncate description if too long
        if len(description) > max_desc_len:
            description = description[:max_desc_len-3] + "..."
        
        print(f"{idx:<4} {name:<{name_width}} {display_name:<{display_width}} {description:<{max_desc_len}}")
    
    print()
    
    # Get user selection
    while True:
        try:
            selection = input(f"Select a flow tool (1-{len(flow_tools)}), or 'q' to quit: ").strip()
            if selection.lower() == 'q':
                print("Cancelled.")
                sys.exit(0)
            
            idx = int(selection) - 1
            if 0 <= idx < len(flow_tools):
                selected_tool = flow_tools[idx]
                break
            else:
                print(f"Please enter a number between 1 and {len(flow_tools)}")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)
    
    tool_name = selected_tool.get("name")
    tool_display_name = selected_tool.get("display_name", "")
    tool_id = selected_tool.get("id")
    
    print(f"\nExporting flow tool '{tool_name}'...")
    
    # Export the tool to a temporary file
    try:
        # Download tool artifacts
        downloaded_bytes = client.download_tools_artifact(tool_id=tool_id)
        
        if not downloaded_bytes:
            print(f"Error: No artifacts found for tool '{tool_name}'", file=sys.stderr)
            sys.exit(1)
        
        # Extract JSON from the zip (downloaded_bytes is already a zip file)
        import io
        with zipfile.ZipFile(io.BytesIO(downloaded_bytes), "r") as zip_ref:
            # Look for flow.json or similar
            json_files = [f for f in zip_ref.namelist() if f.endswith('.json') and 'flow' in f.lower()]
            
            if not json_files:
                # Try any JSON file
                json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
            
            if not json_files:
                print(f"Error: No JSON file found in tool artifacts", file=sys.stderr)
                sys.exit(1)
            
            # Extract the first JSON file to a temp location
            json_content = zip_ref.read(json_files[0])
            
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            temp_file.write(json_content.decode('utf-8'))
            temp_file.close()
            
            print(f"Successfully exported flow definition to temporary file")
            
            # Show conversion options
            print("\n" + "="*60)
            print("Conversion Options")
            print("="*60)
            print(f"Flow name:        {tool_name}")
            print(f"Display name:     {tool_display_name if tool_display_name else '(none)'}")
            print(f"Remove tool UUID: No")
            print("="*60)
            
            # Ask if user wants to update settings
            update_settings = input("\nDo you want to update these settings? (y/N): ").strip().lower()
            
            new_flow_name = None
            new_display_name = None
            remove_tool_uuid = False
            
            if update_settings in ['y', 'yes']:
                print("\n" + "="*60)
                print("Update Conversion Options")
                print("="*60)
                
                # Get flow name
                print(f"\nCurrent flow name: {tool_name}")
                flow_name_input = input(f"Enter new flow name (press Enter to keep '{tool_name}'): ").strip()
                if flow_name_input:
                    new_flow_name = flow_name_input
                
                # Get display name
                print(f"\nCurrent display name: {tool_display_name if tool_display_name else '(none)'}")
                display_name_input = input(f"Enter new display name (press Enter to keep current): ").strip()
                if display_name_input:
                    new_display_name = display_name_input
                
                # Get remove tool UUID option
                print(f"\nCurrent remove tool UUID: No")
                remove_uuid_input = input("Remove tool UUID from generated code to make the flow portable across tenants? (y/N): ").strip().lower()
                remove_tool_uuid = remove_uuid_input in ['y', 'yes']
            
            interactive_options = {
                'flow_name': new_flow_name,
                'display_name': new_display_name,
                'remove_tool_uuid': remove_tool_uuid,
                'tool_name_for_export': tool_name  # Store tool name for zip export
            }
            
            print()
            return (tool_name, temp_file.name, interactive_options)
            
    except Exception as e:
        print(f"Error exporting tool: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    """
    Main function to handle command-line arguments and invoke the converter.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="Generate Python code from JSON Flow model",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-f", "--file",
        required=False,
        help="Path to input JSON file (if not provided, interactive mode to select from wxO environment)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        required=False,
        default="output",
        help="Output directory for generated files (default: ./output)"
    )
    parser.add_argument(
        "-n", "--name", 
        help="Rename the top-level flow (must be a valid Python identifier)"
    )
    parser.add_argument(
        "-d", "--display-name", 
        help="Set a new display name for the top-level flow (can be any string)"
    )
    parser.add_argument(
        "--remove-tool-uuid",
        action="store_true",
        help="Remove the tool UUID from the generated code to make the flow portable across tenants"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    parser.add_argument(
        "--validate-only", 
        action="store_true", 
        help="Only validate the JSON model without generating code"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug output for troubleshooting"
    )
    parser.add_argument(
        "-V", "--version",
        action="store_true",
        help="Show version information and exit"
    )
    
    args = parser.parse_args()
    
    # Handle version flag
    if args.version:
        print_version()
        return 0
    
    # Handle file input - either from file or interactive selection
    json_file = args.file
    cleanup_temp_file = False
    original_json_file = None
    interactive_options = {}
    tool_name_for_export = None  # Track tool name for zip export
    
    if not json_file:
        # Interactive mode: select from wxO environment
        if args.validate_only:
            print("Error: --validate-only requires -f/--file argument", file=sys.stderr)
            return 1
        
        try:
            tool_name, json_file, interactive_options = select_flow_tool_interactive()
            cleanup_temp_file = True
            tool_name_for_export = interactive_options.get('tool_name_for_export')
            
            # Override command-line args with interactive options if provided
            if interactive_options.get('flow_name'):
                args.name = interactive_options['flow_name']
            if interactive_options.get('display_name'):
                args.display_name = interactive_options['display_name']
            if interactive_options.get('remove_tool_uuid'):
                args.remove_tool_uuid = True
                
        except Exception as e:
            print(f"Error in interactive mode: {e}", file=sys.stderr)
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1
    else:
        # Store original JSON file path for copying later
        original_json_file = json_file
        
        # Try to find the tool name from the JSON file to enable zip export
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                flow_name_from_json = json_data.get('spec', {}).get('name', None)
                
                # Try to find this tool in wxO environment for zip export
                if flow_name_from_json:
                    try:
                        from ibm_watsonx_orchestrate.client.utils import instantiate_client
                        from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
                        
                        client = instantiate_client(ToolClient)
                        all_tools = client.get()
                        
                        # Look for a matching flow tool
                        for tool_spec in all_tools:
                            if (tool_spec.get("binding", {}).get("flow") is not None and
                                tool_spec.get("name") == flow_name_from_json):
                                tool_name_for_export = tool_spec.get("name")
                                if args.verbose:
                                    print(f"Found matching flow tool in wxO environment: {tool_name_for_export}")
                                break
                    except Exception:
                        # Silently ignore if we can't connect to wxO
                        pass
        except Exception:
            pass
    
    # Read the JSON to get the flow name
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            flow_name = json_data.get('spec', {}).get('name', 'flow')
    except Exception as e:
        print(f"Warning: Could not read flow name from JSON, using default: flow", file=sys.stderr)
        flow_name = "flow"
    
    # Create output directory
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine output filenames
    python_output = os.path.join(output_dir, f"{flow_name}_generated.py")
    json_output = os.path.join(output_dir, f"{flow_name}.json")
    
    if args.verbose:
        print(f"Output directory: {output_dir}")
        print(f"Python output: {python_output}")
        print(f"JSON output: {json_output}")
    
    try:
        # Call the converter with parsed arguments
        result = convert(
            json_file=json_file,
            output_file=python_output,
            flow_name=args.name,
            display_name=args.display_name,
            remove_tool_uuid=args.remove_tool_uuid,
            verbose=args.verbose,
            debug=args.debug,
            validate_only=args.validate_only
        )
        
        # Copy/save the JSON file to output directory
        if not args.validate_only:
            if original_json_file:
                # Copy from original location only if source and destination are different
                if os.path.abspath(original_json_file) != os.path.abspath(json_output):
                    shutil.copy2(original_json_file, json_output)
                    if args.verbose:
                        print(f"Copied JSON file to: {json_output}")
                else:
                    if args.verbose:
                        print(f"JSON file already at destination: {json_output}")
            else:
                # Copy from temp file (interactive mode)
                shutil.copy2(json_file, json_output)
                if args.verbose:
                    print(f"Saved JSON file to: {json_output}")
            
            # Export original flow as zip if from interactive mode
            if result == 0 and tool_name_for_export:
                try:
                    from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController
                    
                    zip_output = os.path.join(output_dir, f"{flow_name}_original.zip")
                    if args.verbose:
                        print(f"\nExporting original flow as zip to: {zip_output}")
                    
                    tools_controller = ToolsController()
                    tools_controller.export_tool(
                        name=tool_name_for_export,
                        output_path=zip_output
                    )
                    
                    if args.verbose:
                        print(f"Successfully exported original flow to: {zip_output}")
                except Exception as e:
                    print(f"Warning: Could not export original flow as zip: {e}", file=sys.stderr)
                    if args.debug:
                        import traceback
                        traceback.print_exc()
            
            # Print summary of generated files
            if result == 0:
                print("\n" + "="*60)
                print("Conversion completed successfully!")
                print("="*60)
                print(f"Flow model (JSON):       {json_output}")
                print(f"Generated code (Python): {python_output}")
                if tool_name_for_export:
                    zip_output = os.path.join(output_dir, f"{flow_name}_original.zip")
                    print(f"Original flow (ZIP):     {zip_output}")
                print("="*60)
        
        return result
    finally:
        # Clean up temporary file if created
        if cleanup_temp_file and json_file:
            try:
                os.unlink(json_file)
            except:
                pass


if __name__ == "__main__":
    sys.exit(main() or 0)
