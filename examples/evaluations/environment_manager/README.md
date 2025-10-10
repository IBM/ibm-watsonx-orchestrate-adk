# Automated Environment Setup

🚨 For internal use only 🚨

The automated environment manager set-up features imports your agents, tools, and knowledge base (if needed), runs the evaluation, and removes the imported artifacts from the tenant.

## Steps to Run

1. Set `HIDE_ENVIRONMENT_MGR_PANEL` to "false". This is not explicitly required to use this feature, but since this is a hidden feature, by default the flags needed to run this command are hidden in the help panel.

```bash
export HIDE_ENVIRONMENT_MGR_PANEL=false
orchestrate evaluations evaluate --help
```

2. Create a env_manager.yaml file like the example below:

```yaml
env1:
  agent:
    file: ./examples/evaluations/evaluate/agent_tools/hr_agent.json
  tools:
    file: ./examples/evaluations/evaluate/agent_tools/tools.py
    kind: python
  # knowledge:
  #   file: <add knowledge base definition file here if neccesary>
  test_paths: ./examples/evaluations/evaluate/
  clean_up: True # removes the imported artifacts (agents, tools, knowledge) after run
```

3. Run the following command:
```bash
orchestrate evaluations evaluate --env-manager-path <path to env manager.yaml file defined in step3> --output-dir "test-env-setup"
```