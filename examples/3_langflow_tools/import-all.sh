#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )


# read from .env
# make sure to set GROQ_API_KEY and TAVILY_API_KEY
set -a
. ../../.env
set +a

#
# create connections
#
orchestrate connections import -f ${SCRIPT_DIR}/connections/city_news.yaml

# set credentials for connections
for env in draft live; do
  orchestrate connections set-credentials -a city_news --env $env -e "TAVILY_API_KEY=$TAVILY_API_KEY" -e "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY";
done;


# import langflow tool
for flow_tool in CityNews.json; do
  orchestrate tools import -k langflow -f ${SCRIPT_DIR}/tools/${flow_tool} -a city_news -r ${SCRIPT_DIR}/tools/requirements.txt
done

for agent in travel_advice_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done