### How to run evaluation

1. Run `import-all.sh` 
2. Run `orchestrate evaluations evaluate -p hr_sample/  -o ./debug -e ../../.env`
Note: we expect `WATSONX_APIKEY` `WATSONX_SPACE_ID` be part of the environment variables or specified in .env_file. 