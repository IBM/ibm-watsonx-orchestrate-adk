#!/usr/bin/env bash

# Delete script for removing AstraDB tables for bank transfer application
# This script deletes both the transaction_data table and accounts table

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
KEYSPACE_NAME="${ASTRA_KEYSPACE:-default_keyspace}"

echo "🗑️  Deleting AstraDB tables for bank transfer application..."
echo "   Endpoint: $API_ENDPOINT"
echo "   Keyspace: $KEYSPACE_NAME"
echo "   Tables: transaction_data, accounts, contact_details"
echo ""

# Confirm deletion
read -p "⚠️  Are you sure you want to delete ALL tables (transaction_data, accounts, and contact_details)? This will remove all data. (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Deletion cancelled"
    exit 0
fi

echo ""

# ============================================================================
# Delete transaction_data table
# ============================================================================
echo "🗑️  Deleting transaction_data table..."
TABLE_NAME="transaction_data"

curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "dropTable": {
    "name": "'"${TABLE_NAME}"'"
  }
}' | python3 -m json.tool

echo ""
echo "✅ transaction_data table deletion request sent!"
echo ""

# ============================================================================
# Delete accounts table
# ============================================================================
echo "🗑️  Deleting accounts table..."
TABLE_NAME="accounts"

curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "dropTable": {
    "name": "'"${TABLE_NAME}"'"
  }
}' | python3 -m json.tool

echo ""
echo "✅ accounts table deletion request sent!"
echo ""

# ============================================================================
# Delete contact_details table
# ============================================================================
echo "🗑️  Deleting contact_details table..."
TABLE_NAME="contact_details"

curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "dropTable": {
    "name": "'"${TABLE_NAME}"'"
  }
}' | python3 -m json.tool

echo ""
echo "✅ contact_details table deletion request sent!"
echo ""
echo "🔍 Verify the tables were deleted:"
echo "   1. Go to https://astra.datastax.com"
echo "   2. Navigate to your database"
echo "   3. Check the '${KEYSPACE_NAME}' keyspace"
echo "   4. Confirm 'transaction_data', 'accounts', and 'contact_details' tables are no longer present"
echo ""
echo "⚠️  Note: All flow state data, account data, and contact data have been permanently deleted."

# Made with Bob