#!/usr/bin/env bash
set -x


#orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate agents import -f ${SCRIPT_DIR}/agents/sample_agent.yaml