#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# import IBM knowledge agent
KNOWLEDGE_IMPORT_DIR=$(dirname "$(dirname "$SCRIPT_DIR")")
${KNOWLEDGE_IMPORT_DIR}/agent_builder/ibm_knowledge/import_all.sh


# import email tool
for python_tool in send_emails.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${python_tool}
done

# import ibm_knowledge_to_email flow
for flow_tool in ibm_knowledge_to_emails.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool}
done

# import email agent
for agent in email_agent.yaml ibm_email_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done