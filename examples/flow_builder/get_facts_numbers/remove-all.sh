#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for tool in get_facts_about_numbers get_request_status get_number_random_fact_flow; do
  orchestrate tools remove -n ${tool}
done

orchestrate agents remove -n get_number_fact_agent -k native