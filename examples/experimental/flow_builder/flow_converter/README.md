# Flow Converter - From Flow JSON to Flow Python - User Guide

A tool to convert IBM watsonx Orchestrate flow definitions (JSON) into Python code.

## Important Note on Code Format

The converted Python code follows a **standardized format** and will likely not match the original hand-crafted Python code if the flow originated from a hand-crafted Python definition. However, since the code is now in plain-text Python, you can use standard diff-merge capabilities in VSCode or other IDEs to spot the differences between the generated code and your original implementation.

**Recommended Workflow:**
1. Use the generated code as a **new baseline** for your Python code
2. Compare it with your original hand-crafted version using IDE diff-merge tools
3. Identify and preserve any customizations or optimizations from your original code
4. Subsequent conversions will follow the same standardized format, making future diff-merges much easier

This approach ensures consistency across conversions and simplifies maintenance over time.

## Quick Start

### Prerequisites

1. Python 3.10 or higher

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

**Step 1: Activate your wxO environment**

Before running the tool, you need to activate the wxO environment that contains the flow you want to convert:

```bash
wxo environment activate <environment-name>
```

**Step 2: Run the converter in Interactive Mode (Recommended):**

```bash
python main.py
```

The tool will:
1. Connect to your active wxO environment
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
Original flow (ZIP):     output/triage_issue_flow_original.zip
============================================================
```

### Non-Interactive Mode (Command-Line)

You can convert a JSON file directly without interactive prompts by providing the `-f` or `--file` argument:

**Basic Usage:**

```bash
python main.py -f input.json
```

This will:
- Read the flow definition from `input.json`
- Generate Python code in the `output/` directory (default)
- Create `<flow_name>_generated.py` and `<flow_name>.json` files

**Common Options:**

```bash
# Specify output directory
python main.py -f input.json -o my_output/

# Rename the flow (must be a valid Python identifier)
python main.py -f input.json -n my_custom_flow

# Set a custom display name (can be any string)
python main.py -f input.json -d "My Custom Flow"

# Remove tool UUIDs to make the flow portable across tenants
python main.py -f input.json --remove-tool-uuid

# Enable verbose output for detailed progress information
python main.py -f input.json -v

# Combine multiple options
python main.py -f input.json -o my_output/ -n my_flow -d "My Flow" --remove-tool-uuid -v
```

**Additional Options:**

```bash
# Validate JSON without generating code
python main.py -f input.json --validate-only

# Enable debug output for troubleshooting
python main.py -f input.json --debug

# Show version information
python main.py --version

# Show help with all available options
python main.py --help
```

**Example: Converting a specific flow file**

```bash
# Convert the date/time example flow
python main.py -f output/user_flow_application_form_date_time.json -o output -v

# Output:
# Output directory: output
# Python output: output/user_flow_application_form_date_time_generated.py
# JSON output: output/user_flow_application_form_date_time.json
# Copied JSON file to: output/user_flow_application_form_date_time.json
#
# ============================================================
# Conversion completed successfully!
# ============================================================
# Flow model (JSON):       output/user_flow_application_form_date_time.json
# Generated code (Python): output/user_flow_application_form_date_time_generated.py
# ============================================================
```

**Note:** When using non-interactive mode with a JSON file, the tool will attempt to find a matching flow in your active wxO environment to export the original ZIP package. If found, it will also create a `<flow_name>_original.zip` file in the output directory.

## Output Files

The tool generates files in the `output/` directory:

1. **`<flow_name>.json`** - The flow definition in JSON format
2. **`<flow_name>_generated.py`** - The Python code
3. **`<flow_name>_original.zip`** - The original flow package (when using interactive mode or when the flow is found in wxO environment)

The ZIP file contains the complete flow package including all dependencies and connections, which can be imported back into wxO if needed.

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

**"Validation error for UserNodeSpec" or changes to source code not taking effect:**

If you're developing and making changes to the source code in `src/`, you may encounter validation errors or find that your changes aren't being used. This happens because Python uses the installed package from `site-packages` instead of your local source code.

**Solution 1: Use the provided shell script (Recommended)**
```bash
cd examples/experimental/flow_builder/flow_json_to_python
./run_converter.sh -f /path/to/your/file.json -o output -v
```

The `run_converter.sh` script automatically sets `PYTHONPATH` to use your local source code.

**Solution 2: Set PYTHONPATH manually**
```bash
cd examples/experimental/flow_builder/flow_json_to_python
PYTHONPATH=/path/to/flow-converter/src:$PYTHONPATH python main.py -f input.json -o output -v
```

**Solution 3: Reinstall in editable mode**
```bash
cd /path/to/flow-converter
pip install -e .
```

After reinstalling in editable mode, your changes to `src/` will be immediately reflected without needing to set PYTHONPATH.

## Getting Help

```bash
# Show all options
python main.py --help

# Show version
python main.py --version
```
