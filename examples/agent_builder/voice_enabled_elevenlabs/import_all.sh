#!/usr/bin/env bash
set -x

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate voice-configs import -f ${SCRIPT_DIR}/voice/voice_elevenlabs_tts.yaml;

orchestrate agents import -f ${SCRIPT_DIR}/agents/voice_enabled_agent.yaml;