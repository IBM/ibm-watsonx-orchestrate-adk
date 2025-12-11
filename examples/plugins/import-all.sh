#!/usr/bin/env bash
set -x

orchestrate env activate local

# Absolute path to this script's directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# --- Import Python tools ---
for tool in \
    plugins/email_masking_plugin.py \
    plugins/guardrail_plugin.py \
    tools/python_tool_example.py
do
  orchestrate tools import -k python -f "${SCRIPT_DIR}/${tool}"
done

# --- Import Agents ---
for agent in agents/email_agent.yaml
do
  orchestrate agents import -f "${SCRIPT_DIR}/${agent}"
done
