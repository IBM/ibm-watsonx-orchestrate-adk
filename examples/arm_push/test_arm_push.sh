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
#   bash examples/arm_push/test_arm_push.sh [OPTIONS] [s3|registry|all]
#
# Options:
#   --mode <s3|registry|all>       Execution mode (default: all)
#   --server-url <url>             ARM server URL (default: http://localhost:8080/api/v1)
#   --workload-name <name>         Workload name (default: arm-test-agent)
#   --workload-type <type>         Workload type (default: agent)
#   --source-image <image>         OCI image for registry push (default: docker.io/library/hello-world:latest)
#   --archive-path <path>          Path for exported tar archive (default: /tmp/arm-test-agent.tar)
#   --wxo-cmd <cmd>                CLI executable (default: orchestrate)
#   --skip-context-check           Skip checking/switching Docker context
#   -h, --help                     Show this help message
#
# All options can also be supplied via environment variables (ARM_SERVER_URL, WORKLOAD_NAME, etc.).
# Command-line arguments take precedence over environment variables.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE_DIR="${SCRIPT_DIR}/agent-image"

# ---------------------------------------------------------------------------
# Configurable defaults — override via environment variables or CLI flags
# ---------------------------------------------------------------------------
MODE="${MODE:-all}"
ARM_SERVER_URL="${ARM_SERVER_URL:-http://localhost:8080/api/v1}"
FEATURE_ARM_PUSH="${FEATURE_ARM_PUSH:-true}"
WORKLOAD_NAME="${WORKLOAD_NAME:-arm-test-agent}"
WORKLOAD_TYPE="${WORKLOAD_TYPE:-agent}"
IMAGE_NAME="arm-test-agent:latest"
ARCHIVE_PATH="${ARCHIVE_PATH:-/tmp/arm-test-agent.tar}"
SOURCE_IMAGE="${SOURCE_IMAGE:-docker.io/library/hello-world:latest}"
WXO_CMD="${WXO_CMD:-orchestrate}"
ORCHESTRATE_DOCKER_CONTEXT="${ORCHESTRATE_DOCKER_CONTEXT:-lima-ibm-watsonx-orchestrate}"
SKIP_CONTEXT_CHECK="${SKIP_CONTEXT_CHECK:-false}"

# Timestamp-based tag ensures idempotency across repeated runs
TAG="v-$(date +%Y%m%d-%H%M%S)"

# ---------------------------------------------------------------------------
# CLI Argument parsing
# ---------------------------------------------------------------------------
show_usage() {
  cat <<EOF
Usage: $0 [OPTIONS] [s3|registry|all]

Arguments:
  s3 | registry | all             Push mode to test (positional or via --mode, default: all)

Options:
  --mode <s3|registry|all>       Execution mode
  --server-url <url>             ARM server URL (env: ARM_SERVER_URL)
  --workload-name <name>         Workload name (env: WORKLOAD_NAME)
  --workload-type <type>         Workload type: agent|mcp_toolkit|guardrails|eval
  --source-image <image>         Remote OCI image for registry mode (env: SOURCE_IMAGE)
  --archive-path <path>          Tar export path for s3 mode (env: ARCHIVE_PATH)
  --wxo-cmd <path/name>          ADK CLI command (env: WXO_CMD, default: orchestrate)
  --skip-context-check           Skip Docker context validation
  -h, --help                     Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    s3|registry|all)
      MODE="$1"
      shift
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --server-url)
      ARM_SERVER_URL="$2"
      shift 2
      ;;
    --workload-name)
      WORKLOAD_NAME="$2"
      shift 2
      ;;
    --workload-type)
      WORKLOAD_TYPE="$2"
      shift 2
      ;;
    --source-image)
      SOURCE_IMAGE="$2"
      shift 2
      ;;
    --archive-path)
      ARCHIVE_PATH="$2"
      shift 2
      ;;
    --wxo-cmd)
      WXO_CMD="$2"
      shift 2
      ;;
    --skip-context-check)
      SKIP_CONTEXT_CHECK="true"
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo "❌ Unknown argument: $1" >&2
      show_usage >&2
      exit 1
      ;;
  esac
done

if [[ "${MODE}" != "s3" && "${MODE}" != "registry" && "${MODE}" != "all" ]]; then
  echo "❌ Invalid mode '${MODE}'. Expected 's3', 'registry', or 'all'." >&2
  exit 1
fi

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

# Ensure Docker is pointing at the orchestrate context if context check enabled
if [[ "${SKIP_CONTEXT_CHECK}" != "true" ]]; then
  CURRENT_CONTEXT=$(docker context show 2>/dev/null || echo "default")
  if [[ "${CURRENT_CONTEXT}" != "${ORCHESTRATE_DOCKER_CONTEXT}" ]]; then
    log "Docker context is '${CURRENT_CONTEXT}', switching to '${ORCHESTRATE_DOCKER_CONTEXT}'..."
    docker context use "${ORCHESTRATE_DOCKER_CONTEXT}" 2>/dev/null \
      || log "⚠️ Could not switch context to '${ORCHESTRATE_DOCKER_CONTEXT}'. Continuing with '${CURRENT_CONTEXT}'..."
  else
    pass "Docker context is ${ORCHESTRATE_DOCKER_CONTEXT}"
  fi
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
  local cmd="${WXO_CMD} runtime push-image \
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
  "${WXO_CMD}" runtime push-image \
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
  local cmd="${WXO_CMD} runtime push-image \
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
  "${WXO_CMD}" runtime push-image \
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
