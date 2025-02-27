#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=/dev/null
source "${WORKSPACE}/${PIPELINE_CONFIG_REPO_PATH}/scripts/_library_release_util.sh"
#
#if property_set "wai-release-type"; then
#    warn "Starting auto release"
#    # Need to pass in the path of the version file
#    python_release src/ibm_watsonx_orchestrate/__init__.py
#fi

success "EXIT ${BASH_SOURCE[0]}"