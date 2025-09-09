#!/usr/bin/env bash
set -euo pipefail

# Load your environment variables here if you keep a local .env file:
source examples/evaluations/cpd/env/.env.cpd.no_ifm.example

# Add your CPD environment to orchestrate.  Optionally use --insecure for local trusted setups with invalid certs
orchestrate env add -n cpd -u $WO_INSTANCE # --insecure

# Activate the CPD environment.  Use either WO_PASSWORD or WO_API_KEY.
orchestrate env activate cpd --username=$WO_USERNAME --password=$WO_PASSWORD
# orchestrate env activate cpd -username=$WO_USERNAME --api-key $WO_API_KEY

# Run the evaluation
python -m wxo_agentic_evaluation.main --config examples/evaluations/cpd/configs/config_cpd_no_ifm.yaml