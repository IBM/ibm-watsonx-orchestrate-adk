#!/usr/bin/env bash
# =============================================================================
# test_arm_push.sh — Idempotent local validation test for the ADK ARM image-push
# feature (S3 method).
#
# Reproduces the local validation workflow confirmed by Aaron Nguyen:
#   Step 1: Build a Docker image and export it to a .tar archive
#   Step 2: wxo-dev runtime push-image --source-type s3
#           → POST /arm/v1/upload_files/{filename}  (get presigned S3 URL)
#           → PUT  <presigned_url>                   (stream archive to S3)
#           → POST /arm/v1/workloads                 (ARM copies image to registry)
#
# Usage:
#   export ARM_SERVER_URL=http://localhost:8080/api/v1   # local ARM default
#   export FEATURE_ARM_PUSH=true
#   export WO_API_KEY=<your-token>
#   bash examples/arm_push/test_arm_push.sh
#
# Idempotency: each run uses a timestamp-based tag (e.g. v-20261005-143022-s3)
# so repeated runs never collide with an existing tag.
#
# Prerequisites: docker, wxo-dev (ADK CLI built from this branch)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configurable defaults — override via environment variables
# ---------------------------------------------------------------------------
ARM_SERVER_URL="${ARM_SERVER_URL:-http://localhost:8080/api/v1}"
FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH:-true}"
WORKLOAD_NAME="${WORKLOAD_NAME:-arm-test-agent}"
WORKLOAD_TYPE="${WORKLOAD_TYPE:-agent}"
IMAGE_NAME="arm-test-agent:latest"
ARCHIVE_PATH="${ARCHIVE_PATH:-/tmp/arm-test-agent.tar}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE_DIR="${SCRIPT_DIR}/agent-image"

# Timestamp-based tag ensures idempotency across repeated runs
TAG="v-$(date +%Y%m%d-%H%M%S)-s3"

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
require_cmd wxo-dev

[[ "${FEATURE_ARM_PUSH}" == "true" ]] || fail "FEATURE_ARM_PUSH must be 'true'"
[[ -n "${ARM_SERVER_URL}" ]]          || fail "ARM_SERVER_URL must be set"
pass "All prerequisites met"
pass "ARM_SERVER_URL = ${ARM_SERVER_URL}"
pass "WORKLOAD_NAME  = ${WORKLOAD_NAME}"
pass "TAG            = ${TAG}"

# ---------------------------------------------------------------------------
# Step 1: Build the test agent Docker image
# ---------------------------------------------------------------------------
log "=== Step 1: Build Docker image ==="
log "Running: docker build -t ${IMAGE_NAME} ${DOCKERFILE_DIR}"
docker build -t "${IMAGE_NAME}" "${DOCKERFILE_DIR}"
pass "Built ${IMAGE_NAME}"

# ---------------------------------------------------------------------------
# Step 2: Export image to a tar archive
# ---------------------------------------------------------------------------
log "=== Step 2: Export image to tar ==="
log "Running: docker save ${IMAGE_NAME} -o ${ARCHIVE_PATH}"
docker save "${IMAGE_NAME}" -o "${ARCHIVE_PATH}"
ARCHIVE_SIZE_MB=$(du -m "${ARCHIVE_PATH}" | cut -f1)
pass "Exported ${ARCHIVE_PATH} (${ARCHIVE_SIZE_MB} MB)"

# ---------------------------------------------------------------------------
# Step 3: S3 push via ADK CLI
# ---------------------------------------------------------------------------
log "=== Step 3: S3 push ==="

CMD="wxo-dev runtime push-image \
  --image        ${ARCHIVE_PATH} \
  --name         ${WORKLOAD_NAME} \
  --type         ${WORKLOAD_TYPE} \
  --tag          ${TAG} \
  --source-type  s3 \
  --description  \"ARM local validation — S3 method\" \
  --version-description \"Automated test run ${TAG}\""

log "Running: ARM_SERVER_URL=${ARM_SERVER_URL} FEATURE_ARM_PUSH=${FEATURE_ARM_PUSH} ${CMD}"

ARM_SERVER_URL="${ARM_SERVER_URL}" \
FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH}" \
wxo-dev runtime push-image \
  --image        "${ARCHIVE_PATH}" \
  --name         "${WORKLOAD_NAME}" \
  --type         "${WORKLOAD_TYPE}" \
  --tag          "${TAG}" \
  --source-type  s3 \
  --description  "ARM local validation — S3 method" \
  --version-description "Automated test run ${TAG}"

pass "S3 push completed for tag ${TAG}"

# ---------------------------------------------------------------------------
# Step 4: Cleanup
# ---------------------------------------------------------------------------
log "=== Step 4: Cleanup ==="
rm -f "${ARCHIVE_PATH}"
pass "Removed ${ARCHIVE_PATH}"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log "=== All steps passed ==="
echo ""
echo "  Workload: ${WORKLOAD_NAME}:${TAG}"
echo "  ARM URL:  ${ARM_SERVER_URL}/arm/v1/workloads"
echo ""
