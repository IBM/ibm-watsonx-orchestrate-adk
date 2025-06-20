#!/usr/bin/env bash

orchestrate env activate local


SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CURRENT_WD=$(dirname "$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")")
export PYTHONPATH=$PYTHONPATH:$CURRENT_WD:$CURRENT_WD/src

for tool in get_facts_about_numbers.py get_request_status.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${tool};
done

for flow_tool in get_number_random_fact_flow.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# import pet agent
for agent in get_number_fact_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
