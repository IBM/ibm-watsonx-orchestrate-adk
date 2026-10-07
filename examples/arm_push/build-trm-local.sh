#!/usr/bin/env bash
# build-trm-local.sh — Build the ARM-enabled TRM image from tools-runtime-manager
# and restart the tools-runtime-manager service in the dev-edition stack.
#
# Always recompiles the TRM binary and rebuilds the Docker image on every run.
# Skips the container restart only if the container is already running the
# freshly built image.
#
# Usage:
#   bash build-trm-local.sh --trm-dir <path> --env-file <path> [--trm-branch <branch>] [--compose-file <path>] [--wxo-cmd <path>] [--goarch <arch>]
#
# Flags:
#   --trm-dir      <path>    Path to tools-runtime-manager repo  (required)
#   --trm-branch   <branch>  Expected TRM feature branch         (default: aaron-local-validate-epic-arm-de-pe)
#   --env-file     <path>    Path to the stack .env file         (required)
#   --compose-file <path>    Path to compose-lite.yml            (default: generated local-arm-trm.yml)
#   --wxo-cmd      <path>    Path to orchestrate CLI command     (default: orchestrate)
#   --goarch       <arch>    Target architecture for Go binary   (default: autodetected or arm64/amd64)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
TRM_DIR=""
TRM_EXPECTED_BRANCH="aaron-local-validate-epic-arm-de-pe"
ENV_FILE=""
COMPOSE_FILE=""  # set after generation step unless overridden by --compose-file
WXO_CMD="${WXO_CMD:-orchestrate}"

# Autodetect GOARCH (maps x86_64 -> amd64, arm64/aarch64 -> arm64)
HOST_ARCH="$(uname -m)"
case "${HOST_ARCH}" in
  x86_64)          DEFAULT_GOARCH="amd64" ;;
  arm64|aarch64)   DEFAULT_GOARCH="arm64" ;;
  *)               DEFAULT_GOARCH="arm64" ;;
esac
TARGET_GOARCH="${GOARCH:-${DEFAULT_GOARCH}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --trm-dir)      TRM_DIR="$2";             shift 2 ;;
    --trm-branch)   TRM_EXPECTED_BRANCH="$2"; shift 2 ;;
    --env-file)     ENV_FILE="$2";            shift 2 ;;
    --compose-file) COMPOSE_FILE="$2";        shift 2 ;;
    --wxo-cmd)      WXO_CMD="$2";             shift 2 ;;
    --goarch)       TARGET_GOARCH="$2";       shift 2 ;;
    -h|--help)
      echo "Usage: $0 --trm-dir <path> --env-file <path> [--trm-branch <branch>] [--compose-file <path>] [--wxo-cmd <path>] [--goarch <arch>]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2
       echo "Usage: $0 --trm-dir <path> --env-file <path> [--trm-branch <branch>] [--compose-file <path>] [--wxo-cmd <path>] [--goarch <arch>]" >&2
       exit 1 ;;
  esac
done

[[ -n "${TRM_DIR}" ]]  || { echo "❌ --trm-dir is required" >&2; exit 1; }
[[ -n "${ENV_FILE}" ]] || { echo "❌ --env-file is required" >&2; exit 1; }

BRANCH=$(git -C "${TRM_DIR}" branch --show-current 2>/dev/null || echo "${TRM_EXPECTED_BRANCH}")
IMAGE="tools-runtime-manager:${BRANCH}"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile.trm-arm-local"

log()  { echo "[$(date +%H:%M:%S)] $*"; }
pass() { echo "  ✅ $*"; }
skip() { echo "  ⏭️  $*"; }
fail() { echo "  ❌ $*" >&2; exit 1; }

# Default compose file is the generated one; only use a custom path if --compose-file was passed
GENERATED_COMPOSE="${SCRIPT_DIR}/local-arm-trm.yml"
[[ -z "${COMPOSE_FILE}" ]] && COMPOSE_FILE="${GENERATED_COMPOSE}"

log "=== TRM ARM-local setup ==="

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
log "=== Preflight checks ==="

[[ -d "${TRM_DIR}" ]]        || fail "tools-runtime-manager not found at ${TRM_DIR}"
[[ -f "${TRM_DIR}/go.mod" ]] || fail "${TRM_DIR} doesn't look like the TRM repo (no go.mod)"
[[ -f "${ENV_FILE}" ]]       || fail "env file not found at ${ENV_FILE}"

# Check orchestrate CLI is reachable
if "${WXO_CMD}" --help > /dev/null 2>&1; then
  pass "orchestrate CLI reachable (${WXO_CMD})"
