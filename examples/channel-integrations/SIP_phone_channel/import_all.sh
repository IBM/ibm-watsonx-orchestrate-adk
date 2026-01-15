#!/usr/bin/env bash
set -x

# orchestrate env activate your_environment

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# set up your SIP phone number
your_sip_number="+11234567890"

orchestrate voice-configs import -f ${SCRIPT_DIR}/voice/voice_example.yaml;

orchestrate agents import -f ${SCRIPT_DIR}/agents/channel_agent.yaml;

orchestrate phone import -f ${SCRIPT_DIR}/phone/genesys_audio_connector_example.yaml;

orchestrate phone add-number --name "SIP Phone Channel" --number ${your_sip_number} --agent-name channel_agent --env draft
