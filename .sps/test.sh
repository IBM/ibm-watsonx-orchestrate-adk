#!/usr/bin/env bash

set -euo pipefail

source "${WORKSPACE}/${PIPELINE_CONFIG_REPO_PATH}/scripts/_docker.sh"

warn "ENTER ${BASH_SOURCE[0]}"

BUILD_IMAGE=$(get_env "wai-build-env-image")
login_docker_registry "$(get_env "wai-registry-development")"
BASE_DIR=$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")

echo $BASE_DIR

UNIT_TEST_SCRIPT=$(cat <<EOF
pip install ".[dev]"
mkdir -p coverage
hatch run test:coverage run -m pytest --junitxml coverage/test-results.xml
#hatch run test:coverage html -d coverage/html
#tar czvf coverage/coverage-html.tar.gz coverage/html
#hatch run test:coverage xml -o coverage/coverage.xml
EOF)

docker_run $BUILD_IMAGE "$UNIT_TEST_SCRIPT"

ls -lah "${BASE_DIR}/coverage"


collect_evidence \
   --tool-type "pytest" \
   --attachment "${BASE_DIR}/coverage/test-results.xml"

#   --attachment "${BASE_DIR}/coverage/coverage.xml" \
#   --attachment "${BASE_DIR}/coverage/coverage-html.tar.gz"

success "EXIT ${BASH_SOURCE[0]}"