else
  fail "orchestrate CLI not found or errored: '${WXO_CMD} --help' failed. Set --wxo-cmd to the correct path."
fi

# Check python3 is usable
if python3 -c "print('hello world')" > /dev/null 2>&1; then
  pass "python3 reachable ($(python3 --version 2>&1))"
else
  fail "python3 not found or not working. Ensure python3 is on PATH."
fi

# ---------------------------------------------------------------------------
# Step 0: Generate local-arm-trm.yml from the installed default compose-lite.yml
#         (skipped if --compose-file was passed explicitly, or file already exists for this image)
# ---------------------------------------------------------------------------
if [[ "${COMPOSE_FILE}" == "${GENERATED_COMPOSE}" ]] && [[ -f "${GENERATED_COMPOSE}" ]] && grep -q "image: ${IMAGE}" "${GENERATED_COMPOSE}"; then
  skip "Step 0: ${GENERATED_COMPOSE} already exists for image '${IMAGE}' — skipping generation (delete it to regenerate)"
elif [[ "${COMPOSE_FILE}" == "${GENERATED_COMPOSE}" ]]; then
  log "=== Step 0: Generating ${GENERATED_COMPOSE} from default compose-lite.yml ==="

  python3 - "${GENERATED_COMPOSE}" "${IMAGE}" <<'PYEOF'
import sys, importlib.resources
import ibm_watsonx_orchestrate.developer_edition.resources.docker as pkg

out_path = sys.argv[1]
image    = sys.argv[2]

src = importlib.resources.files(pkg) / "compose-lite.yml"
lines = src.read_text().splitlines(keepends=True)

TRM_DEFAULT_IMAGE = "    image: ${TRM_REGISTRY:-us.icr.io/watson-orchestrate-private}/tools-runtime-manager:${TRM_TAG:-latest}\n"
TRM_PLATFORM      = "    platform: linux/amd64\n"

ARM_REGISTRY_DEPENDS = "      arm-registry:\n        condition: service_started\n"
ARM_REGISTRY_ENV = (
    '      REGISTRY_HOST: "arm-registry:5000"\n'
    '      REGISTRY_TYPE: "local"\n'
    '      REGISTRY_USERNAME: "dummy"\n'
    '      REGISTRY_PASSWORD: "dummy"\n'
    '      ARM_REGISTRY_NAMESPACE: "wxo-workloads"\n'
)
ARM_REGISTRY_SERVICE = (
    "  arm-registry:\n"
    "    image: ${OPENSOURCE_REGISTRY_PROXY:-docker.io}/registry:2\n"
    "    restart: unless-stopped\n"
    "    ports:\n"
    '      - "5000:5000"\n'
)

out = []
i = 0
in_opensearch_knowledge_service = False
in_trm_service = False   # True only while inside the tools-runtime-manager service block
trm_image_seen = False

while i < len(lines):
    line = lines[i]

    # ── Track which top-level service we are in ───────────────────────────
    if line == "  tools-runtime-manager:\n":
        in_trm_service = True
    elif line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":") and line != "  tools-runtime-manager:\n":
        in_trm_service = False

    # ── Drop wxo-opensearch-knowledge service block ──────────────────────
    if line == "  wxo-opensearch-knowledge:\n":
        in_opensearch_knowledge_service = True
        i += 1
        continue
    if in_opensearch_knowledge_service:
        # Service blocks end at the next top-level service (2-space indent key)
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip() != "" and not line.startswith("  #"):
            in_opensearch_knowledge_service = False
            # fall through to process this line normally
        else:
            i += 1
            continue

    # ── Drop wxo-opensearch-knowledge-data volume ─────────────────────────
    if line == "  wxo-opensearch-knowledge-data:\n":
        i += 1
        continue

    # ── Drop ALLOW_PRIVATE_SEARCH_IP ─────────────────────────────────────
    if line.strip() == "ALLOW_PRIVATE_SEARCH_IP: true":
        i += 1
        continue

    # ── Drop wxo-opensearch-knowledge depends_on entry (3 lines) ─────────
    if line == "      wxo-opensearch-knowledge:\n":
        if i + 2 < len(lines) and "condition: service_healthy" in lines[i+1] and "required: False" in lines[i+2]:
            i += 3
            continue

    # ── Drop OPENSEARCH_* env vars (only the ones referencing wxo-opensearch-knowledge) ──
    stripped = line.lstrip()
    if stripped.startswith("OPENSEARCH_VERIFY_CERTS: ${OPENSEARCH_VERIFY_CERTS"):
        i += 1
        continue
    if stripped.startswith("OPENSEARCH_USERNAME:"):
        i += 1
        continue
    if stripped.startswith("OPENSEARCH_PASSWORD:"):
        i += 1
        continue
    if stripped.startswith("OPENSEARCH_URL:") and "wxo-opensearch-knowledge" in line:
        i += 1
        continue

    # ── Swap TRM image line ───────────────────────────────────────────────
    if line == TRM_DEFAULT_IMAGE:
        out.append(f"    image: {image}\n")
        trm_image_seen = True
        i += 1
        continue

    # ── Swap platform → pull_policy (line immediately after new TRM image) ─
    if trm_image_seen and line == TRM_PLATFORM:
        out.append("    pull_policy: never\n")
        trm_image_seen = False
        i += 1
        continue
    if trm_image_seen:
        trm_image_seen = False  # next line wasn't platform, move on

    # ── Inject arm-registry depends_on after wxo-server-db condition line ─
    # (only inside tools-runtime-manager — it's the only service with this exact comment)
    if in_trm_service and line.strip() == "condition: service_healthy # Ensures DB is ready before starting":
        out.append(line)
        out.append(ARM_REGISTRY_DEPENDS)
        i += 1
        continue

    # ── Inject ARM registry env vars before extra_hosts (TRM service only) ─
    if in_trm_service and line == "    extra_hosts:\n":
        out.append(ARM_REGISTRY_ENV)

    # ── Inject arm-registry service before top-level volumes: block ───────
    if line == "volumes:\n":
        # Default compose has two blank lines before volumes:. Pop the last one
        # so arm-registry sits after the first blank, then restore two blanks
        # before volumes:  =>  \n  arm-registry  \n\n  volumes:
        if out and out[-1] == "\n":
            out.pop()
        out.append(ARM_REGISTRY_SERVICE)
        out.append("\n")
        out.append("\n")

    out.append(line)
    i += 1

