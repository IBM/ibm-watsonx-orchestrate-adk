#!/bin/bash
##
## IBM Confidential
## OCO Source Materials
## 5737-I23
## Copyright IBM Corp. 2018 - 2025
## The source code for this program is not published or otherwise divested of its trade secrets, irrespective of what has been deposited with the U.S Copyright Office.
##

set -e

# If you change the location of this script the BASE_DIR should also be changed.
BASE_DIR=$(dirname "$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")") 
APP_HOME=/app
UT_OUTPUT_DIR=${BASE_DIR}/data/test-output
UT_OUTPUT_DIR_CONTAINER=${APP_HOME}/test-output
HOST_UID=$(id -u)
HOST_GID=$(id -g)
CMD_ARG=$1
DOCKER_REGISTRY_URL=${DOCKER_REGISTRY_URL:-docker-na-public.artifactory.swg-devops.com/hyc-odm-dockerhub-docker-remote}

function print_usage() {
    echo ""
    echo "Usage: run-unit-tests.sh <command>"
    echo ""
    echo "the <command> argument can be:"
    echo "  all     - run all unit tests."
    echo "  shell   - acquire the interactive shell session for manual debugging."
    echo ""
    echo "Note: make sure your dependencies are up-to-date before running the test. If in double, run tools/get-dependencies.sh to pull the latest dependencies."
    echo ""
}

function duration() {
    local PREFIX=$1
    local DURATION=$2
    local M=$((DURATION / 60))
    local S=$((DURATION % 60))
    printf '%s %d:%02d\n' "$PREFIX" "$M" "$S"
}

TEST_START_TS=$(date +%s)
function print_success() {
    local RC=${1:-0}
    TEST_END_TS=$(date +%s)
    if [ "$RC" -eq 0 ]; then
        echo ""
        echo "   _____ _    _  _____ _____ ______  _____ _____  "
        echo "  / ____| |  | |/ ____/ ____|  ____|/ ____/ ____| "
        echo " | (___ | |  | | |   | |    | |__  | (___| (___   "
        echo "  \___ \| |  | | |   | |    |  __|  \___  \\___ \ "
        echo "  ____) | |__| | |___| |____| |____ ____) |___) | "
        echo " |_____/ \____/ \_____\_____|______|_____/_____/  "
        echo ""
    else
        echo ""
        echo " XXXXXXX    X    XXX X       XXXXXXX XXXXXX  "
        echo " X         X X    X  X       X       X     X "
        echo " X        X   X   X  X       X       X     X "
        echo " XXXXX   X     X  X  X       XXXXX   X     X "
        echo " X       XXXXXXX  X  X       X       X     X "
        echo " X       X     X  X  X       X       X     X "
        echo " X       X     X XXX XXXXXXX XXXXXXX XXXXXX  "
        echo ""
    fi
    duration "Total test time:" $((TEST_END_TS - TEST_START_TS))
    echo "See the test report in ${UT_OUTPUT_DIR}"
    echo ""
}

