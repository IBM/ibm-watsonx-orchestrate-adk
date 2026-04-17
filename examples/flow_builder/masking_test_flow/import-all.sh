#!/usr/bin/env bash

# orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Import flow tools
for flow_tool in masking_test_flow.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool}
done

# Import Python tools (commented out until import issues are resolved)
for python_tool in process_user_data.py validate_credentials.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${python_tool}
done

# Import OpenAPI tools
for openapi_tool in jsonplaceholder-users.openapi.yml; do
  orchestrate tools import -k openapi -f ${SCRIPT_DIR}/tools/${openapi_tool}
done

for agent in masking_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done

echo "All tools imported successfully!"

