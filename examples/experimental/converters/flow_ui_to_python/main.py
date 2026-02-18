"""
JSON Flow Model to Python Code Converter - CLI Entry Point

This module provides the command-line interface for converting JSON Flow models 
to equivalent Python code using the wxO ADK Flow programming model.

Usage:
    python main.py -f input.json -o output.py [-n new_name] [-d "New Display Name"]

Options:
    -f, --file              Path to input JSON file
    -o, --output            Path to output Python file
    -n, --name              Rename the top-level flow (must be a valid Python identifier)
    -d, --display-name      Set a new display name for the top-level flow
    -v, --verbose           Enable verbose output
    --validate-only         Only validate the JSON model without generating code
    --no-helper-functions   Don't include helper functions in the generated code
    --remove-tool-uuid      Remove the tool UUID from the generated code
    --debug                 Enable debug output for troubleshooting
    -V, --version           Show version information and exit
"""

import argparse
import sys

from flow_model_converter import convert


# Version information
__version__ = "1.0.0"


def print_version():
    """Print version information."""
    print(f"JSON Flow Model to Python Code Converter v{__version__}")
    print("Copyright (c) IBM Corporation")
    print("Licensed under the Apache License, Version 2.0")


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
        help="Path to input JSON file"
    )
    parser.add_argument(
        "-o", "--output", 
        required=False, 
        help="Path to output Python file"
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
        help="Remove the tool UUID from the generated code"
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
    parser.add_argument(
        "--no-helper-functions", 
        action="store_true",
        help="Don't include helper functions in the generated code"
    )
    
    args = parser.parse_args()
    
    # Handle version flag
    if args.version:
        print_version()
        return 0
    
    # Check for required file argument
    if not args.file:
        parser.error("the following arguments are required: -f/--file")
        return 1
    
    # Call the converter with parsed arguments
    return convert(
        json_file=args.file,
        output_file=args.output,
        flow_name=args.name,
        display_name=args.display_name,
        remove_tool_uuid=args.remove_tool_uuid,
        include_helpers=not args.no_helper_functions,
        verbose=args.verbose,
        debug=args.debug,
        validate_only=args.validate_only
    )


if __name__ == "__main__":
    sys.exit(main() or 0)
