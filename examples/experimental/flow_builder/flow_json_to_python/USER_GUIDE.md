# Flow JSON to Python Converter - User Guide

A tool to convert IBM watsonx Orchestrate flow definitions (JSON) into Python code.

## Quick Start

### Prerequisites

1. Python 3.8 or higher

2. Clone the repository with the flow-converter branch:
   ```bash
   git clone -b flow-converter https://github.ibm.com/WatsonOrchestrate/wxo-clients.git
   cd wxo-clients
   ```

3. Install the SDK from the cloned repository:
   ```bash
   pip install -e .
   ```

4. Navigate to the converter tool:
   ```bash
   cd examples/experimental/flow_builder/flow_json_to_python
   ```

### Running the Tool

**Interactive Mode (Recommended):**

```bash
python main.py
```

The tool will:
1. Connect to your wxO environment
2. Show a list of available flow tools
3. Let you select which flow to convert
4. Ask if you want to customize conversion options
5. Generate the Python code

**Example Session:**

```
Fetching flow tools from wxO environment...

Found 3 flow tool(s):

#    Name                 Display Name         Description                                                 
-----------------------------------------------------------------------------------------------------------
1    get_pet_facts        get_pet_facts        Based on the request, we will return the list of facts ab...
2    triage_issue_flow    triage_issue_flow    Flow to triage customer issue                               
3    user_flow_example    user_flow_example    Example user flow.                                          

Select a flow tool (1-3), or 'q' to quit: 2

Exporting flow tool 'triage_issue_flow'...
Successfully exported flow definition to temporary file

============================================================
Conversion Options
============================================================
Flow name:        triage_issue_flow
Display name:     triage_issue_flow
Remove tool UUID: No
============================================================

Do you want to update these settings? (y/N): N

============================================================
Conversion completed successfully!
============================================================
Flow model (JSON):       output/triage_issue_flow.json
Generated code (Python): output/triage_issue_flow_generated.py
============================================================
```

### Command-Line Mode

Convert a JSON file directly:

```bash
python main.py -f input.json
```

**Common Options:**

```bash
# Specify output directory
python main.py -f input.json -o my_output/

# Rename the flow
python main.py -f input.json -n my_custom_flow

# Set display name
python main.py -f input.json -d "My Custom Flow"

# Remove tool UUIDs
python main.py -f input.json --remove-tool-uuid

# Verbose output
python main.py -f input.json -v
```

## Output Files

The tool generates two files in the `output/` directory:

1. **`<flow_name>.json`** - The flow definition in JSON format
2. **`<flow_name>_generated.py`** - The Python code

## Generated Code Structure

The Python file includes:

- **Imports** - All necessary SDK imports
- **Schema Classes** - Pydantic models for data validation
- **Flow Function** - Main function decorated with `@flow`
- **Helper Functions** - Utilities for creating nodes (optional)

## Using the Generated Code

```python
from output.triage_issue_flow_generated import build_triage_issue_flow_flow
from ibm_watsonx_orchestrate.flow_builder.flows import Flow

# Create and build the flow
flow = Flow()
flow = build_triage_issue_flow_flow(flow)

# Compile and use
compiled_flow = flow.compile()
```

## Common Issues

**"Module not found" error:**
- Install the SDK: `pip install ibm-watsonx-orchestrate`

**"Connection error":**
- Check your wxO environment configuration
- Verify your credentials

**"Invalid JSON":**
- Ensure the JSON file is valid
- Use `--debug` flag for details: `python main.py -f input.json --debug`

## Getting Help

```bash
# Show all options
python main.py --help

# Show version
python main.py --version
```

For more technical details, see `IMPLEMENTATION.md`.