#!/usr/bin/env bash
# =============================================================================
# test_arm_push.sh — Idempotent local/SaaS validation test for the ADK ARM
# image-push feature.
#
# Supports three modes:
#   s3        — build a Docker image, export to .tar, push via presigned S3 URL
#   registry  — bind a remote OCI image reference directly
#   all       — run both s3 and registry (default)
#
# Usage:
#   bash examples/arm_push/test_arm_push.sh [s3|registry|all]
#
#   export ARM_SERVER_URL=http://localhost:8080/api/v1   # local ARM default
#   export FEATURE_ARM_PUSH=true
#   export WO_API_KEY=<your-token>
#
# Idempotency: each run uses a timestamp-based tag (e.g. v-20261005-143022)
# so repeated runs never collide with an existing tag.
#
# Prerequisites: docker, orchestrate (ADK CLI), jq
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Mode argument: s3 | registry | all (default: all)
# ---------------------------------------------------------------------------
MODE="${1:-all}"
if [[ "${MODE}" != "s3" && "${MODE}" != "registry" && "${MODE}" != "all" ]]; then
  echo "Usage: $0 [s3|registry|all]" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Configurable defaults — override via environment variables
# ---------------------------------------------------------------------------
ARM_SERVER_URL="${ARM_SERVER_URL:-http://localhost:8080/api/v1}"
FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH:-true}"
WORKLOAD_NAME="${WORKLOAD_NAME:-arm-test-agent}"
WORKLOAD_TYPE="${WORKLOAD_TYPE:-agent}"
IMAGE_NAME="arm-test-agent:latest"
ARCHIVE_PATH="${ARCHIVE_PATH:-/tmp/arm-test-agent.tar}"
SOURCE_IMAGE="${SOURCE_IMAGE:-docker.io/library/hello-world:latest}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE_DIR="${SCRIPT_DIR}/agent-image"

# Timestamp-based tag ensures idempotency across repeated runs
TAG="v-$(date +%Y%m%d-%H%M%S)"

# Docker context that orchestrate uses (created by the embedded lima binary)
ORCHESTRATE_DOCKER_CONTEXT="ibm-watsonx-orchestrate"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "[$(date +%H:%M:%S)] $*"; }
pass() { echo "  ✅ $*"; }
fail() { echo "  ❌ $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" &>/dev/null || fail "Required command not found: $1"
}

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
log "=== Preflight ==="
require_cmd docker
require_cmd orchestrate
require_cmd jq

[[ "${FEATURE_ARM_PUSH}" == "true" ]] || fail "FEATURE_ARM_PUSH must be 'true'"
[[ -n "${ARM_SERVER_URL}" ]]          || fail "ARM_SERVER_URL must be set"

# Ensure Docker is pointing at the orchestrate context so that images built
# here are visible to the containers orchestrate manages.
CURRENT_CONTEXT=$(docker context show)
if [[ "${CURRENT_CONTEXT}" != "${ORCHESTRATE_DOCKER_CONTEXT}" ]]; then
  log "Docker context is '${CURRENT_CONTEXT}', switching to '${ORCHESTRATE_DOCKER_CONTEXT}'..."
  docker context use "${ORCHESTRATE_DOCKER_CONTEXT}" \
    || fail "Could not switch Docker context to '${ORCHESTRATE_DOCKER_CONTEXT}'. Is the orchestrate server running?"
  pass "Docker context switched to ${ORCHESTRATE_DOCKER_CONTEXT}"
else
  pass "Docker context is ${ORCHESTRATE_DOCKER_CONTEXT}"
fi

pass "All prerequisites met"
pass "ARM_SERVER_URL = ${ARM_SERVER_URL}"
pass "WORKLOAD_NAME  = ${WORKLOAD_NAME}"
pass "MODE           = ${MODE}"
pass "TAG            = ${TAG}"

