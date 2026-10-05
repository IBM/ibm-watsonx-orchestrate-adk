#!/usr/bin/env bash
# =============================================================================
# test_arm_push.sh — Idempotent end-to-end test for the ADK ARM image-push feature.
#
# Tests both upload methods:
#   1. S3 method   — build a Docker image, export to .tar, push via presigned URL
#   2. Registry method — bind a remote OCI image reference directly
#
# Usage:
#   export ARM_SERVER_URL=http://localhost:8080/api   # or dev-conn URL
#   export FEATURE_ARM_PUSH=true
#   bash examples/arm_push/test_arm_push.sh
#
# Idempotency: each run uses a timestamp-based tag (e.g. v-20261005-143022) so
# repeated runs never collide with an existing tag.  The workload name is fixed
# so ARM accumulates versions rather than creating duplicates.
#
# Prerequisites: docker, wxo-dev (ADK CLI), jq
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configurable defaults — override via environment variables
# ---------------------------------------------------------------------------
ARM_SERVER_URL="${ARM_SERVER_URL:-http://localhost:8080/api}"
FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH:-true}"
WORKLOAD_NAME="${WORKLOAD_NAME:-arm-test-agent}"
WORKLOAD_TYPE="${WORKLOAD_TYPE:-agent}"
IMAGE_NAME="arm-test-agent:latest"
ARCHIVE_PATH="${ARCHIVE_PATH:-/tmp/arm-test-agent.tar}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE_DIR="${SCRIPT_DIR}/agent-image"

# Timestamp-based tag ensures idempotency across repeated runs
TAG="v-$(date +%Y%m%d-%H%M%S)"

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
require_cmd jq

[[ "${FEATURE_ARM_PUSH}" == "true" ]] || fail "FEATURE_ARM_PUSH must be 'true'"
[[ -n "${ARM_SERVER_URL}" ]]          || fail "ARM_SERVER_URL must be set"
pass "All prerequisites met"
pass "ARM_SERVER_URL = ${ARM_SERVER_URL}"
pass "TAG            = ${TAG}"

# ---------------------------------------------------------------------------
# Step 1: Build the test agent Docker image
# ---------------------------------------------------------------------------
log "=== Step 1: Build Docker image ==="
docker build -t "${IMAGE_NAME}" "${DOCKERFILE_DIR}"
pass "Built ${IMAGE_NAME}"

# ---------------------------------------------------------------------------
# Step 2: Export image to a tar archive (S3 method requires a local archive)
# ---------------------------------------------------------------------------
log "=== Step 2: Export image to tar ==="
docker save "${IMAGE_NAME}" -o "${ARCHIVE_PATH}"
ARCHIVE_SIZE_MB=$(du -m "${ARCHIVE_PATH}" | cut -f1)
pass "Exported ${ARCHIVE_PATH} (${ARCHIVE_SIZE_MB} MB)"

# ---------------------------------------------------------------------------
# Step 3: S3 push — upload archive via presigned URL, then register workload
# ---------------------------------------------------------------------------
log "=== Step 3: S3 push (source-type=s3) ==="
S3_TAG="${TAG}-s3"

ARM_SERVER_URL="${ARM_SERVER_URL}" \
FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH}" \
wxo-dev runtime push-image \
  --image        "${ARCHIVE_PATH}" \
  --name         "${WORKLOAD_NAME}" \
  --type         "${WORKLOAD_TYPE}" \
  --tag          "${S3_TAG}" \
  --source-type  s3 \
  --description  "ARM integration test — S3 method" \
  --version-description "Automated test run ${S3_TAG}"

pass "S3 push completed for tag ${S3_TAG}"

# ---------------------------------------------------------------------------
# Step 4: Registry push — bind a public OCI image reference directly
# ---------------------------------------------------------------------------
log "=== Step 4: Registry push (source-type=registry) ==="
REGISTRY_TAG="${TAG}-registry"

# Uses the same image published to a registry.
# Substitute SOURCE_IMAGE with your own registry reference when testing
# against a private registry; also supply --app-id <connection_id>.
SOURCE_IMAGE="${SOURCE_IMAGE:-docker.io/library/hello-world:latest}"

ARM_SERVER_URL="${ARM_SERVER_URL}" \
FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH}" \
wxo-dev runtime push-image \
  --image        "${SOURCE_IMAGE}" \
  --name         "${WORKLOAD_NAME}-registry" \
  --type         "${WORKLOAD_TYPE}" \
  --tag          "${REGISTRY_TAG}" \
  --source-type  registry \
  --description  "ARM integration test — registry method" \
  --version-description "Automated test run ${REGISTRY_TAG}"

pass "Registry push completed for tag ${REGISTRY_TAG}"

# ---------------------------------------------------------------------------
# Step 5: Cleanup
# ---------------------------------------------------------------------------
log "=== Step 5: Cleanup ==="
rm -f "${ARCHIVE_PATH}"
pass "Removed ${ARCHIVE_PATH}"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log "=== All steps passed ==="
echo ""
echo "  Workload (S3):       ${WORKLOAD_NAME}:${S3_TAG}"
echo "  Workload (registry): ${WORKLOAD_NAME}-registry:${REGISTRY_TAG}"
echo ""
