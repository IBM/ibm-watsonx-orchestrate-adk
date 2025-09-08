# IBM knowledge dynamic mode
This example was written to simulate an agent with both knowledge-base and a python tool configured. 

Today Knowledge is used as a linear pipeline that retrieves information from whatever content store it is connected to, knowledge takes the user input and context of the conversation to create a query against that store and then generates an answer which is sent back to the agent.

By enabling the dynamic mode, you allow knowledge to perform a retrieval as before, but the agent can then decide what it does with that retrieved information. This could be generating an answer or using the retrieved information as context for the agent to complete tasks. In addition, the agent creates the query against the content store.

This example is intended to demonstrate
- new use cases enabled by the dynamic mode where retrieved knowledge can be applied in subsequent tool calls
- answering FAQ type of questions using only information from knowledge base

## Steps to import
1. Run `orchestrate server start -e .my-env`
2. Run the import all script `./import_all_dynamic_mode.sh`
3. Run `orchestrate chat start`

## Suggested script for FAQ type of use cases

**These questions should be handled well by the LLM that is currently configured: the llama 90B model**

- who is ibm ceo
- tell me about ibm history

## Suggested script for more sophisticated agent behaviour

**NOTE: Please note that more sophisticated use cases need better LLMs, such as gpt 4.1 mini**

- tell me stock prices of companies that IBM has partnerships with

