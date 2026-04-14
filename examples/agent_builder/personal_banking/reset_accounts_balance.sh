#!/usr/bin/env bash

# Reset script for updating account balances to values in account_list.json
# This script updates existing accounts in the accounts table without recreating it

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
TABLE_NAME="accounts"

echo "🔄 Resetting account balances from account_list.json..."
echo "   Endpoint: $API_ENDPOINT"
echo "   Keyspace: $KEYSPACE_NAME"
echo "   Table: $TABLE_NAME"
echo ""

# Check if account_list.json exists
if [ ! -f "${SCRIPT_DIR}/account_list.json" ]; then
    echo "❌ Error: account_list.json not found"
    exit 1
fi

# Export variables for Python script
export SCRIPT_DIR
export API_ENDPOINT
export KEYSPACE_NAME
export TABLE_NAME
export ASTRA_TOKEN

# Update account balances using Python
python3 << 'EOF'
import json
import os
import requests
import sys

script_dir = os.environ.get('SCRIPT_DIR')
api_endpoint = os.environ.get('API_ENDPOINT')
keyspace = os.environ.get('KEYSPACE_NAME')
table = os.environ.get('TABLE_NAME')
token = os.environ.get('ASTRA_TOKEN')

# Load accounts from JSON
with open(f'{script_dir}/account_list.json', 'r') as f:
    accounts = json.load(f)

print(f"📊 Found {len(accounts)} accounts to reset")
print("")

# Update each account
for account in accounts:
    account_id = account['account_id']
    account_type = account['account_type']
    balance = account['balance']
    
    print(f"   Resetting {account_id} ({account_type}): ${balance}")
    
    # Use updateOne to update existing records or insert if not exists
    payload = {
        "updateOne": {
            "filter": {
                "account_id": account_id
            },
            "update": {
                "$set": {
                    "account_type": account_type,
                    "balance": balance
                }
            },
            "options": {
                "upsert": True
            }
        }
    }
    
    response = requests.post(
        f"{api_endpoint}/api/json/v1/{keyspace}/{table}",
        headers={
            "Token": token,
            "Content-Type": "application/json"
        },
        json=payload
    )
    
    if response.status_code != 200:
        print(f"❌ Error updating {account_id}: {response.text}")
        sys.exit(1)

print("")
print("✅ All account balances reset successfully!")
EOF

echo ""
echo "📊 Reset Accounts:"
python3 -c "import json; accounts = json.load(open('${SCRIPT_DIR}/account_list.json')); [print(f\"   - {a['account_id']}: {a['account_type']} - \${a['balance']}\") for a in accounts]"
echo ""
echo "✅ Reset complete!"

# Made with Bob