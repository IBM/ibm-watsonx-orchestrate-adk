# Flow MCP Interactive Tester

An interactive testing tool for the Flow MCP (Model Context Protocol) client. This tool allows you to explore and test MCP flow tools through an interactive command-line interface.

## Overview

The Flow MCP Interactive Tester (`flow_mcp_tester.py`) provides a user-friendly way to:
- List all available MCP flow tools
- View tool specifications (input/output schemas)
- Call tools interactively with custom arguments
- View results in formatted tables or JSON

## Prerequisites

1. **Install MCP SDK**:
   ```bash
   pip install mcp
   ```

2. **Activate Environment**:
   ```bash
   orchestrate env activate <env_name>
   ```

## Usage

### Running the Tester

```bash
cd examples/flow_builder/flow_mcp_tester
python flow_mcp_tester.py
```

### Interactive Menu

1. **Tool List**: View all available MCP tools in a formatted table
2. **Select Tool**: Choose a tool by number to interact with it
3. **Tool Actions**:
   - **Show specification**: View detailed input/output schemas
   - **Call tool**: Execute the tool with custom JSON arguments
   - **Back**: Return to tool list

### Example Workflow

```
1. Start the tester
2. Select a tool (e.g., "list_flows")
3. Choose "Call tool"
4. Enter arguments as JSON: {}
5. View results in formatted table or JSON
```

## Features

### Smart Result Display

- **Lists of objects**: Displayed as formatted tables with key columns
- **Dictionaries**: Displayed as syntax-highlighted JSON
- **Debug information**: Shows result type, length, and data source

### Tool Routing

The tester intelligently routes known tools to specific client methods:
- `list_flows` → `client.list_flows()`
- `run_flow__*` → `client.run_flow()`
- `run_flow_async__*` → `client.arun_flow()`
- `query_flow__*` → `client.query_flow()`
- `cancel_flow` → `client.cancel_flow()`
- `replay_flow_pending_elicitation` → `client.replay_flow_pending_elicitation()`
- `submit_flow_elicitation` → `client.submit_flow_elicitation()`

### Debug Mode

The tester shows debug information for each tool call:
- Result type (list, dict, str, etc.)
- Data source (structuredContent, content array, or raw result)
- List length or dictionary keys
- JSON parsing status

## Limitations

### Elicitation Handling with Interactive Menus

The tester **does support elicitation** (user input requests from flows), but there's an important limitation when using the interactive menu:

**The Issue:**
- The interactive menu uses synchronous prompts (`Prompt.ask()`) that block the terminal
- When an elicitation callback fires while you're at a menu prompt, the output is buffered
- You won't see the elicitation request until after you respond to the current prompt

**Workarounds:**
1. **Recommended**: After calling a flow tool, **wait at the result screen** instead of navigating menus
   - Elicitation requests will display immediately with a 🔔 bell notification
   - You can respond to the elicitation
   - The flow will continue and subsequent elicitations will appear

2. **Listen for the bell**: A terminal bell (`\a`) sounds when elicitation arrives
   - Even if you don't see the output, you'll hear/see the alert
   - Press Enter at the current prompt to see the buffered elicitation

3. **Check debug logs**: Elicitation callbacks are logged with timestamps
   - Look for `DEBUG [timestamp]: Elicitation callback invoked` messages
   - This confirms if callbacks are being received

**Example - Correct Usage:**
```
1. Select tool: run_flow__my_flow
2. Choose "Call tool"
3. Enter arguments: {"input": "data"}
4. [WAIT HERE - Don't navigate menus]
5. 🔔 Elicitation request appears
6. Respond to elicitation
7. Flow continues, more elicitations may appear
```

**Example - Problematic Usage:**
```
1. Call flow tool
2. Immediately press 'r' to refresh tool list  ← DON'T DO THIS
3. While at "Your choice:" prompt, elicitation fires
4. Output is buffered, you don't see it
5. You're confused why nothing is happening
```

### Other Limitations

- **Concurrent Operations**: The tester cannot handle multiple flows running simultaneously
- **Basic Error Handling**: Complex error scenarios may not be fully handled
- **Terminal-Based UI**: For better concurrent elicitation handling, consider a web-based UI

## Configuration

### Environment File

Create a `.env` file in this directory with your configuration.

### VS Code Debugging

A debug configuration is available in `.vscode/launch.json`:
- **Name**: "Debug Flow MCP Interactive Tester"
- **Loads**: Environment variables from `.env`
- **Terminal**: Integrated terminal for interactive prompts

## Files

- `flow_mcp_tester.py`: Main interactive tester program
- `.env`: Environment configuration (create this file)
- `README.md`: This file

## Troubleshooting

### "MCP SDK not installed"
```bash
pip install mcp
```

### "Connection Error"
- Ensure the MCP server is running
- Check your environment configuration
- Verify network connectivity

### "Tool call failed"
- Check the tool arguments format (must be valid JSON)
- Verify required parameters are provided
- Review error message for specific issues

## Related Documentation

- [Flow MCP Support - Public Preview](https://developer.watson-orchestrate.ibm.com/tools/flows/mcp_workflows)
