#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate knowledge-bases remove -n ibm_knowledge_base_dynamic_mode
orchestrate tools remove -k python -n get_stock_price
orchestrate agents remove -n ibm_agent_dynamic_mode -k native
