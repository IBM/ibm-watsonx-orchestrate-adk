#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
for flow_tool in  get_kvp_schemas_for_invoice.py get_kvp_schemas_for_utility_bill.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

for flow_tool in  document_processing_flow.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

for agent in document_processing_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done