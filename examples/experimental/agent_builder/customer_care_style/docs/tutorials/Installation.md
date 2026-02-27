# Installation Guide

This guide will help you set up the CustomerCare repository and run the banking agent demonstration.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

### For TypeScript Server

1. **Node.js** (v20 or higher)
   - Download from [nodejs.org](https://nodejs.org/)
   - Verify installation: `node --version`

2. **npm** (comes with Node.js)
   - Verify installation: `npm --version`

### For Python Server

1. **Python** (v3.11 or higher)
   - Download from [python.org](https://python.org/)
   - Verify installation: `python3 --version`

2. **UV** (Python package installer)
   - Install UV by following the instructions at [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/)
   - For macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - For Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - Verify installation: `uv --version`

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd CustomerCare
```

### 2. Install the MCP Server Dependencies

The MCP servers are available in both TypeScript (`toolkits/banking_mcp_server/ts_server/`) and Python (`toolkits/banking_mcp_server/py_server/`). Both implementations provide identical functionality - choose the one that best fits your technology stack.

#### TypeScript Server

```bash
# Navigate to TypeScript server directory
cd ts_server

# Install Node.js dependencies
npm install

# Build the TypeScript project
npm run build
```

#### Python Server

```bash
# Navigate to Python server directory
cd py_server

# Install dependencies using uv
uv sync --extra dev
```

### 3. Install the Customer Care Agent Runtime

The agent runtime is a Python-based text UI (TUI) that allows you to interact with the MCP server.

```bash
# Navigate to the agent runtime directory
cd agent_runtime

# Install the CCA tool using UV
uv tool install cca-0.5.5-py3-none-any.whl --python 3.13
```

### 4. Verify Installation

Test that all components are installed correctly:

```bash
# Test the TypeScript MCP server (from ts_server directory)
cd ts_server
npm run dev

# Or test the Python MCP server (from py_server directory)
cd py_server
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
customercare-server
# Or alternatively: uvicorn src.main:app --host 0.0.0.0 --port 3004

# In another terminal, test the CCA tool
uvx cca --help
```

## Running the Banking Agent Demo

The repository includes a complete banking agent example that demonstrates the customer care agent style.

### 1. Start the MCP Server

Choose either the TypeScript or Python server:

**TypeScript:**

```bash
cd ts_server
npm run dev
```

**Python:**

```bash
cd py_server

# Run using the CLI entry point
uv run customercare-server

# Or run directly with uvicorn
uv run uvicorn src.main:app --host 0.0.0.0 --port 3004
```

The Python server starts on `http://localhost:3004` by default. You should see:

```
CustomerCare Banking MCP server listening on 0.0.0.0:3004
```

### 2. Run the Banking Agent

In a new terminal window, navigate to the banking agent example:

```bash
cd agent_runtime/examples/banking_agent
```

Copy the .env.example file to .env and update your WO_INSTANCE and WO_API_KEY to point to a watsonx Orchestrate
SaaS service instance url and api key (can be a trail).

```bash
LANGFUSE_ORG_ID=orchestrate
LANGFUSE_ORG_NAME=WatsonOrchestrate
LANGFUSE_PROJECT_ID=orchestrate
LANGFUSE_PROJECT_NAME=WatsonOrchestrateDCA

LANGFUSE_HOST=http://localhost:3010
LANGFUSE_PUBLIC_KEY=pk-lf-7417757e-d6df-421b-957e-683b76acb5df
LANGFUSE_PRIVATE_KEY=sk-lf-7bc4da63-7b2b-40c0-b5eb-1e0cf64f9af2
LANGFUSE_SECRET_KEY=sk-lf-7bc4da63-7b2b-40c0-b5eb-1e0cf64f9af2

LANGFUSE_EMAIL=orchestrate@ibm.com
LANGFUSE_USERNAME=orchestrate
LANGFUSE_PASSWORD=

WO_INSTANCE=https://api.dl.watson-orchestrate.ibm.com/instances/<my-service-instance-id>
WO_API_KEY=<my api key>
```

# Run the agent with the provided start script
```bash
./start.sh
```

Alternatively, you can run it manually with:

```bash
uvx cca chat \
  -a agents/banking_agent.yaml \
  -t toolkits/banking_mcp_server.yaml \
  -c sample_context/CUST001.yaml \
  -e ../../.env
```

### 3. Interact with the Agent

Once the agent starts, you'll see a text-based interface. Try these example interactions:

- **Check balance**: "What's my checking account balance?"
- **Transfer money**: "I want to transfer $100 from checking to savings"
- **Get statement**: "Show me my recent transactions"
- **Talk to agent**: "I need to speak with someone"

### Using Different Customer Profiles

The example includes multiple customer profiles with different product combinations:

```bash
# Customer with personal banking only
uvx cca chat -a agents/banking_agent.yaml \
  -t toolkits/banking_mcp_server.yaml \
  -c sample_context/CUST001.yaml

# Customer with personal banking and mortgage
uvx cca chat -a agents/banking_agent.yaml \
  -t toolkits/banking_mcp_server.yaml \
  -c sample_context/CUST002.yaml

# Customer with all products
uvx cca chat -a agents/banking_agent.yaml \
  -t toolkits/banking_mcp_server.yaml \
  -c sample_context/CUST003.yaml
```

Each customer profile demonstrates how the agent personalizes available tools based on the customer's products.

## Development Workflow

### Running in Development Mode

**TypeScript Server:**

```bash
cd ts_server

# Run MCP server with auto-reload
npm run dev

# Run linting
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run prettier:fix
```

**Python Server:**

```bash
cd py_server

# Run with auto-reload
uv run uvicorn src.main:app --host 0.0.0.0 --port 3004 --reload

# Run tests
uv run pytest

# Run linting
uv run ruff check src/

# Fix linting issues
uv run ruff check --fix src/

# Format code
uv run ruff format src/

# Type checking
uv run mypy src/
```

### Building for Production

**TypeScript:**

```bash
cd ts_server
npm run build
npm start
```

**Python:**

```bash
cd py_server

# Run the server
uv run customercare-server

# Or with uvicorn directly
uv run uvicorn src.main:app --host 0.0.0.0 --port 3004
```

## Configuration

### MCP Server Configuration

The MCP server can be configured via environment variables:

- `PORT`: Server port (default: 3004)
- Additional configuration can be added to `toolkits/banking_mcp_server/ts_server/src/index.ts` (TypeScript) or `toolkits/banking_mcp_server/py_server/src/main.py` (Python)

### Agent Configuration

Agent configuration is defined in YAML files:

- **Agent definition**: `agent_runtime/examples/banking_agent/agents/banking_agent.yaml`
- **Toolkit definition**: `agent_runtime/examples/banking_agent/toolkits/banking_mcp_server.yaml`
- **Context/credentials**: `agent_runtime/examples/banking_agent/sample_context/*.yaml`

## Troubleshooting

### MCP Server Won't Start

- Ensure port 3004 is not in use: `lsof -i :3004` (macOS/Linux) or `netstat -ano | findstr :3004` (Windows)
- For TypeScript: Check Node.js version: `node --version` (should be v20+)
- For TypeScript: Reinstall dependencies: `cd ts_server && rm -rf node_modules package-lock.json && npm install`
- For Python: Check Python version: `python3 --version` (should be v3.11+)
- For Python: Reinstall dependencies: `cd py_server && uv sync --extra dev`

### CCA Tool Not Found

- Ensure UV is installed: `uv --version`
- Reinstall the CCA tool: `uv tool install --force agent_runtime/cca-0.5.5-py3-none-any.whl`
- Check UV tool path is in your PATH

### Connection Errors

- Verify the MCP server is running on the correct port
- Check the URL in `toolkits/banking_mcp_server.yaml` matches your server configuration
- Ensure no firewall is blocking localhost connections

## Next Steps

- Read the [Getting Started Guide](GettingStarted.md) to understand the architecture
- Explore the [pattern documentation](../) to learn about different patterns
- Try [extending the server](ExtendingTheServer.md) with your own tools
- Learn how to [create new MCP servers](CreatingNewServers.md) from scratch

## Additional Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Watson Orchestrate Documentation](https://www.ibm.com/docs/en/watsonx/watson-orchestrate)
- [Repository Documentation](../docs/)