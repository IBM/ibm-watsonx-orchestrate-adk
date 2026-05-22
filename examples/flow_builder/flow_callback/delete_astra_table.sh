#!/usr/bin/env bash

# Delete script for removing AstraDB flow_events table for flow callback application
# This script deletes the flow_events table

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Load environment variables
if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
fi

# Check for required environment variables
if [ -z "$ASTRA_TOKEN" ]; then
    echo "❌ Error: ASTRA_TOKEN not set"
    echo "Please set ASTRA_TOKEN in your .env file or environment"
    exit 1
fi

if [ -z "$ASTRA_URL" ]; then
    echo "❌ Error: ASTRA_URL not set"
    echo "Please set ASTRA_URL in your .env file or environment"
    exit 1
fi

# AstraDB configuration
API_ENDPOINT="$ASTRA_URL"
KEYSPACE_NAME="${ASTRA_NAMESPACE:-default_keyspace}"

echo "🗑️  Deleting AstraDB table for flow callback application..."
echo "   Endpoint: $API_ENDPOINT"
echo "   Keyspace: $KEYSPACE_NAME"
echo "   Table: flow_events"
echo ""

# Confirm deletion
read -p "⚠️  Are you sure you want to delete the flow_events table? This will remove all event data. (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Deletion cancelled"
    exit 0
fi

echo ""

# ============================================================================
# Delete flow_events table
# ============================================================================
echo "🗑️  Deleting flow_events table..."
TABLE_NAME="flow_events"

curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "dropTable": {
    "name": "'"${TABLE_NAME}"'"
  }
}' | python3 -m json.tool

echo ""
echo "✅ flow_events table deletion request sent!"
echo ""
echo "🔍 Verify the table was deleted:"
echo "   1. Go to https://astra.datastax.com"
echo "   2. Navigate to your database"
echo "   3. Check the '${KEYSPACE_NAME}' keyspace"
echo "   4. Confirm 'flow_events' table is no longer present"
echo ""
echo "⚠️  Note: All flow event data has been permanently deleted."

# Made with Bob