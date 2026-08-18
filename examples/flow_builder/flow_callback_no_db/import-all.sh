#!/usr/bin/env bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

orchestrate env activate local

# import flow_with_callbacks_tool flow (used as callback by example flow)
echo "🔧 Importing flow_with_callbacks_tool flow..."
orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/flow_callback_handler.py -p ${SCRIPT_DIR}/tools/
echo "✅ Flow imported"

echo ""

# import callback_handler_on_task_wait flow (used as callback by example flow)
echo "🔧 Importing callback_handler_on_task_wait flow..."
orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/task_callback_handler.py -p ${SCRIPT_DIR}/tools/
echo "✅ Flow imported"

echo ""

# import example flow with callbacks
echo "🔧 Importing example flow with callback..."
orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/example_flow_with_callback.py -p ${SCRIPT_DIR}/tools/
echo "✅ Flow imported"

echo ""

# import agent
echo "🤖 Importing flow callback agent..."
orchestrate agents import -f ${SCRIPT_DIR}/agents/flow_callback_agent.yaml
echo "✅ Agent imported"

echo ""
echo "✅ Import complete!"
echo ""
