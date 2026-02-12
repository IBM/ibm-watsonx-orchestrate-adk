#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate toolkits remove -n banking || true
orchestrate toolkits import -f ${SCRIPT_DIR}/toolkits/banking_mcp_server.yaml


for agent in banking_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done

