#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate tools import -k python -f ${SCRIPT_DIR}/agent_tools/tools_context.py

orchestrate agents import -f ${SCRIPT_DIR}/agent_tools/hr_agent_context.json
