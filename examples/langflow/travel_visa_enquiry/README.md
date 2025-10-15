### Langflow as a tool in wxO

In this example, we have 2 langflow applications:
1. `IndexIndiaVisaInfo.json` - create a vector index in AstraDB
1. `QueryIndiaVisaInfo.json` - search for answer about travel questions to India 

Before you start:
1. Start the ADK with Langflow `orchestrate server start -e .env --with-langflow`
1. Get API keys for Astra DB, watsonx.AI.  You can use trial keys for this example.
1. Go to Astra DB, create a new database called `langflow_doc`.  
1. Within that database, create a new collection called `visa_info`.  Pick Nvidia as the embedding algorithm and take default for the rest of the value.
1. You should only need to call the IndexIndiaVisaInfo tool once.

### Use Travel Advice agent with Langflow tool from wxO Chat

1. Create a `.env` file with the setting:
    1. `ASTRA_API_KEY=<your Astra DB api key>`
    2. `WXAI_API_KEY=<your wx.ai api key>`
    3. `WXAI_PROJECT_ID=<your wx.ai project id>`
1. Run `import-all.sh` 
    1. As part of the script, we create an app-id `doc_search` with the environment values and associate them with the Langflow tool.
1. Launch the Chat UI with `orchestrate chat start`
1. Pick the `travel_visa_agent`
1. Type in something like `Do I need a visa if I travel to India as a US citizen?`. The agent should response with a set of travel advices.

