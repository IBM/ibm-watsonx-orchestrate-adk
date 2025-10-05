#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
AGENTS_DIR="${SCRIPT_DIR}/agents"

# Import the agent using orchestrate CLI
echo "Importing the agent..."
orchestrate agents import -f "${AGENTS_DIR}/currency_agent.yaml"

# Import the supervisor agent
echo "Adding currency conversion to the customer care agent..."
orchestrate agents import -f "${AGENTS_DIR}/customer_care_agent_v2.yaml"

# Made with Bob
