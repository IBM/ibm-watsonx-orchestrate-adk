# IBM knowledge
This example was written to simulate an agent with a knowledge-base created from 2 PDF files.

Knowledge uses dynamic mode by default. In dynamic mode, the agent creates the query against the content store and decides what to do with the retrieved information — this could be generating an answer or using the retrieved information as context to complete subsequent tasks.

This example is intended to demonstrate:
- answering FAQ type of questions using only information from the knowledge base
- new use cases where retrieved knowledge can be applied in subsequent tool calls

## Steps to import
1. Run `orchestrate server start -e .my-env`
2. Run the import all script `./import_all.sh`
3. Run `orchestrate chat start`

## Suggested script

- who is ibm ceo
- tell me about ibm history
