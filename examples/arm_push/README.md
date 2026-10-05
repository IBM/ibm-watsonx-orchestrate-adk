# ARM Push — Integration Test

End-to-end test for the ADK ARM image-push feature ([#88741](https://github.ibm.com/WatsonOrchestrate/wo-tracker/issues/88741)).

## Contents

```
examples/arm_push/
├── agent-image/
│   ├── Dockerfile        # Minimal UBI9-based agent image
│   ├── agent.py          # Stub Flask agent with /health endpoint
│   └── requirements.txt  # flask>=3.0.0
└── test_arm_push.sh      # Idempotent end-to-end test script
```

## Prerequisites

- `docker`
- `wxo-dev` (ADK CLI, built from this branch with `FEATURE_ARM_PUSH=true`)
- `jq`
- Access to a running ARM server (local or dev-conn)

## Usage

```bash
# Local ARM server
export ARM_SERVER_URL=http://localhost:8080/api
export FEATURE_ARM_PUSH=true
bash examples/arm_push/test_arm_push.sh

# dev-conn (once access is granted)
export ARM_SERVER_URL=https://<dev-conn-host>/api
export FEATURE_ARM_PUSH=true
bash examples/arm_push/test_arm_push.sh
```

## What the script does

| Step | Description |
|------|-------------|
| 1 | Builds the `agent-image/` Dockerfile into a local Docker image |
| 2 | Exports the image to a `.tar` archive (`/tmp/arm-test-agent.tar`) |
| 3 | **S3 push** — calls `wxo-dev runtime push-image --source-type s3`, which: obtains a presigned URL from ARM, streams the archive to S3, then calls ARM to copy into the cluster registry |
| 4 | **Registry push** — calls `wxo-dev runtime push-image --source-type registry` to bind a public OCI reference directly |
| 5 | Cleans up the local tar archive |

## Idempotency

Each run generates a timestamp-based tag (e.g. `v-20261005-143022-s3`) so repeated runs never collide with an existing tag. The workload name is fixed (`arm-test-agent`) so ARM accumulates versions rather than creating duplicates.

## Overridable environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARM_SERVER_URL` | `http://localhost:8080/api` | ARM server base URL |
| `FEATURE_ARM_PUSH` | `true` | Must be `true` to enable the CLI commands |
| `WORKLOAD_NAME` | `arm-test-agent` | Workload name registered with ARM |
| `WORKLOAD_TYPE` | `agent` | One of: `agent`, `mcp_toolkit`, `guardrails`, `eval` |
| `SOURCE_IMAGE` | `docker.io/library/hello-world:latest` | OCI image reference for the registry push step |