# ---------------------------------------------------------------------------
# S3 push steps
# ---------------------------------------------------------------------------
run_s3_push() {
  local s3_tag="${TAG}-s3"

  log "=== [S3] Step 1: Build Docker image ==="
  log "Running: docker build -t ${IMAGE_NAME} ${DOCKERFILE_DIR}"
  docker build -t "${IMAGE_NAME}" "${DOCKERFILE_DIR}"
  pass "Built ${IMAGE_NAME}"

  log "=== [S3] Step 2: Export image to tar ==="
  log "Running: docker save ${IMAGE_NAME} -o ${ARCHIVE_PATH}"
  docker save "${IMAGE_NAME}" -o "${ARCHIVE_PATH}"
  ARCHIVE_SIZE_MB=$(du -m "${ARCHIVE_PATH}" | cut -f1)
  pass "Exported ${ARCHIVE_PATH} (${ARCHIVE_SIZE_MB} MB)"

  log "=== [S3] Step 3: Push via ADK CLI ==="
  local cmd="orchestrate runtime push-image \
  --image        ${ARCHIVE_PATH} \
  --name         ${WORKLOAD_NAME} \
  --type         ${WORKLOAD_TYPE} \
  --tag          ${s3_tag} \
  --source-type  s3 \
  --description  \"ARM validation — S3 method\" \
  --version-description \"Automated test run ${s3_tag}\""
  log "Running: ARM_SERVER_URL=${ARM_SERVER_URL} FEATURE_ARM_PUSH=${FEATURE_ARM_PUSH} ${cmd}"

  ARM_SERVER_URL="${ARM_SERVER_URL}" \
  FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH}" \
  orchestrate runtime push-image \
    --image        "${ARCHIVE_PATH}" \
    --name         "${WORKLOAD_NAME}" \
    --type         "${WORKLOAD_TYPE}" \
    --tag          "${s3_tag}" \
    --source-type  s3 \
    --description  "ARM validation — S3 method" \
    --version-description "Automated test run ${s3_tag}"

  pass "S3 push completed for tag ${s3_tag}"

  log "=== [S3] Step 4: Cleanup ==="
  rm -f "${ARCHIVE_PATH}"
  pass "Removed ${ARCHIVE_PATH}"
}

# ---------------------------------------------------------------------------
# Registry push steps
# ---------------------------------------------------------------------------
run_registry_push() {
  local registry_tag="${TAG}-registry"

  log "=== [Registry] Step 1: Push via ADK CLI ==="
  local cmd="orchestrate runtime push-image \
  --image        ${SOURCE_IMAGE} \
  --name         ${WORKLOAD_NAME}-registry \
  --type         ${WORKLOAD_TYPE} \
  --tag          ${registry_tag} \
  --source-type  registry \
  --description  \"ARM validation — registry method\" \
  --version-description \"Automated test run ${registry_tag}\""
  log "Running: ARM_SERVER_URL=${ARM_SERVER_URL} FEATURE_ARM_PUSH=${FEATURE_ARM_PUSH} ${cmd}"

  ARM_SERVER_URL="${ARM_SERVER_URL}" \
  FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH}" \
  orchestrate runtime push-image \
    --image        "${SOURCE_IMAGE}" \
    --name         "${WORKLOAD_NAME}-registry" \
    --type         "${WORKLOAD_TYPE}" \
    --tag          "${registry_tag}" \
    --source-type  registry \
    --description  "ARM validation — registry method" \
    --version-description "Automated test run ${registry_tag}"

  pass "Registry push completed for tag ${registry_tag}"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
case "${MODE}" in
  s3)
    run_s3_push
    ;;
  registry)
    run_registry_push
    ;;
  all)
    run_s3_push
    run_registry_push
    ;;
esac

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log "=== All steps passed ==="
echo ""
if [[ "${MODE}" == "s3" || "${MODE}" == "all" ]]; then
  echo "  Workload (S3):       ${WORKLOAD_NAME}:${TAG}-s3"
fi
if [[ "${MODE}" == "registry" || "${MODE}" == "all" ]]; then
  echo "  Workload (registry): ${WORKLOAD_NAME}-registry:${TAG}-registry"
fi
echo "  ARM URL:  ${ARM_SERVER_URL}/arm/v1/workloads"
echo ""
