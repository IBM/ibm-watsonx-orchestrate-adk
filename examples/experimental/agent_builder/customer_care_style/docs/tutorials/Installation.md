# Installation Guide

This guide will help you set up and run the banking agent demonstration using watsonx orchestrate developer edition.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Node.js** (v20 or higher)
   - Download from [nodejs.org](https://nodejs.org/)
   - Verify installation: `node --version`

2. **npm** (comes with Node.js)
   - Verify installation: `npm --version`

3. **watsonx orchestrate CLI**
   - Install the watsonx orchestrate CLI following the official documentation
   - Verify installation: `orchestrate --version`

4. **Docker** (for watsonx orchestrate developer edition)
   - Download from [docker.com](https://www.docker.com/)
   - Verify installation: `docker --version`

## Installation Steps

### 1. Navigate to the Example

Navigate to the example directory:

```bash
cd examples/experimental/agent_builder/customer_care_style
```

### 2. Set Up watsonx orchestrate Developer Edition

Initialize and start the watsonx orchestrate developer edition server:

```bash
# Start the developer edition server
orchestrate server start
```

This will start a local instance of watsonx orchestrate that you can use for development and testing. The server will initialize and start all necessary containers on `http://localhost:4321`.

**Note**: If you need additional features like Langfuse observability, you can enable them with flags:
```bash
# Start with Langfuse support
orchestrate server start --langfuse

# Start with custom .env file
orchestrate server start -e /path/to/.env
```

### 3. Start the Developer Edition Chat UI

After the server is running, start the chat UI:

```bash
# Start the chat UI
orchestrate chat start
```

This will start the watsonx orchestrate UI on `http://localhost:3000`. The UI will automatically open in your browser.

### 4. Install the MCP Server Dependencies

The MCP server is a Node.js/TypeScript application located in the `toolkits/banking_mcp_server/` directory.

```bash
# Navigate to the MCP server directory
cd toolkits/banking_mcp_server

# Install Node.js dependencies
npm install

# Build the TypeScript project
npm run build
```

### 5. Verify Installation

Test that the components are installed correctly:

```bash
# Test the MCP server (from the toolkits/banking_mcp_server directory)
npm run dev

# In another terminal, verify orchestrate CLI
orchestrate --version
```

## Running the Banking Agent Demo

This example includes a complete banking agent that demonstrates the customer care agent style.

### 1. Start the MCP Server

From the `toolkits/banking_mcp_server/` directory:

```bash
# Start the MCP server in development mode
npm run dev
```

The server will start on `http://localhost:3004` by default. You should see:
```
Banking MCP server listening on port 3004
```

### 2. Start the Chat UI (if not already running)

If you haven't already started the chat UI, run:

```bash
orchestrate chat start
```

The UI will be available at `http://localhost:3000`.

### 3. Import the Agent into Developer Edition

From the example directory, run the import script:

```bash
# Make sure you're in the example directory
cd examples/experimental/agent_builder/customer_care_style

# Run the import script
./import-all.sh
```

This script will:
- Activate the local developer edition environment
- Import the banking toolkit
- Import the banking agent

### 4. Get the Web Chat Embed Code

The easiest way to get the correct configuration for your web chat is to use the CLI:

```bash
# Get the embed code for the banking agent
orchestrate channels webchat embed -a banking_agent
```

This command will output the complete embed code with all the correct IDs pre-filled. Copy the configuration values from the output.

Alternatively, you can retrieve the IDs manually:
- Use `orchestrate agents list` to get the `agentId` and `agentEnvironmentId`
- The `orchestrationID` is your instance ID (available in the developer edition)

### 5. Configure the Web Chat Interface

Open `sample_webchat.html` in a text editor and update the configuration:

1. **Update the customer context** (lines 25-26):
   ```javascript
   telephoneNumber: "+15551234567", // Use a phone number from customerDatabase.ts
   jwtToken: "<token>" // Any non-blank value works for the demo
   ```

2. **Update the IDs** (lines 42, 50-51) using the values from the embed code:
   ```javascript
   orchestrationID: "<instance id>",  // Replace with your orchestrationID
   agentId: "<agent-id>",             // Replace with your agentId
   agentEnvironmentId: "<env id>",    // Replace with your agentEnvironmentId
   ```

### 6. Open the Web Chat

Open `sample_webchat.html` in your web browser. The chat interface will connect to your local developer edition instance.

### 7. Interact with the Agent

Try these example interactions in the web chat:

- **Check balance**: "What's my checking account balance?"
- **Transfer money**: "I want to transfer $100 from checking to savings"
- **Get statement**: "Show me my recent transactions"
- **Talk to agent**: "I need to speak with someone"

### Using Different Customer Profiles

To test with different customer profiles, update the `telephoneNumber` in `sample_webchat.html`:

- **CUST001** (+15551234567): Personal banking + Credit card
- **CUST002** (+15559876543): Personal banking + Mortgage
- **CUST003** (+15555555555): All products (personal banking, mortgage, credit card)
- **CUST004** (+15551111111): Personal banking only

Each customer profile demonstrates how the agent personalizes available tools based on the customer's products. You can find these profiles in `toolkits/banking_mcp_server/src/customerDatabase.ts`.

## Development Workflow

### Running in Development Mode

For active development, use these commands:

```bash
# From toolkits/banking_mcp_server/
# Run MCP server with auto-reload
npm run dev

# Run linting
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run prettier:fix
```

### Making Changes to the Agent

After modifying agent configurations or tools:

```bash
# Re-import the agent from the example directory
cd examples/experimental/agent_builder/customer_care_style
./import-all.sh

# Refresh the web chat in your browser
```

### Building for Production

```bash
# Build the TypeScript project
npm run build

# Run the built version
npm start
```

## Configuration

### MCP Server Configuration

The MCP server can be configured via environment variables:

- `PORT`: Server port (default: 3004)
- Additional configuration can be added to `toolkits/banking_mcp_server/src/index.ts`

### Agent Configuration

Agent configuration is defined in YAML files:

- **Agent definition**: `agents/banking_agent.yaml`
- **Toolkit definition**: `toolkits/banking_mcp_server.yaml`

### Web Chat Configuration

The web chat interface is configured in `sample_webchat.html`:

- **Customer context**: Phone number and JWT token (lines 25-26)
- **Instance IDs**: orchestrationID, agentId, agentEnvironmentId (lines 42, 50-51)
- **Host URL**: Points to local developer edition (line 43)

## Troubleshooting

### MCP Server Won't Start

- Ensure port 3004 is not in use: `lsof -i :3004` (macOS/Linux) or `netstat -ano | findstr :3004` (Windows)
- Check Node.js version: `node --version` (should be v20+)
- Reinstall dependencies: `rm -rf node_modules package-lock.json && npm install`

### Developer Edition Not Running

- Check if Docker is running: `docker ps`
- Check server status: `orchestrate server status`
- Restart developer edition: `orchestrate server stop` then `orchestrate server start`
- Check logs: `orchestrate server logs`

### Import Script Fails

- Ensure developer edition is running: `orchestrate server status`
- Verify you're in the correct directory when running `./import-all.sh`
- Check that the MCP server is running before importing

### Web Chat Won't Connect

- Verify developer edition is running on port 3000
- Check the `orchestrationID`, `agentId`, and `agentEnvironmentId` in `sample_webchat.html`
- Open browser console (F12) to see connection errors
- Ensure the MCP server is running and accessible

### Agent Not Responding

- Verify the MCP server is running on the correct port
- Check the URL in `toolkits/banking_mcp_server.yaml` matches your server configuration
- Ensure no firewall is blocking localhost connections
- Check browser console for errors

## Next Steps

- Read the [Getting Started Guide](GettingStarted.md) to understand the architecture
- Explore the [pattern documentation](../) to learn about different patterns
- Try [extending the server](ExtendingTheServer.md) with your own tools
- Learn how to [create new MCP servers](CreatingNewServers.md) from scratch

## Additional Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Watson Orchestrate Documentation](https://www.ibm.com/docs/en/watsonx/watson-orchestrate)