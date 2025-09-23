#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for flow_tool in hello_message_script_flow.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# import hello message agent
for agent in hello_message_script_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done