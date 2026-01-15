#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for tool in crm_tool.py payment_tool.py knowledge_base_tool.py system_diag_tool.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${tool} 
done

# import swarm agents
for agent in billing_agent.yaml fallback_agent.yaml technical_agent.yaml triage_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done

for flow_tool in triage_issue_flow.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# import top level customer service agent
for agent in customer_service_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
