#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. "$SCRIPT_DIR"/env.sh

curl -X POST -k "http://localhost:9044/tempus/flow/model/hello_world" -v \
  --header 'Content-Type: application/json' \
  --header "Authorization: Bearer $(cat ~/.cache/orchestrate/credentials.yaml  | yq .auth.local.wxo_mcsp_token)" \
  --data "$(cat $SCRIPT_DIR/../../flow_builder/generated_model/hello_world_agent.json)"
