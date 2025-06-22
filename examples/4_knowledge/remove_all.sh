#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate knowledge-bases remove -n ibm_knowledge_base
orchestrate agents remove -n ibm_agent -k native