with open(out_path, "w") as f:
    f.writelines(out)
PYEOF

  [[ -f "${GENERATED_COMPOSE}" ]] || fail "Failed to generate ${GENERATED_COMPOSE}"
  pass "Generated ${GENERATED_COMPOSE}"
else
  log "Using custom compose file: ${COMPOSE_FILE}"
  [[ -f "${COMPOSE_FILE}" ]] || fail "compose-lite.yml not found at ${COMPOSE_FILE}"
fi

# Warn if not on the ARM feature branch
if [[ "${BRANCH}" != "${TRM_EXPECTED_BRANCH}" ]]; then
  echo "  ⚠️  TRM branch is '${BRANCH}', expected '${TRM_EXPECTED_BRANCH}'"
  echo "     Switch with: git -C ${TRM_DIR} checkout ${TRM_EXPECTED_BRANCH}"
  read -rp "  Continue anyway? [y/N] " ans
  [[ "${ans}" =~ ^[Yy]$ ]] || exit 1
fi

TRM_HEAD=$(git -C "${TRM_DIR}" rev-parse --short HEAD 2>/dev/null || echo "unknown")

log "=== Step 1: Compile TRM binary on host ==="
log "Compiling for GOOS=linux GOARCH=${TARGET_GOARCH}..."
CGO_ENABLED=0 GOOS=linux GOARCH="${TARGET_GOARCH}" go build -C "${TRM_DIR}" -o "${TRM_DIR}/main" .
pass "Binary compiled: ${TRM_DIR}/main (GOARCH=${TARGET_GOARCH})"

log "=== Step 2: Build Docker image ${IMAGE} ==="
docker build \
  -f "${DOCKERFILE}" \
  --label "git.commit=${TRM_HEAD}" \
  -t "${IMAGE}" \
  "${TRM_DIR}"

rm -f "${TRM_DIR}/main"
pass "Image built: ${IMAGE} (commit ${TRM_HEAD})"

# ----------------------------------------------------------------------------
# Step 3: Restart orchestrate server with ARM preview enabled
# ----------------------------------------------------------------------------
log "=== Step 3: Restarting orchestrate server with ARM preview ==="
log "Stopping orchestrate server..."
"${WXO_CMD}" server stop || log "⚠️ orchestrate server stop returned non-zero (server may not have been running)."

log "Starting orchestrate server with --preview-arm, --compose-file, and --env-file..."
"${WXO_CMD}" server start \
  --preview-arm \
  --compose-file "${COMPOSE_FILE}" \
  --env-file "${ENV_FILE}" \
  < /dev/tty
pass "orchestrate server started with ARM TRM image"

echo ""
echo "  ──────────────────────────────────────────────────────────"
echo "  ARM TRM build and server restart complete."
echo "  Run the test:"
echo "    bash ${SCRIPT_DIR}/test_arm_push.sh"
echo "  ──────────────────────────────────────────────────────────"
