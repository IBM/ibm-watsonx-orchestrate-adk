#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PID_FILE="${SCRIPT_DIR}/server.pid"

# Check if PID file exists
if [ ! -f "${PID_FILE}" ]; then
    echo "Error: PID file not found at ${PID_FILE}"
    echo "Server may not be running or was started without creating a PID file."
    exit 1
fi

# Read PIDs from the PID file
read SERVER_PID NGROK_PID < "${PID_FILE}"

echo "Stopping server (PID: ${SERVER_PID}) and ngrok (PID: ${NGROK_PID})..."

# Kill the processes
kill ${SERVER_PID} ${NGROK_PID} 2>/dev/null || true

# Check if processes are still running
if ps -p ${SERVER_PID} > /dev/null 2>&1; then
    echo "Warning: Server process (PID: ${SERVER_PID}) is still running. Trying with SIGKILL..."
    kill -9 ${SERVER_PID} 2>/dev/null || true
fi

if ps -p ${NGROK_PID} > /dev/null 2>&1; then
    echo "Warning: ngrok process (PID: ${NGROK_PID}) is still running. Trying with SIGKILL..."
    kill -9 ${NGROK_PID} 2>/dev/null || true
fi

# Remove the PID file
rm -f "${PID_FILE}"

echo "Server and ngrok stopped successfully."

# Made with Bob
