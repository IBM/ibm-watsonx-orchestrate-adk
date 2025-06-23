#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for python_tool in auto_denial.py auto_approval.py require_manager_approval.py get_requests.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${python_tool}
done

for flow_tool in get_tuition_reimbursed.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool}
done

for agent in get_tuition_reimbursed_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
