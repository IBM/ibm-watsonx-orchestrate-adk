#!/usr/bin/env bash
set -x

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. ../../.env
orchestrate connections import -f ${SCRIPT_DIR}/connections/tavily.yaml
set +x
orchestrate connections set-credentials -a tavily --env draft -e "TAVILY_API_KEY=$TAVILY_API_KEY"
orchestrate connections set-credentials -a tavily --env live -e "TAVILY_API_KEY=$TAVILY_API_KEY"
set -x

orchestrate toolkits import --kind mcp \
  --name tavily \
  --description "Search the internet" \
  --command "npx -y tavily-mcp@0.1.3" \
  --package "tavily-mcp@0.1.3" \
  --tools "*"  \
  --app-id tavily

for agent in internet_searcher.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done

