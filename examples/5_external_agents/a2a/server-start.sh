#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVER_DIR="${SCRIPT_DIR}/server"
AGENTS_DIR="${SCRIPT_DIR}/../../agents"

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "Error: ngrok is not installed. Please install it from https://ngrok.com/download"
    exit 1
fi

# Start the a2a server in the background
echo "Starting the a2a server..."
cd "${SERVER_DIR}" && uv run app --host 0.0.0.0 --port 10000 &
SERVER_PID=$!

# Give the server time to start
echo "Waiting for server to start..."
sleep 5

# Start ngrok to expose the server
echo "Starting ngrok to expose the server..."
ngrok http 10000 --log=stdout &
NGROK_PID=$!

# Wait for ngrok to generate a public URL
echo "Waiting for ngrok to generate a public URL..."
sleep 5

# Get the ngrok public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | grep -o 'https://[^"]*')

if [ -z "$NGROK_URL" ]; then
    echo "Error: Failed to get ngrok URL. Please check if ngrok is running properly."
    kill $SERVER_PID
    kill $NGROK_PID
    exit 1
fi

echo "ngrok URL: $NGROK_URL"
echo "Server is running with PID: $SERVER_PID"
echo "ngrok is running with PID: $NGROK_PID"
echo "To stop the server and ngrok, run: kill $SERVER_PID $NGROK_PID"

# Export the NGROK_URL so it can be used by other scripts
export NGROK_URL

# Create a PID file to store the server and ngrok PIDs
PID_FILE="${SCRIPT_DIR}/server.pid"
echo "${SERVER_PID} ${NGROK_PID}" > "${PID_FILE}"

echo "PID file created at: ${PID_FILE}"
echo "To stop the server and ngrok, run: ./stop-server.sh"

# Create the external agent definition
cat > "${AGENTS_DIR}/currency_agent.yaml" << EOL
spec_version: v1
kind: external
name: currency_agent
title: Currency Conversion Agent
description: An external agent that provides currency conversion services using the A2A protocol
provider: external_chat/A2A/0.2.1
api_url: ${NGROK_URL}
auth_scheme: NONE
chat_params:
  agentProtocol: A2A
  stream: false
EOL

echo "Created external agent definition at ${AGENTS_DIR}/currency_agent.yaml"

# Made with Bob
