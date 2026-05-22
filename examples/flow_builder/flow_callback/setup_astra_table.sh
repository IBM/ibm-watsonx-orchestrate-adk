#!/usr/bin/env bash

# Setup script for creating AstraDB flow_events table for flow callback application
# This script creates the flow_events table to store flow event data

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

echo "🚀 Setting up AstraDB table for flow callback application..."
echo "   Endpoint: $API_ENDPOINT"
echo "   Keyspace: $KEYSPACE_NAME"
echo ""

# ============================================================================
# Create flow_events table for flow event storage
# ============================================================================
echo "📋 Creating flow_events table..."
TABLE_NAME="flow_events"

curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "createTable": {
    "name": "'"${TABLE_NAME}"'",
    "definition": {
      "columns": {
        "event_id": {
          "type": "text"
        },
        "event_kind": {
          "type": "text"
        },
        "created_at": {
          "type": "text"
        },
        "instance_id": {
          "type": "text"
        },
        "flow_name": {
          "type": "text"
        },
        "environment_id": {
          "type": "text"
        },
        "flow_state": {
          "type": "text"
        },
        "parent_instance_id": {
          "type": "text"
        },
        "parent_flow_name": {
          "type": "text"
        },
        "task_id": {
          "type": "text"
        },
        "task_name": {
          "type": "text"
        },
        "task_display_name": {
          "type": "text"
        },
        "error": {
          "type": "text"
        },
        "output": {
          "type": "text"
        },
        "elicitation": {
          "type": "text"
        }
      },
      "primaryKey": "event_id"
    }
  }
}' | python3 -m json.tool

echo ""
echo "✅ flow_events table creation request sent!"
echo ""
echo "🔍 Creating indexes for better query performance..."

# Create index on instance_id for querying events by flow instance
curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}/${TABLE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "createIndex": {
    "name": "instance_id_idx2",
    "definition": {
      "column": "instance_id"
    }
  }
}' | python3 -m json.tool

echo ""
echo "✅ instance_id index creation request sent!"
echo ""

# Create index on event_kind for querying events by kind
curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}/${TABLE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "createIndex": {
    "name": "event_kind_idx",
    "definition": {
      "column": "event_kind"
    }
  }
}' | python3 -m json.tool

echo ""
echo "✅ event_kind index creation request sent!"
echo ""

# Create index on created_at for querying events by time
curl -sS -L -X POST "${API_ENDPOINT}/api/json/v1/${KEYSPACE_NAME}/${TABLE_NAME}" \
  --header "Token: ${ASTRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
  "createIndex": {
    "name": "created_at_idx",
    "definition": {
      "column": "created_at"
    }
  }
}' | python3 -m json.tool

echo ""
echo "✅ created_at index creation request sent!"
echo ""

echo "================================================================"
echo "📝 Summary of Created Table"
echo "================================================================"
echo ""
echo "1️⃣  flow_events table (Flow Callback Event Storage):"
echo "   - event_id (text, PRIMARY KEY): Unique event identifier"
echo "   - event_kind (text, INDEXED): Kind of flow callback event"
echo "   - created_at (text, INDEXED): ISO 8601 timestamp when event occurred"
echo "   - instance_id (text, INDEXED): Unique flow instance identifier"
echo "   - flow_name (text): Name of the flow"
echo "   - environment_id (text): Environment identifier"
echo "   - flow_state (text): Current execution state (working, input_required, completed, failed)"
echo "   - parent_instance_id (text): Parent flow instance ID (for child flows)"
echo "   - parent_flow_name (text): Parent flow name (for child flows)"
echo "   - task_id (text): Task identifier (for task-related events)"
echo "   - task_name (text): Internal task name (for task-related events)"
echo "   - task_display_name (text): Human-readable task display name (for task-related events)"
echo "   - error (text): JSON string containing error details (for error events)"
echo "   - output (text): JSON string containing flow output (when state is completed)"
echo "   - elicitation (text): JSON string containing elicitation details (when state is input_required)"
echo ""
echo "   ℹ️  Note: Each event creates a NEW ROW with a unique event_id."
echo "   This creates a complete audit trail of all flow callback events."
echo ""
echo "🔍 Verify the table was created:"
echo "   1. Go to https://astra.datastax.com"
echo "   2. Navigate to your database"
echo "   3. Check the '${KEYSPACE_NAME}' keyspace"
echo "   4. Look for the 'flow_events' table"
echo ""
echo "✅ Setup complete!"

# Made with Bob