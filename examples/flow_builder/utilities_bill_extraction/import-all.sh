#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for flow_tool in utilities_bill_extraction_flow.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

for agent in utilities_extraction_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done