#!/usr/bin/env bash
set -x

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Import the universities tool
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/universities/get_universities.py -r ${SCRIPT_DIR}/tools/universities/requirements.txt

# Import the university finder agent
orchestrate agents import -f ${SCRIPT_DIR}/agents/university_finder_agent.yaml

echo "Import completed successfully!"

# Made with Bob
