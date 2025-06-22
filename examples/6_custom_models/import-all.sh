 #!/usr/bin/env bash
 set -x

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate connections import -f ${SCRIPT_DIR}/connections/openai.yaml
orchestrate connections import -f ${SCRIPT_DIR}/connections/anthropic.yaml

set +x
. ../../.env
orchestrate connections set-credentials -a openai --env draft -e "api_key=$OPENAI_API_KEY"
orchestrate connections set-credentials -a openai --env live -e "api_key=$OPENAI_API_KEY"

orchestrate connections set-credentials -a anthropic --env draft -e "api_key=$ANTHROPIC_API_KEY"
orchestrate connections set-credentials -a anthropic --env live -e "api_key=$ANTHROPIC_API_KEY"
set -x

orchestrate models add -n virtual-model/openai/o4-mini -a openai --description "OpenAI O4 Mini"
orchestrate models add -n virtual-model/anthropic/claude-3-5-sonnet-20241022 -a anthropic --description "Claude Sonnet 3.5 v2"
orchestrate models add -n virtual-model/anthropic/claude-3-5-sonnet-20240620 -a anthropic --description "Claude Sonnet 3.5"

orchestrate models policy import -f ${SCRIPT_DIR}/policies/claude-model-fallback-policy.yaml
orchestrate models policy import -f ${SCRIPT_DIR}/policies/claude-model-loadbalance-policy.yaml


for python_tool in get_healthcare_benefits.py get_my_claims.py search_healthcare_providers.py; do
 orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${python_tool} -r ${SCRIPT_DIR}/tools/requirements.txt
done


for agent in anthropic_api_agent.yaml openai_api_agent.yaml; do
 orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done


