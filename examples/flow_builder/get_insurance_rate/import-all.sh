#!/usr/bin/env bash
# set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

ADK=$(dirname "$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")")
export PYTHONPATH=$PYTHONPATH:$ADK:$ADK/src 

for flow_tool in get_insurance_rate.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# import hello message agent
for agent in insurance_assessment_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
