#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for openapi_tool in get-healthcare-providers.yml; do
  orchestrate tools import -k openapi -f ${SCRIPT_DIR}/tools/${openapi_tool} -r ${SCRIPT_DIR}/tools/requirements.txt;
done

for agent in healthcare_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done


