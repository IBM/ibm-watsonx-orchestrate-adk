#!/usr/bin/env bash
set -x

# orchestrate env activate your_environment

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/genesys_tools.py -r ${SCRIPT_DIR}/tools/requirements.txt;

orchestrate agents import -f ${SCRIPT_DIR}/agents/channel_agent.yaml;

orchestrate channels import \
  --agent-name "channel_agent" \
  --env draft \
  -f ${SCRIPT_DIR}/channels/genesys_bot_connector_example.yaml;
