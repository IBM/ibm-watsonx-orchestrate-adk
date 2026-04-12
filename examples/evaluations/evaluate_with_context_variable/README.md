### How to run evaluation with context variables

This example demonstrates how to evaluate an agent that uses **context variables**. Context variables allow the agent to receive runtime information (such as the logged-in user's identity) without requiring the user to explicitly provide it.

#### Key Differences from Standard Evaluation

1. **Agent Definition**: The agent includes `context_access_enabled: true` and a `context_variables` list specifying which variables it expects (e.g., `sap_username`).

2. **Test Data**: Each test case includes a `runtime_context` field that provides the context variable values for that test scenario.

#### Setup

1. Run `import-all.sh` to import the tools and agent:
   ```bash
   ./examples/evaluations/evaluate_with_context_variable/import-all.sh
   ```

2. Run the evaluation:
   ```bash
   orchestrate evaluations evaluate -p ./examples/evaluations/evaluate_with_context_variable/ -o ./debug -e .env_file
   ```

Note: We expect `WATSONX_APIKEY, WATSONX_SPACE_ID` or `WO_INSTANCE, WO_API_KEY` to be part of the environment variables or specified in .env_file.

#### Context Variables in Test Data

The test data files (`data_simple.json`, `data_complex.json`) include a `runtime_context` field:

```json
{
  "agent": "hr_agent_context",
  "runtime_context": {
    "sap_username": "nwaters"
  },
  ...
}
```

This simulates a scenario where the user "nwaters" is already authenticated, and the agent can use this context to automatically look up the user's information without asking for their username.

#### Test Scenarios

- **data_simple.json**: A single user querying their own timeoff schedule using context variables
- **data_complex.json**: A manager querying the timeoff schedules of their direct reports using context variables
