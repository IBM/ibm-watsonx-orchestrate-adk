#!/bin/bash

set -euo pipefail

# ============================================================
# Configuration
# ============================================================

BASE_URL="<Service instance URL>/v1/orchestrate"
APP_ID="voice-webhook-call-detail-record"
WEBHOOK_TYPE="call_detail_record"
AGENT_ID=""
WEBHOOK_URL=""
JWT_TOKEN=""

# ============================================================
# Parse arguments
# ============================================================

ENV="draft"

usage() {
  echo "Usage: $0 [--env draft|live]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      ;;
  esac
done

if [[ "$ENV" != "draft" && "$ENV" != "live" ]]; then
  echo "ERROR: --env must be 'draft' or 'live'"
  usage
fi

# ============================================================
# Validate required fields
# ============================================================

if [ -z "$BASE_URL" ] || [ -z "$AGENT_ID" ] || [ -z "$WEBHOOK_URL" ] || [ -z "$JWT_TOKEN" ]; then
  echo "ERROR: BASE_URL, AGENT_ID, WEBHOOK_URL, and JWT_TOKEN must all be set in the script"
  exit 1
fi

AUTH="Authorization: Bearer ${JWT_TOKEN}"

echo "============================================================"
echo "APP_ID:       $APP_ID"
echo "WEBHOOK_TYPE: $WEBHOOK_TYPE"
echo "AGENT_ID:     $AGENT_ID"
echo "WEBHOOK_URL:  $WEBHOOK_URL"
echo "ENV:          $ENV"
echo "============================================================"

# ============================================================
# 1. Get or create application
# ============================================================

echo ""
echo "[1/5] Fetching applications..."
APPS=$(curl -sf -m 10 -X GET "${BASE_URL}/connections/applications" \
  -H "$AUTH")

CONNECTION_ID=$(echo "$APPS" | jq -r "[.applications[] | select(.app_id==\"${APP_ID}\")] | first | .connection_id // empty")

if [ -z "$CONNECTION_ID" ]; then
  echo "  Application not found — creating..."
  CREATE_RESPONSE=$(curl -sf -m 10 -X POST "${BASE_URL}/connections/applications" \
    -H "Content-Type: application/json" \
    -H "$AUTH" \
    -d @- <<EOF
{
  "app_id": "${APP_ID}",
  "name": "Voice webhook - ${APP_ID}",
  "description": "Voice webhook - ${APP_ID}"
}
EOF
  )
  echo "$CREATE_RESPONSE" | jq
  APPS=$(curl -sf -m 10 -X GET "${BASE_URL}/connections/applications" -H "$AUTH")
  CONNECTION_ID=$(echo "$APPS" | jq -r "[.applications[] | select(.app_id==\"${APP_ID}\")] | first | .connection_id // empty")
fi

CONNECTION_ID=$(echo "$CONNECTION_ID" | tr -d '[:space:]')

if [ -z "$CONNECTION_ID" ]; then
  echo "ERROR: Failed to resolve CONNECTION_ID"
  exit 1
fi

echo "  CONNECTION_ID: $CONNECTION_ID"

# ============================================================
# 2. Ensure configuration
# ============================================================

echo ""
echo "[2/5] Checking configuration for env=${ENV}..."
CONFIG_RESPONSE=$(curl -s -m 10 -w "\nHTTP_STATUS:%{http_code}" \
  -X GET "${BASE_URL}/connections/applications/${APP_ID}/configurations/${ENV}" \
  -H "$AUTH")
CONFIG_BODY=$(echo "$CONFIG_RESPONSE" | sed '$d')
CONFIG_STATUS=$(echo "$CONFIG_RESPONSE" | tail -n1 | cut -d: -f2)
echo "  DEBUG: HTTP $CONFIG_STATUS — $CONFIG_BODY"

if [ "$CONFIG_STATUS" = "200" ]; then
  HAS_CONFIG=$(echo "$CONFIG_BODY" | jq -r '.connection_id // empty')
  echo "  Configuration exists (connection_id: $HAS_CONFIG)"
  if [ -z "$CONNECTION_ID" ]; then
    CONNECTION_ID=$(echo "$HAS_CONFIG" | tr -d '[:space:]')
    echo "  Using CONNECTION_ID from config: $CONNECTION_ID"
  fi
else
  echo "  No configuration found — creating..."
  curl -sf -m 10 -X POST "${BASE_URL}/connections/applications/${APP_ID}/configurations" \
    -H "Content-Type: application/json" \
    -H "$AUTH" \
    -d @- <<EOF | jq
{
  "environment": "${ENV}",
  "preference": "team",
  "sso": false,
  "server_url": "${WEBHOOK_URL}",
  "security_scheme": "basic_auth"
}
EOF
fi

# ============================================================
# 3. Ensure runtime credentials (upsert — skip GET, POST and treat 409 as ok)
# ============================================================

echo ""
echo "[3/5] Creating runtime credentials (upsert)..."
RUNTIME_CREATE_RESPONSE=$(curl -s -m 10 -w "\nHTTP_STATUS:%{http_code}" \
  -X POST "${BASE_URL}/connections/applications/${APP_ID}/configs/${ENV}/runtime_credentials" \
  -H "Content-Type: application/json" \
  -H "$AUTH" \
  -d @- <<EOF
{
  "runtime_credentials": {
    "username": "<username>",
    "password": "<password>",
    "custom_runtime_credentials": {
      "voice_webhook_settings": {
        "headers": {
          "custom_header_1": "custom_value_1",
          "custom_header_2": "custom_value_2"
        },
        "timeout": 2
      }
    }
  }
}
EOF
)
RUNTIME_CREATE_BODY=$(echo "$RUNTIME_CREATE_RESPONSE" | sed '$d')
RUNTIME_CREATE_STATUS=$(echo "$RUNTIME_CREATE_RESPONSE" | tail -n1 | cut -d: -f2)
echo "  HTTP STATUS: $RUNTIME_CREATE_STATUS"
echo "  BODY: $RUNTIME_CREATE_BODY"

if [ "$RUNTIME_CREATE_STATUS" = "200" ] || [ "$RUNTIME_CREATE_STATUS" = "201" ]; then
  echo "  Runtime credentials created"
elif [ "$RUNTIME_CREATE_STATUS" = "409" ]; then
  echo "  Runtime credentials already exist"
else
  echo "ERROR: Unexpected status creating runtime credentials: $RUNTIME_CREATE_STATUS"
  exit 1
fi

# ============================================================
# 4. Fetch agent and check existing webhooks
# ============================================================

echo ""
echo "[4/5] Fetching agent ${AGENT_ID}..."
AGENT_RESPONSE=$(curl -s -m 10 -w "\nHTTP_STATUS:%{http_code}" \
  -X GET "${BASE_URL}/agents/${AGENT_ID}" \
  -H "$AUTH" \
  -H "X-Watson-Origin: internal")

AGENT_BODY=$(echo "$AGENT_RESPONSE" | sed '$d')
AGENT_STATUS=$(echo "$AGENT_RESPONSE" | tail -n1 | cut -d: -f2)

echo "  HTTP STATUS: $AGENT_STATUS"

if [ "$AGENT_STATUS" != "200" ]; then
  echo "ERROR: Failed to fetch agent:"
  echo "$AGENT_BODY"
  exit 1
fi

EXISTING=$(echo "$AGENT_BODY" | jq -r \
  ".voice_webhook_connections.${ENV}[]? | select(.webhook_type==\"${WEBHOOK_TYPE}\") | .connection_id // empty")

# ============================================================
# 5. Attach webhook
# ============================================================

echo ""
echo "[5/5] Attaching webhook..."
echo "  CONNECTION_ID: $CONNECTION_ID"

if [ -z "$EXISTING" ]; then
  ATTACH_RESPONSE=$(curl -s -m 10 -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "${BASE_URL}/agents/${AGENT_ID}/voice_webhook_connections" \
    -H "Content-Type: application/json" \
    -H "$AUTH" \
    -H "X-Watson-Origin: internal" \
    -d @- <<EOF
{
  "connection_id": "${CONNECTION_ID}",
  "webhook_type": "${WEBHOOK_TYPE}",
  "environment": "${ENV}"
}
EOF
  )
  ATTACH_BODY=$(echo "$ATTACH_RESPONSE" | sed '$d')
  ATTACH_STATUS=$(echo "$ATTACH_RESPONSE" | tail -n1 | cut -d: -f2)
  echo "  HTTP STATUS: $ATTACH_STATUS"
  echo "  BODY: $ATTACH_BODY"

  if [ "$ATTACH_STATUS" = "200" ] || [ "$ATTACH_STATUS" = "201" ]; then
    echo "  Webhook attached successfully"
  elif [ "$ATTACH_STATUS" = "409" ]; then
    echo "  Webhook already attached"
  else
    echo "ERROR: Unexpected status attaching webhook: $ATTACH_STATUS"
    exit 1
  fi
else
  echo "  Webhook already attached (connection_id: $EXISTING) — skipping"
fi

echo ""
echo "DONE"

