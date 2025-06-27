#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for openapi_tool in cat-facts.openapi.yml dog-facts.openapi.yml; do
  orchestrate tools import -k openapi -f ${SCRIPT_DIR}/tools/${openapi_tool};
done

for flow_tool in get_pet_facts.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# import pet agent
for agent in pet_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
