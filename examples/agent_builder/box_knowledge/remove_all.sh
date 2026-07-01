#!/usr/bin/env bash
#
# Remove the Box knowledge base and HR benefits agent.
#
# Usage:
#   ./remove_all.sh

set -e

orchestrate agents remove -n hr_benefits_agent
orchestrate knowledge-bases remove -n box_hr_knowledge_base
