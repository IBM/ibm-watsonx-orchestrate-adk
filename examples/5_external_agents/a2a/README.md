# A2A Agent Integration with watsonx Orchestrate

This directory contains scripts and templates for setting up an A2A (Agent-to-Agent) server and integrating it with watsonx Orchestrate as an external agent, along with a supervisor agent that delegates to it.

## Overview

The A2A server in this example is a currency conversion agent built with LangGraph that provides real-time currency exchange information. The `import-all.sh` script automates the process of:

1. Starting the A2A server locally
2. Exposing it publicly using ngrok
3. Creating an external agent definition that connects to the exposed server
4. Creating a supervisor agent that delegates to the currency agent
5. Importing both agents into watsonx Orchestrate

## Prerequisites

- [ngrok](https://ngrok.com/download) installed on your system
- Python 3.12 or higher
- [UV](https://docs.astral.sh/uv/) package manager
- Access to an LLM API (Google Gemini or custom LLM)
- watsonx Orchestrate CLI installed and configured

## Usage

1. Make sure you have the prerequisites installed
2. Run the import-all.sh script:

```bash
cd examples/8_connect_external_agents/a2a
./import-all.sh
```

3. Follow the prompts to configure your LLM choice:
   - For Google Gemini, you'll need to provide your Google API Key
   - For a custom LLM, you'll need to provide the LLM URL and model name

4. The script will:
   - Start the A2A server in the background
   - Expose it via ngrok
   - Create an external agent definition with the ngrok URL
   - Create a supervisor agent that delegates to the currency agent
   - Import both agents into watsonx Orchestrate

5. The terminal will display:
   - The ngrok URL
   - The PIDs of the server and ngrok processes
   - Instructions for stopping the server and ngrok

## Files

- `import-all.sh`: Main script for setting up and importing the A2A agent
- `agents/currency_agent_template.yaml`: Template for the external agent definition
- `agents/a2a_example_supervisor.yaml`: Definition for the supervisor agent that delegates to the currency agent
- `server/`: Directory containing the A2A server implementation

## How It Works

The A2A server implements the [A2A protocol](https://a2a-protocol.org/) which enables standardized interaction between agents. The server exposes endpoints that conform to the A2A specification, allowing it to be integrated with watsonx Orchestrate as an external agent.

When imported into watsonx Orchestrate, the currency agent appears as an external agent that can be used for currency conversion tasks. The agent maintains conversational context and can request additional information when needed.

The supervisor agent (a2a_example_supervisor) is a native agent that delegates all user requests to the currency agent. This demonstrates how to create a chain of agents where one agent can invoke another to handle specialized tasks.

## Troubleshooting

- If the script fails to get the ngrok URL, make sure ngrok is running properly and that port 4040 is accessible
- If the server fails to start, check the .env file in the server directory for proper configuration
- If the agent import fails, check that the watsonx Orchestrate CLI is properly configured

## Cleanup

To stop the server and ngrok, press Ctrl+C in the terminal where the script is running, or use the kill command with the PIDs displayed by the script:

```bash
kill <SERVER_PID> <NGROK_PID>
```

To remove the agent from watsonx Orchestrate:

```bash
orchestrate agents remove -n currency_agent -k external
orchestrate agents remove -n a2a_example_supervisor -k native
```