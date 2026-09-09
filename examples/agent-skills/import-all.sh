#!/usr/bin/env bash
set -x

orchestrate env activate local

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Import the skill first (uploads SKILL.md, scripts/, and references/ in one command)
orchestrate skills import --dir "${SCRIPT_DIR}/skills/hello-skill/"

# Import the agent (resolves the hello-skill name to its ID at import time)
orchestrate agents import -f "${SCRIPT_DIR}/agents/hello_skill_agent.yaml"
