#!/usr/bin/env bash
# set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

ADK=$(dirname "$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")")
export PYTHONPATH=$PYTHONPATH:$ADK:$ADK/src 

for python_tool in alert_helpdesk.py check_support_system.py echo_message.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${python_tool} -r ${SCRIPT_DIR}/tools/requirements.txt
done


# import inform agent agent
for agent in schedule_inform_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done

for flow_tool in alert_helpdesk_flow.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# import schedule alert agent
for agent in schedule_alert_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
