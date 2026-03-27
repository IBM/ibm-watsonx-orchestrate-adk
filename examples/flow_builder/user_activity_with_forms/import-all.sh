#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Import both flow tools from separate files
for flow_tool in user_flow_forms.py user_flow_forms_date_time.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool}
done

# Import the agent that uses both tools
for agent in user_activity_agent_forms.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done