#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

AGENT_NAME="channel_demo_agent"

# Step 1: Import the demo agent
echo "Importing agent..."
orchestrate agents import -f ${SCRIPT_DIR}/agents/channel_demo_agent.yaml

# Step 2: Import channel configurations
# Channels are linked to agents through agent environments (draft/live)
echo "Importing channels..."

orchestrate channels import --agent-name ${AGENT_NAME} --env draft \
  -f ${SCRIPT_DIR}/channels/twilio_whatsapp_example.yaml

orchestrate channels import --agent-name ${AGENT_NAME} --env draft \
  -f ${SCRIPT_DIR}/channels/twilio_sms_example.yaml

orchestrate channels import --agent-name ${AGENT_NAME} --env draft \
  -f ${SCRIPT_DIR}/channels/webchat_example.yaml

echo "Done! Agent '${AGENT_NAME}' and its channels are configured."