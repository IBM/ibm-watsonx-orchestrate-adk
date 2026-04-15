#!/usr/bin/env bash

# Setup script for creating AstraDB tables for bank transfer application
# This script creates both the transaction_data table and accounts table

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

echo "🚀 Setting up AstraDB tables for bank transfer application..."
echo "   Endpoint: $API_ENDPOINT"
echo "   Keyspace: $KEYSPACE_NAME"
echo ""

# ============================================================================
# Create transaction_data table for flow state storage
# ============================================================================
echo "📋 Creating transaction_data table..."
TABLE_NAME="transaction_data"

curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "createTable": {
    "name": "'"${TABLE_NAME}"'",
    "definition": {
      "columns": {
        "instance_id": {
          "type": "uuid"
        },
        "task_id": {
          "type": "uuid"
        },
        "state": {
          "type": "text"
        },
        "state_data": {
          "type": "text"
        },
        "created_at": {
          "type": "text"
        },
        "updated_at": {
          "type": "text"
        }
      },
      "primaryKey": "task_id"
    }
  }
}' | python3 -m json.tool

echo ""
echo "✅ transaction_data table creation request sent!"
echo ""
echo "🔍 Creating index on instance_id for better query performance..."

# Create index on instance_id
curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}/${TABLE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "createIndex": {
    "name": "instance_id_idx",
    "definition": {
      "column": "instance_id"
    }
  }
}' | python3 -m json.tool

echo ""
echo "✅ Index creation request sent!"
echo ""

# ============================================================================
# Create accounts table for account balances
# ============================================================================
echo "📋 Creating accounts table..."
TABLE_NAME="accounts"

curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "createTable": {
    "name": "'"${TABLE_NAME}"'",
    "definition": {
      "columns": {
        "account_id": {
          "type": "text"
        },
        "account_type": {
          "type": "text"
        },
        "balance": {
          "type": "decimal"
        }
      },
      "primaryKey": "account_id"
    }
  }
}' | python3 -m json.tool

echo ""
echo "✅ accounts table creation request sent!"
echo ""

# ============================================================================
# Create contact_details table for contact information
# ============================================================================
echo "📋 Creating contact_details table..."
TABLE_NAME="contact_details"

curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "createTable": {
    "name": "'"${TABLE_NAME}"'",
    "definition": {
      "columns": {
        "contact_id": {
          "type": "text"
        },
        "name": {
          "type": "text"
        },
        "address": {
          "type": "text"
        },
        "email": {
          "type": "text"
        }
      },
      "primaryKey": "contact_id"
    }
  }
}' | python3 -m json.tool

echo ""
echo "✅ contact_details table creation request sent!"
echo ""

# Wait a moment for table creation to complete
sleep 2

# ============================================================================
# Initialize accounts table with data from account_list.json
# ============================================================================
echo "💾 Loading account data from account_list.json..."

if [ ! -f "${SCRIPT_DIR}/account_list.json" ]; then
    echo "❌ Error: account_list.json not found"
    exit 1
fi

# Export variables for Python script
export SCRIPT_DIR
export API_ENDPOINT
export KEYSPACE_NAME
export ASTRA_TOKEN

# Read the JSON file and insert each account
python3 << 'EOF'
import json
import os
import requests
import sys

script_dir = os.environ.get('SCRIPT_DIR')
api_endpoint = os.environ.get('API_ENDPOINT')
keyspace = os.environ.get('KEYSPACE_NAME')
table = "accounts"
token = os.environ.get('ASTRA_TOKEN')

# Load accounts from JSON
with open(f'{script_dir}/account_list.json', 'r') as f:
    accounts = json.load(f)

print(f"📊 Found {len(accounts)} accounts to insert")
print("")

