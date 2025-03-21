#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for python_tool in  find_user_id.py find_user_management_chain.py find_user_peers.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${python_tool} -r ${SCRIPT_DIR}/tools/requirements.txt
done

for openapi_tool in cat-facts.openapi.yml; do
  orchestrate tools import -k openapi -f ${SCRIPT_DIR}/tools/${openapi_tool} -r ${SCRIPT_DIR}/tools/requirements.txt
done

for agent in jokester_agent.yaml hr_agent.yaml manager_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done


