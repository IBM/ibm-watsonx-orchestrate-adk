#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for flow_tool in  document_extractor_flow.py.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

for agent in document_extractor_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done