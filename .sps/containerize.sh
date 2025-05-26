#!/usr/bin/env bash

set -euo pipefail

source "${WORKSPACE}/${PIPELINE_CONFIG_REPO_PATH}/scripts/_github.sh"

function is_release_branch() {
  local branch=$(get_git_branch)
  local release_branch_pattern="^$(get_default_branch)-release-[0-9]+\.[0-9]+\.[0-9]+(b[0-9])*$"

  if [[ $branch =~ $release_branch_pattern ]]; then
      return 0
  else
      return 1
  fi
}

function is_staging_branch() {
  local branch=$(get_git_branch)
  local staging_branch_pattern="^$(get_default_branch)-staging-[0-9]+\.[0-9]+\.[0-9]+$"

  if [[ $branch =~ $staging_branch_pattern ]]; then
      return 0
  else
      return 1
  fi
}

function is_prebuild_branch() {
  local branch=$(get_git_branch)
  local staging_branch_pattern="^prebuild-.+$"

  if [[ $branch =~ $staging_branch_pattern ]]; then
      return 0
  else
      return 1
  fi
}

function is_prerelease() {
  if is_prebuild_branch || is_staging_branch; then
    return 0
  else
    return 1
  fi
}


warn "ENTER ${BASH_SOURCE[0]}"

BUILD_IMAGE=$(get_env "wai-build-env-image")
login_docker_registry "$(get_env "wai-registry-development")"


if property_set "wai-release-type"; then
  release_type=$(get_env "wai-release-type")
  release_type=$(echo "$release_type" | awk '{print tolower($0)}')
  docker_run $BUILD_IMAGE "hatch version ${release_type}"
fi


VERSION=$(docker_run $BUILD_IMAGE "hatch version")
set_env wai-artifact-version "${VERSION}"


echo "TARGET VERSION ${VERSION}"
if is_prerelease; then
  if is_prebuild_branch ; then
    SANITIZED_VERSION=$(echo "${VERSION}" | sed 's/b[0-9]*//')
    docker_run $BUILD_IMAGE "hatch version ${SANITIZED_VERSION}.dev${BUILD_NUMBER}"
  elif is_staging_branch; then
    SANITIZED_VERSION=$(echo "${VERSION}" | sed 's/b[0-9]*//')
    docker_run $BUILD_IMAGE "hatch version ${SANITIZED_VERSION}.rc${BUILD_NUMBER}"
  fi
  VERSION=$(docker_run $BUILD_IMAGE "hatch version")
fi
docker_run $BUILD_IMAGE "hatch build"


if is_prerelease && ! property_set "wai-release-type"; then
  info "Publishing release candidate version ${VERSION}"
  pypi_repo="testpypi"
  pypi_api_key=$(get_env "test-pypi-watson-devex")
  docker_run $BUILD_IMAGE "twine upload --repository testpypi -u __token__ -p ${pypi_api_key} dist/*"
  COMMIT_MESSAGE=$(cat <<EOF
### Release published to testpypi
Release ${VERSION} has been published to testpypi.

To install locally run
\`\`\`
pip install --upgrade -i https://test.pypi.org/simple/ ibm-watsonx-orchestrate==${VERSION}
orchestrate server start -e .env
orchestrate env activate local --registry testpypi --test-package-version-override ${VERSION}
\`\`\`
EOF)
  comment_on_issue "${COMMIT_MESSAGE}"
elif is_release_branch; then
  info "Publishing version ${VERSION}"

  pypi_repo="testpypi"
  pypi_api_key=$(get_env "test-pypi-watson-devex")
  docker_run $BUILD_IMAGE "twine upload --repository testpypi -u __token__ -p ${pypi_api_key} dist/*"

  pypi_repo="pypi"
  pypi_api_key=$(get_env "pypi-watson-devex")
  docker_run $BUILD_IMAGE "twine upload --repository pypi -u __token__ -p ${pypi_api_key} dist/*"

  github_create_release ${VERSION}
fi

success "EXIT ${BASH_SOURCE[0]}"