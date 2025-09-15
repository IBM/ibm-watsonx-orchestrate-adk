#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )


# read from .env
# make sure to set GROQ_API_KEY and TAVILY_API_KEY
set -a
source .env
set +a

#
# create connections
#
orchestrate connections add --app-id city_news
orchestrate connections configure -a city_news --env draft --kind key_value --type team
orchestrate connections set-credentials -a city_news --env draft -e GROQ_API_KEY=$GROQ_API_KEY -e TAVILY_API_KEY=$TAVILY_API_KEY

# import langflow tool
for flow_tool in CityNews.json; do
  orchestrate tools import -k langflow -f ${SCRIPT_DIR}/tools/${flow_tool} --app-id city_news -r ${SCRIPT_DIR}/tools/requirements.txt
done

for agent in travel_advice_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done