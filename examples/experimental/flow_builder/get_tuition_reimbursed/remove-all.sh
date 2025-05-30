#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for python_tool in auto_deny_request auto_approval require_manager_approval get_tuition_reimbursed; do
  orchestrate tools remove -n ${python_tool}
done

orchestrate agents remove -n get_tuition_reimbursed -k native

