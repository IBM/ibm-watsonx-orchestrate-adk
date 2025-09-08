### how to run analyze command example

1. open a terminal and maximize the window width & length on the screen

2. Option1: Run the following command: `orchestrate evaluations analyze -d ./examples/evaluations/analysis/ -e .env_file`

3. Option2: Run the command with tools directory to perform additional analysis with tools:
`orchestrate evaluations analyze -d ./examples/evaluations/analysis/ -e env.lite -t ./examples/evaluations/analysis/tools.py`
🚨 Note: we expect `WATSONX_APIKEY, WATSONX_SPACE_ID` or `WO_INSTANCE, WO_API_KEY` to be part of the environment variables or specified in .env_file. 
