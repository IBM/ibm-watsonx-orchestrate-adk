#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Import Python tool (get_states_or_provinces)
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/get_states_or_provinces.py

# Import flow tool (user_activity_with_dynamic_forms_full)
for flow_tool in user_activity_with_dynamic_forms_full.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# Import agent
for agent in user_activity_agent_dynamic_forms.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
