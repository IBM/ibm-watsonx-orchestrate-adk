#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Import Python tools
orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/knowledge_base_search.py"
orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/get_order_history.py"

# Import agent
orchestrate agents import -f "${SCRIPT_DIR}/agent.yaml"
