#!/usr/bin/env bash
set -euo pipefail

# Load your environment variables here if you keep a local .env file:
source examples/evaluations/cpd/env/.env.cpd.ifm.example

# Add your CPD environment to orchestrate.  Optionally use --insecure for local trusted setups with invalid certs
orchestrate env add -n cpdifm -u $WO_INSTANCE # --insecure

# Activate the CPD environment.  Use either WO_PASSWORD or WO_API_KEY.
orchestrate env activate cpdifm --username=$WO_USERNAME --password=$WO_PASSWORD
# orchestrate env activate cpdifm -username=$WO_USERNAME --api-key $WO_API_KEY

orchestrate evaluations evaluate --config examples/evaluations/cpd/configs/config_cpd_ifm.yaml