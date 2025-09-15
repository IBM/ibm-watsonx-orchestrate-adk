# Validating and Evaluating Native Agents

## Validation 

The `validate-native` command validates your native agent and store the results for later triaging and debugging.

### Running Validation
1. Follow the documentation on [creating and importing agents](https://developer.watson-orchestrate.ibm.com/agents/build_agent),[tools](https://developer.watson-orchestrate.ibm.com/tools/overview), [and/or knowledge bases ](https://developer.watson-orchestrate.ibm.com/knowledge_base/overview).
2. Prepare a TSV with three columns. The first column contains user stories. The second column is the expected summary or output. The third column is the native agent that is being validated. See `examples/evaluations/native_agent_validation/native_agent_validation.tsv`
3. The command is as follows:
```bash
orchestrate evaluations validate-native -t <path to data file tsv> -o <output folder>
```

#### Running the example
1. Use the `import-all.sh` in `./examples/evaluations/evaluate` to import sample tools and agents
2. Run the command below:
Sample command:

```bash
orchestrate evaluations validate-native -t ./examples/evaluations/native_agent_validation/native_agent_validation.tsv -o native-agent-validation
```

5. The validation results are saved to a `native_agent_evaluations` subfolder under the path provided for the `--output` flag.

🚨 Note: we expect `WATSONX_APIKEY, WATSONX_SPACE_ID` or `WO_INSTANCE, WO_API_KEY` be part of the environment variables or specified in .env_file. 
