### generate test cases by planning - example

1. load the agents & tools using `bash import-all.sh`
2. prepare a stories like `stories.csv`. The 1st column should include the story for the test case and the 2nd column should be the agent name.
```
story,agent
"I want to know my assignment ID for nwaters.",hr_agent
```
3. run generation `orchestrate evaluations generate -s examples/evaluations/generate/stories.csv -t examples/evaluations/generate/tools.py -e .env_file`
Note: we expect `WATSONX_APIKEY` `WATSONX_SPACE_ID` be part of the environment variables or specified in .env_file. 