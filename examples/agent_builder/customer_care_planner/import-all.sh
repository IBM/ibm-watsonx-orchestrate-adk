#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for python_tool in customer_care/get_healthcare_benefits.py customer_care/get_my_claims.py customer_care/search_healthcare_providers.py customer_care/format_task_results.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${python_tool} -r ${SCRIPT_DIR}/tools/requirements.txt
done

for agent in customer_care_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done

