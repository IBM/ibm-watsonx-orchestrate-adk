#!/usr/bin/env bash
set -x
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate env activate local

orchestrate tools import -k python -f ${SCRIPT_DIR}/agent_tools/tools.py

orchestrate agents import -f ${SCRIPT_DIR}/agent_tools/hr_agent.json
