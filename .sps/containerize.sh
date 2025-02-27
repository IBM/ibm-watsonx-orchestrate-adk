#!/usr/bin/env bash

set -euo pipefail

warn "ENTER ${BASH_SOURCE[0]}"

BUILD_IMAGE=$(get_env "wai-build-env-image")
login_docker_registry "$(get_env "wai-registry-development")"


if property_set "wai-release-type"; then
  release_type=$(get_env "wai-release-type")
  release_type=echo $release_type | awk '{ print tolower($1) }'
  VERSION=$(docker_run $BUILD_IMAGE "hatch version ${release_type} 2> /dev/null")
else
  VERSION=$(docker_run $BUILD_IMAGE "hatch version dev 2> /dev/null")
fi
set_env wai-artifactory-link "https://na.artifactory.swg-devops.com/artifactory/api/pypi/wcp-wea-pypi-local/wxo-clients/${VERSION}"
set_env wai-artifact-version "${VERSION}"

echo "TARGET VERSION ${VERSION}"
docker_run $BUILD_IMAGE "hatch build"

success "EXIT ${BASH_SOURCE[0]}"