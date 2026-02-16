### How to run evaluation

1. Run `import-all.sh` 
2. Run `orchestrate evaluations evaluate -p ./examples/evaluations/evaluate/  -o ./debug -e .env_file`
🚨 Note: we expect `WATSONX_APIKEY, WATSONX_SPACE_ID` or `WO_INSTANCE, WO_API_KEY` be part of the environment variables or specified in .env_file. 

#### Using IBM Cloud Pak for Data (CPD)
To run the evaluator with IBM Cloud Pak for Data (with or without IFM), see:
- examples/evaluations/cpd/README.md 

### Agentops Evaluation
The `orchestrate evaluations evaluate` command is the only `evaluations` command that supports non-legacy evaluation. To enable this mode, set the following environment variable:

```bash
export USE_LEGACY_EVAL=FALSE
```

All other `orchestrate evaluations` commands operate in legacy mode only. For them, setting `USE_LEGACY_EVAL=FALSE` has no effect.

Note: When running in non-legacy evaluation mode, the necessary files for `orchestrate evaluations analyze` are not automatically created, so this command will not work with non-legacy evaluation

To enable Langfuse telemetry, start your Orchestrate server with the `-l` flag:

```bash
orchestrate server start --env-file <ENV FILE> -l
```

After the server starts, you can access your local Langfuse dashboard at [http://localhost:3010](http://localhost:3010)

Your Langfuse username and password will appear in the terminal. Use these credentials to log in to the dashboard.

#### Run the Evaluation

Now, you can run the evaluation command as usual:

```bash
orchestrate evaluations evaluate -p examples/evaluations/evaluate/data_no_summary -o <OUTPUTDIR> -l
```

When the evaluation completes, you’ll receive links to your Langfuse sessions containing detailed evaluation results, for example:

```bash
Config and metadata saved to output/evaluate_1110/2025-11-10_21-06-55
Langfuse Evaluation run completed for collection 2025-11-10_21-06-55_collection:
 - http://localhost:3010/project/orchestrate-lite/sessions/e1bac47c-060a-46a7-8820-3260fd5f7252
 - http://localhost:3010/project/orchestrate-lite/sessions/1b56c480-4a2d-45ed-9c55-23e8a71f0a16
```

Here is an example Langfuse session page with different metric values:

![Langfuse Dashboard Example](./langfuse-dashboard.png)