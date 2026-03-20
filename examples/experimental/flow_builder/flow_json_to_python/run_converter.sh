#!/bin/bash
# Script to run the flow converter with the local source code
# This ensures that changes to src/ are used instead of the installed package

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the workspace root (4 levels up from this script)
WORKSPACE_ROOT="$( cd "$SCRIPT_DIR/../../../.." && pwd )"

# Set PYTHONPATH to use local source
export PYTHONPATH="$WORKSPACE_ROOT/src:$PYTHONPATH"

# Run the converter with all passed arguments
cd "$SCRIPT_DIR"
python main.py "$@"

# Made with Bob
