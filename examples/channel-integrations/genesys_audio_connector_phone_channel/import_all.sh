#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/genesys_tools.py -r ${SCRIPT_DIR}/tools/requirements.txt;

orchestrate agents import -f ${SCRIPT_DIR}/agents/channel_agent.yaml;

orchestrate phone import -f ${SCRIPT_DIR}/phone/genesys_audio_connector_example.yaml;
