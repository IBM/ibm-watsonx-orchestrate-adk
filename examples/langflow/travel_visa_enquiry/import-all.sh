#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )


# read from .env
# make sure to set ASTRA_API_KEY, WXAI_API_KEY and WXAI_PROJECT_ID
set -a
source .env
set +a

# List of required environment variables
REQUIRED_VARS=("ASTRA_API_KEY" "WXAI_API_KEY" "WXAI_PROJECT_ID")

# Check each variable
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Error: Environment variable '$var' is not set."
    exit 1
  fi
done

#
# create connections
#
orchestrate connections add --app-id doc_search
orchestrate connections configure -a doc_search --env draft --kind key_value --type team
orchestrate connections set-credentials -a doc_search --env draft -e ASTRA_API_KEY="$ASTRA_API_KEY" -e WXAI_API_KEY="$WXAI_API_KEY" -e WXAI_PROJECT_ID=$WXAI_PROJECT_ID

# import langflow tool
orchestrate tools import -k langflow -f ${SCRIPT_DIR}/tools/IndexIndiaVisaInfo.json --app-id doc_search -r ${SCRIPT_DIR}/tools/requirements.txt
orchestrate tools import -k langflow -f ${SCRIPT_DIR}/tools/QueryIndiaVisaInfo.json --app-id doc_search -r ${SCRIPT_DIR}/tools/requirements.txt


for agent in travel_visa_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done