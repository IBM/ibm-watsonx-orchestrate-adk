# Using IBM Cloud Pak for Data (CPD)

This guide shows how to run the evaluation framework using CPD with:
- no IFM: uses watsonx.ai for inference provider while authenticating via CPD
- IFM: uses your CPD Inferencing Foundation Models (IFM) for inference provider

You can run either scenario by setting the appropriate environment variables and using the provided configs.

## Quick links:
- Example env files: ./env/.env.cpd.no_ifm.example, ./env/.env.cpd.ifm.example
- Example configs: ./configs/config_cpd_no_ifm.yaml, ./configs/config_cpd_ifm.yaml
- Example run scripts: ./run/run_cpd_no_ifm.sh, ./run/run_cpd_ifm.sh

Note: For CPD, you must specify exactly one of WO_PASSWORD or WO_API_KEY (not both).

## Prerequisites

- A working CPD instance URL and credentials
- For the "no IFM" path, a watsonx.ai Space and API key
- For the CPD IFM path, a CPD IFM Space ID (no watsonx.ai API key required)

## Folder Structure

- env/
  - .env.cpd.no_ifm.example: Example variables for CPD without IFM
  - .env.cpd.ifm.example: Example variables for CPD with IFM
- configs/
  - config_cpd_no_ifm.yaml: Evaluation config for CPD (no IFM)
  - config_cpd_ifm.yaml: Evaluation config for CPD with IFM
- run/
  - run_cpd_no_ifm.sh: Convenience script to run the evaluation for no IFM
  - run_cpd_ifm.sh: Convenience script to run the evaluation for IFM

## Scenario 1: CPD (no IFM)

In this scenario, you authenticate to CPD, while evaluation inference is performed using watsonx.ai.

### 1. Set environment variables

Use `./env/.env.cpd.no_ifm.example` as a reference, or export the variables manually:

```bash
export WO_INSTANCE=<your-instance-url>  # e.g. https://cpd-cpd-instance-1.apps.mydomain.cp.fyre.ibm.com/orchestrate/cpd-instance-1/instances/yourinstance
export WO_USERNAME=<your-username>      # e.g. cpadmin

# Choose exactly one:
export WO_PASSWORD=<your-password>
# or
export WO_API_KEY=<your-api-key>

# watsonx.ai inference
export WATSONX_SPACE_ID="<your-watsonx-space-id>"
export WATSONX_APIKEY="<your-watsonx-api-key>"

# Optional: disable SSL verification for private/self-signed CPD instances
export WO_SSL_VERIFY="false"
```

> Important: Set exactly one of `WO_PASSWORD` or `WO_API_KEY`, not both.

Note: This setup uses watsonx.ai as the inference provider for the agent evaluator.

### 2. Use the config file

```text
./configs/config_cpd_no_ifm.yaml
```

### 3. Run the evaluation

From the repository root:

```bash
orchestrate evaluations evaluate --config examples/evaluations/cpd/configs/config_cpd_no_ifm.yaml
```

Or use the helper script:

```bash
./examples/evaluations/cpd/run/run_cpd_no_ifm.sh
```

## Scenario 2: CPD with IFM

In this scenario, you authenticate to CPD, while evaluation inference is performed by CPD IFM.

### 1. Set environment variables

Use `./env/.env.cpd.ifm.example` as a reference, or export the variables manually:

```bash
export WATSONX_SPACE_ID="<your-cpd-ifm-space-id>"
export WO_INSTANCE=<your-instance-url>     # e.g. https://cpd-cpd-instance-1.apps.mydomain.cp.fyre.ibm.com/orchestrate/cpd-instance-1/instances/yourinstance
export WO_USERNAME=<your-cpd-username>     # e.g. cpadmin

# Choose exactly one:
export WO_PASSWORD=<your-cpd-password>
# or
export WO_API_KEY=<your-cpd-api-key>

# Optional: disable SSL verification for private/self-signed CPD instances
export WO_SSL_VERIFY="false"

# Optional: model override if your CPD IFM exposes only one or a limited set of models
export MODEL_OVERRIDE="groq/openai/gpt-oss-120b"
```

> Important: Set exactly one of `WO_PASSWORD` or `WO_API_KEY`, not both.

Note: This setup uses CPD IFM as the inference provider for the agent evaluator.

### 2. Use the config file

```text
./configs/config_cpd_ifm.yaml
```

### 3. Run the evaluation

From the repository root:

```bash
orchestrate evaluations evaluate --config examples/evaluations/cpd/configs/config_cpd_ifm.yaml
```

Or use the helper script:

```bash
bash examples/evaluations/cpd/run/run_cpd_ifm.sh
```

## Sample Configuration files
Both configurations below point test_paths to existing sample datasets so you can verify the integration immediately.

### examples/evaluations/cpd/configs/config_cpd_no_ifm.yaml
```
test_paths:
  - examples/evaluations/evaluate/data_simple.json

auth_config:
  url: https://cpd-cpd-instance-1.apps.mydomain.cp.fyre.ibm.com/orchestrate/cpd-instance-1/instances/yourinstance
  tenant_name: cpd

provider_config:
  provider: "model_proxy"
  model_id: "groq/openai/gpt-oss-120b"

output_dir: "debug-cpd-no-ifm"
enable_verbose_logging: true
```

