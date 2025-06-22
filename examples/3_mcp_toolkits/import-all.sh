#!/usr/bin/env bash
set -x

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate connections import -f ${SCRIPT_DIR}/connections/google-maps.yaml
orchestrate connections set-credentials -a google-maps --env draft -e "GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY"

orchestrate toolkits import --kind mcp \
  --name gmaps \
  --description "Allows a user to search google maps" \
  --command "npx -y @modelcontextprotocol/server-google-maps" \
  --tools "*"  \
  --package-root toolkits \
  --app-id google-maps

for agent in map_searcher.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done