function run_unit_test_container() {
    local RUN_CMD=$1
    local WITH_TTY=${2:-false}

    local TTY_ARG
    TTY_ARG=$([ "${WITH_TTY}" == "true" ] && echo "-t" || echo "")

    # Clean up the running container if exists
    local CONTAINER_NAME=wxo-clients-flow-tests
    docker rm -f ${CONTAINER_NAME} >/dev/null 2>&1 || true

    # Make sure the folders exists
    mkdir -p "${UT_OUTPUT_DIR}"
    rm -rf "${UT_OUTPUT_DIR:?}"/*

    # Start up the container
    local BASE_IMAGE=dind-with-python
    local IMAGE_TAG=latest

    # shellcheck disable=SC2016
    local CMD_EXPORT_PATH=' \
        export PATH=/app/.venv/bin:${PATH} \
    '

    local CMD_PIP_INSTALL=' \
        pip install . \
    '

    local CMD_PIP_INSTALL_DEV=' \
        pip install .[dev] \
    '

    local CMD_PIP_INSTALL_ORCHESTRATE=' \
        pip install --upgrade -i https://test.pypi.org/simple/ ibm-watsonx-orchestrate==1.3.1rc497 \
    '

    local CMD_USE_LOCAL_ORCHESTRATE=' \
        pip install -e . \
    '

    local CMD_START_ORCHESTRATE=' \
        orchestrate server start -e .env --with-flow-runtime --accept-terms-and-conditions \
    '

    local CMD_ACTIVATE_ORCHESTRATE=' \
        orchestrate env activate local --registry testpypi --test-package-version-override 1.4.0rc515 \
    '
    # local CMD_RUN_PYLINT=' \
    #     pylint --disable=C,R,W --max-line-length=120 ./wdp \
    # '
    # local CMD_RUN_ISORT=' \
    #     isort ./wdp \
    # '
    # shellcheck disable=SC2016
    local CMD_MARK_START=' \
        STARTUP_TS=$(date +%s) \
    '
    # shellcheck disable=SC2016
    local CMD_MARK_END=' \
        echo Time elapsed: $(($(date +%s)-$STARTUP_TS))s \
    '

    # local CMD_CREATE_EXPECT_TEMP=' \
    #     echo "spawn sh -c \"orchestrate server start -e .env --with-flow-runtime
    # '



    local CMD=" \
        python3 -m venv ./.venv && \
        chmod 777 ./.venv/bin/activate && \
        ./.venv/bin/activate && \
        ${CMD_MARK_START} && \
        ${CMD_EXPORT_PATH} && \
        ${CMD_PIP_INSTALL} && \
        ${CMD_PIP_INSTALL_DEV} && \
        ${CMD_PIP_INSTALL_ORCHESTRATE} && \
        ${CMD_USE_LOCAL_ORCHESTRATE} && \
        ${CMD_START_ORCHESTRATE} && \
        ${CMD_ACTIVATE_ORCHESTRATE} && \
        ${CMD_MARK_END} && \
        ${RUN_CMD} \
    "

    echo $CMD

    local RC=0
    # shellcheck disable=SC2086

    # -v "${BASE_DIR}/src:${APP_HOME}/src" \
    # -v "${BASE_DIR}/tests:${APP_HOME}/tests" \
    # -v "${BASE_DIR}/.env:${APP_HOME}/.env" \
    # -v "${BASE_DIR}/pyproject.toml:${APP_HOME}/pyproject.toml" \

    if ! docker image inspect "${BASE_IMAGE}:${IMAGE_TAG}" > /dev/null 2>&1; then
        echo "Testing image ${BASE_IMAGE}:${IMAGE_TAG} not found. Building..."
        docker build -t "${BASE_IMAGE}:${IMAGE_TAG}" $(dirname "$(realpath "${BASH_SOURCE[0]}")")
    else
        echo "Testing image ${BASE_IMAGE}:${IMAGE_TAG} found!"
    fi

    docker run --privileged --rm -i ${TTY_ARG} --user root --name "${CONTAINER_NAME}" \
        -v "${BASE_DIR}/src:${APP_HOME}/src" \
        -v "${BASE_DIR}/tests:${APP_HOME}/tests" \
        -v "${BASE_DIR}/.env:${APP_HOME}/.env" \
        -v "${BASE_DIR}/pyproject.toml:${APP_HOME}/pyproject.toml" \
        -v "${BASE_DIR}/__init__.py:${APP_HOME}/__init__.py" \
        -v "${BASE_DIR}/LICENSE:${APP_HOME}/LICENSE" \
        -v "${BASE_DIR}/examples:${APP_HOME}/examples" \
        -v "${UT_OUTPUT_DIR}:${UT_OUTPUT_DIR_CONTAINER}" \
        -e APP_HOME=${APP_HOME} \
        -e PYTHONPATH=${APP_HOME} \
        -e HOME=${APP_HOME} \
        -e UT_OUTPUT_DIR_CONTAINER=${UT_OUTPUT_DIR_CONTAINER} \
        -w ${APP_HOME} \
        --entrypoint=/bin/sh \
        ${BASE_IMAGE} \
        -c "/usr/local/bin/dockerd-entrypoint.sh & while ! docker info > /dev/null 2>&1; do sleep 1; done; echo 'Dockerd is ready'; ${CMD};" ||
        RC=1

    if [ "${WITH_TTY}" != "true" ]; then
        print_success $RC
    fi
    exit $RC
}

WITH_TTY=false
RUN_CMD=
# REPORT_CMD=" \
#     --junitxml=${UT_OUTPUT_DIR_CONTAINER}/ut-${CMD_ARG}.xml || RC=\$? && \
#     junit2html ${UT_OUTPUT_DIR_CONTAINER}/ut-${CMD_ARG}.xml ${UT_OUTPUT_DIR_CONTAINER}/ut-${CMD_ARG}.html && \
#     chown -R ${HOST_UID}:${HOST_GID} ${UT_OUTPUT_DIR_CONTAINER}/* && \
#     exit \${RC:-0} \
# "

REPORT_CMD=" \
    || RC=\$? && \
    exit \${RC:-0} \
"

if [ "${CMD_ARG}" == "shell" ] || [ "${CMD_ARG}" == "sh" ]; then
    WITH_TTY=true
    RUN_CMD=/bin/sh
elif [ "${CMD_ARG}" == "all" ]; then
    RUN_CMD="pytest ${APP_HOME}/tests/integration_tests ${REPORT_CMD}"
else
    print_usage
    exit 1
fi

run_unit_test_container "${RUN_CMD}" "${WITH_TTY}"