# Insert each account
for account in accounts:
    account_id = account['account_id']
    account_type = account['account_type']
    balance = account['balance']
    
    print(f"   Inserting {account_id} ({account_type}): ${balance}")
    
    payload = {
        "insertOne": {
            "document": {
                "account_id": account_id,
                "account_type": account_type,
                "balance": balance
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
        print(f"❌ Error inserting {account_id}: {response.text}")
        sys.exit(1)

print("")
print("✅ All accounts inserted successfully!")
EOF

echo ""

# ============================================================================
# Initialize contact_details table with data from contacts.json
# ============================================================================
echo "💾 Loading contact data from contacts.json..."

if [ ! -f "${SCRIPT_DIR}/contacts.json" ]; then
    echo "❌ Error: contacts.json not found"
    exit 1
fi

# Read the JSON file and insert each contact
python3 << 'EOF'
import json
import os
import requests
import sys

script_dir = os.environ.get('SCRIPT_DIR')
api_endpoint = os.environ.get('API_ENDPOINT')
keyspace = os.environ.get('KEYSPACE_NAME')
table = "contact_details"
token = os.environ.get('ASTRA_TOKEN')

# Load contacts from JSON
with open(f'{script_dir}/contacts.json', 'r') as f:
    contacts = json.load(f)

print(f"📊 Found {len(contacts)} contacts to insert")
print("")

# Insert each contact
for contact in contacts:
    contact_id = contact['contact_id']
    name = contact['name']
    address = contact['address']
    email = contact['email']
    
    print(f"   Inserting {contact_id} ({name})")
    
    payload = {
        "insertOne": {
            "document": {
                "contact_id": contact_id,
                "name": name,
                "address": address,
                "email": email
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
        print(f"❌ Error inserting {contact_id}: {response.text}")
        sys.exit(1)

print("")
print("✅ All contacts inserted successfully!")
EOF

echo ""
echo "=" "================================================================"
echo "📝 Summary of Created Tables"
echo "=" "================================================================"
echo ""
echo "1️⃣  transaction_data table (Flow State Storage):"
echo "   - instance_id (uuid, INDEXED): Unique flow instance identifier"
echo "   - task_id (uuid, PRIMARY KEY): Task/interaction identifier"
echo "   - state (text): Current flow state (working, input_required, completed, failed)"
echo "   - state_data (text): JSON string containing full flow state details"
echo "   - created_at (text): ISO 8601 timestamp when flow was created"
echo "   - updated_at (text): ISO 8601 timestamp of last update"
echo ""
echo "   ℹ️  Note: Each write creates a NEW ROW with a new task_id."
echo "   This creates a complete audit trail of all interactions."
echo ""
echo "2️⃣  accounts table (Account Balances):"
echo "   - account_id (text, PRIMARY KEY): Unique account identifier"
echo "   - account_type (text): Type of account (checking, savings, etc.)"
echo "   - balance (decimal): Current account balance"
echo ""
echo "📊 Initialized Accounts:"
python3 -c "import json; accounts = json.load(open('${SCRIPT_DIR}/account_list.json')); [print(f\"   - {a['account_id']}: {a['account_type']} - \${a['balance']}\") for a in accounts]"
echo ""
echo "3️⃣  contact_details table (Contact Information):"
echo "   - contact_id (text, PRIMARY KEY): Unique contact identifier"
echo "   - name (text): Contact's full name"
echo "   - address (text): Contact's mailing address"
echo "   - email (text): Contact's email address"
echo ""
echo "📊 Initialized Contacts:"
python3 -c "import json; contacts = json.load(open('${SCRIPT_DIR}/contacts.json')); [print(f\"   - {c['contact_id']}: {c['name']} ({c['email']})\") for c in contacts]"
echo ""
echo "🔍 Verify the tables were created:"
echo "   1. Go to https://astra.datastax.com"
echo "   2. Navigate to your database"
echo "   3. Check the '${KEYSPACE_NAME}' keyspace"
echo "   4. Look for the 'transaction_data', 'accounts', and 'contact_details' tables"
echo ""
echo "✅ Setup complete!"

# Made with Bob