### examples/evaluations/cpd/configs/config_cpd_ifm.yaml
```
test_paths:
  - examples/evaluations/evaluate/data_simple.json

auth_config:
  url: https://cpd-cpd-instance-1.apps.mydomain.cp.fyre.ibm.com/orchestrate/cpd-instance-1/instances/yourinstance
  tenant_name: cpdifm

provider_config:
  provider: "model_proxy"
  model_id: "groq/openai/gpt-oss-120b"  # May be overridden by $MODEL_OVERRIDE

output_dir: "debug-cpd-ifm"
enable_verbose_logging: true
```

Tip:

If your IFM environment only exposes a single model, use MODEL_OVERRIDE
to force that model at runtime.


## Environment variables reference

| Variable | CPD (no IFM) | CPD with IFM | Example Notes |
|----------|----------------|--------------|---------------|
| WO_INSTANCE | Required | Required | https://cpd.../orchestrate/cpd-instance-1/instances/yourinstance | Your CPD instance URL |
| WO_USERNAME | Required | Required | cpadmin | CPD username |
| WO_PASSWORD | Either/Or | Either/Or | ******** | Use exactly one of WO_PASSWORD or WO_API_KEY |
| WO_API_KEY | Either/Or | Either/Or | ******** | Use exactly one of WO_PASSWORD or WO_API_KEY |
| WO_SSL_VERIFY | Optional | Optional | false | Set to "false" to disable SSL verification (private/self-signed CPD) |
| WATSONX_SPACE_ID | Required | Required | <space-id> | For “no IFM”, this is a watsonx.ai space; for IFM, this is your CPD IFM space |
| WATSONX_APIKEY | Required | Not needed | ******** | Required only for “no IFM” path where inference uses watsonx.ai |
| MODEL_OVERRIDE | Ignored | Optional | openai/gpt-oss-120b | Helpful if your CPD IFM exposes a single or constrained set of models |

Important: For CPD, specify one of WO_PASSWORD or WO_API_KEY, not both.

### Running with our sample data
The configs reference examples/evaluations/evaluate/data_simple.json
which uses the sample hr_agent.

### Add your CPD environment
```bash
orchestrate env add -n cpd -u $WO_INSTANCE # --insecure
```
Optionally use --insecure for local trusted setups with invalid certs

### Activate the CPD environment
```bash
orchestrate env activate cpd 
```

It will prompt you for the orchestrate user (ie. cpadmin) and either password or api key (use either one).


### If you haven’t imported the sample tools/agent yet:

```bash
orchestrate tools import -k python -f examples/evaluations/evaluate/agent_tools/tools.py
orchestrate agents import -f examples/evaluations/evaluate/agent_tools/hr_agent.json
```

Then run either:

#### CPD (no IFM)
```bash
orchestrate evaluations evaluate --config examples/evaluations/cpd/configs/config_cpd_no_ifm.yaml
```

#### CPD with IFM
```bash
orchestrate evaluations evaluate --config examples/evaluations/cpd/configs/config_cpd_ifm.yaml
```

## Recording
Recording mode works the same for CPD, using the same environment variables as the agent evaluation.

For example:
```bash
orchestrate evaluations record --output-dir "dir/to/save/recordings" -e examples/evaluations/cpd/env/.env.cpd.ifm.example
```

This will initiate a recording from your CPD watsonx Orchestrate chat.

## Troubleshooting
### SSL certificate issues:
For private/self-signed CPD environments, you can disable SSL verification during evaluation by setting:

```bash
export WO_SSL_VERIFY="false"
```

If you are adding the environment with the CLI, `orchestrate env add` also supports additional SSL-related flags that are helpful for on-premises CPD setups:

```bash
orchestrate env add -n cpd -u $WO_INSTANCE --type cpd --insecure
```

Available flags:

- `--type` / `-t` `<string>`
  - Optional and usually inferred from the URL.
  - Use this to explicitly specify the authentication type for the environment.
  - Accepted values:
    - `ibm_iam`: IBM Cloud environments using IBM Identity and Access Management (IAM)
    - `mcsp`: AWS environments using Multi-Cloud SaaS Platform (MCSP); tries v2 first, then falls back to v1 if needed
    - `mcsp_v1`: AWS environments using MCSP v1 authentication
    - `mcsp_v2`: AWS environments using MCSP v2 authentication
    - `cpd`: On-premises environments

- `--insecure`
  - Boolean flag.
  - Ignores SSL validation errors.
  - Intended for on-premises environments only.

- `--verify` `<path>`
  - String value.
  - Provides a path to an SSL certificate file.
  - Intended for on-premises environments only.

Example using a certificate file instead of disabling verification:

```bash
orchestrate env add -n cpd -u $WO_INSTANCE --type cpd --verify /path/to/certificate.pem
```

### Authentication failed:
Confirm you set exactly one of `WO_PASSWORD` or `WO_API_KEY`.

Verify `WO_INSTANCE` matches your CPD watsonx Orchestrate instance URL path.

You also may need to activate your environment again with `orchestrate env activate <yourenvname>` to refresh the credentials.

### Model not found:
If using IFM, ensure the model exists in your IFM space. Consider setting `MODEL_OVERRIDE`.

### Permissions:
Ensure your CPD and (if applicable) watsonx.ai credentials have permissions to run inference.

### Can't find agent in UI for recording
You may need to deploy your agent in the UI or by using the `orchestrate agents deploy` command. 

