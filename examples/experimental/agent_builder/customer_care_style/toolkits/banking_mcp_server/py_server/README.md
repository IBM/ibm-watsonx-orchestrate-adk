# CustomerCare MCP Server - Python Implementation

A Python implementation of the CustomerCare MCP Server, providing identical functionality to the TypeScript version in `ts_server/`.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the server
uv run customercare-server
```

The server will start on `http://localhost:3004` by default.

## Configuration

Copy `.env.example` to `.env` in the repository root and configure the required environment variables.

## Documentation

See the main [README](../README.md) and [docs/](../docs/) for complete documentation on:

- Architecture and patterns
- Tool implementation
- Testing with the agent runtime
