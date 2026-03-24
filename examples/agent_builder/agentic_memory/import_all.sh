#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for python_tool in create_patient_support_ticket.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/${python_tool}
done

for agent in st_marys_hospitals_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/${agent}
done

