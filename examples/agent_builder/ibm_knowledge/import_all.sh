#!/usr/bin/env bash
set -x

git lfs install

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate knowledge-bases import -f ${SCRIPT_DIR}/knowledge_base/ibm_knowledge_base.yaml
orchestrate agents import -f ${SCRIPT_DIR}/agents/ibm_agent.yaml
