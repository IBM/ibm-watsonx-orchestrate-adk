#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. "$SCRIPT_DIR"/env.sh

curl -X POST -k "http://localhost:9044/tempus/v1/flow/hello_world/version/TIP" -v \
  --header 'Content-Type: application/json' \
  --header "wxoMsgThreadId: ${WXO_SERVER_MSG_THREAD_ID}" \
  --header "Authorization: Bearer $(cat ~/.cache/orchestrate/credentials.yaml  | yq .auth.local.wxo_mcsp_token)"
