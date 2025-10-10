### How to run evaluation

1. Run `import-all.sh` 
2. Run `orchestrate evaluations evaluate -p ./examples/evaluations/evaluate/  -o ./debug -e .env_file`
🚨 Note: we expect `WATSONX_APIKEY, WATSONX_SPACE_ID` or `WO_INSTANCE, WO_API_KEY` be part of the environment variables or specified in .env_file. 

#### Using IBM Cloud Pak for Data (CPD)
To run the evaluator with IBM Cloud Pak for Data (with or without IFM), see:
- examples/evaluations/cpd/README.md 