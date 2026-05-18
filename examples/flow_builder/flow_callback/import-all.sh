#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# read from .env
# make sure to set ASTRA_TOKEN, ASTRA_URL, and ASTRA_KEYSPACE
set -a
source .env
set +a

# List of required environment variables
REQUIRED_VARS=("ASTRA_TOKEN" "ASTRA_URL")

# Check each variable
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Error: Environment variable '$var' is not set."
    echo "Please copy .env.example to .env and configure your AstraDB credentials."
    exit 1
  fi
done

echo "✅ Environment variables validated"
echo ""

#
# create connections
#
echo "📦 Creating connection for flow_callback_app..."
orchestrate connections add --app-id flow_callback_app
orchestrate connections configure -a flow_callback_app --env draft --kind key_value --type team
orchestrate connections set-credentials -a flow_callback_app --env draft -e ASTRA_TOKEN="$ASTRA_TOKEN" -e ASTRA_URL="$ASTRA_URL" -e ASTRA_KEYSPACE="${ASTRA_KEYSPACE:-default_keyspace}"

echo "✅ Connection created"
echo ""

# import flow callback handler tool
echo "🔧 Importing flow callback handler tool..."
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/flow_callback_handler.py --app-id flow_callback_app -r ${SCRIPT_DIR}/tools/requirements.txt -p ${SCRIPT_DIR}/tools/
echo "✅ Tool imported"

echo ""

# import greeting tool
echo "🔧 Importing greeting tool..."
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/greeting_tool.py
echo "✅ Tool imported"

echo ""

# import query flow events tool
echo "🔧 Importing query flow events tool..."
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/query_flow_events.py --app-id flow_callback_app -r ${SCRIPT_DIR}/tools/requirements.txt
echo "✅ Tool imported"

echo ""

# import example flow with callbacks
echo "🔧 Importing example flow with callbacks..."
orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/example_flow_with_callbacks.py -p ${SCRIPT_DIR}/tools/
echo "✅ Flow imported"

echo ""

# import agent
echo "🤖 Importing flow callback agent..."
orchestrate agents import -f ${SCRIPT_DIR}/agents/flow_callback_agent.yaml
echo "✅ Agent imported"

echo ""
echo "✅ Import complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Make sure you've run ./setup_astra_table.sh to create the flow_events table"
echo "   2. Use the flow_callback_handler tool in your flows to track events"
echo "   3. Try running the example_flow_with_callbacks flow to see callbacks in action"
echo "   4. Chat with the flow_callback_agent to interact with the callback system"
echo ""

# Made with Bob
