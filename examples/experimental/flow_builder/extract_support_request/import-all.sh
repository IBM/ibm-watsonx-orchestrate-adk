#!/usr/bin/env bash
# set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

ADK=$(dirname "$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")")
export PYTHONPATH=$PYTHONPATH:$ADK:$ADK/src 

for python_tool in  email_helpdesk.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${python_tool} -r ${SCRIPT_DIR}/tools/requirements.txt
done

for flow_tool in extract_support_info.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# import hello message agent
for agent in ticket_processing_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
