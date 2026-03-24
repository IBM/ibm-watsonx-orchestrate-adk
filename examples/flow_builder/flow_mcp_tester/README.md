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
   pip install ibm-watsonx-orchestrate[mcp]
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

- **No Elicitation Support**: The tester does not currently support interactive elicitation (human-in-the-loop) flows. Flows that require user input will pause and wait, but the tester cannot respond to elicitation requests.
- **Synchronous Only**: The tester runs synchronously and cannot handle concurrent operations
- **Basic Error Handling**: Complex error scenarios may not be fully handled

## Configuration

### Environment File

Create a `.env` file in this directory with your configuration:

```bash
# Example .env file
WXO_BASE_URL=https://your-server.com
WXO_API_KEY=your-api-key
```

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
pip install ibm-watsonx-orchestrate[mcp]
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

- [Flow MCP Architecture](../../../docs/flow-mcp.md)
- [FlowMCPClient API](../../../src/ibm_watsonx_orchestrate/client/tools/flow_mcp_client.py)