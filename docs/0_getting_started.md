# Getting started guide

1. Request access to the orchestrate light docker repository.
2. Make sure you have the following installed:
- docker
- docker compose
- python 3.12
3. Make sure your ssh key is uploaded to your personal github account
    1. Run cat ~/.ssh/id_rsa.pub and if it returns `cat: /some/path/.ssh/id_rsa.pub: No such file or directory`, run ssh-keygen
    2. Take the contents printed out by running cat ~/.ssh/id_rsa.pub and upload it to [github](https://github.ibm.com/settings/keys)
4. Run pip install git+ssh://github.ibm.com/WatsonOrchestrate/wxo-clients.git
5. Next we'll need to create an IBM Cloud IAM key so that we will be able to download orchestrate lite. Follow the instructions [here](https://cloud.ibm.com/docs/account?topic=account-userapikey&interface=ui) making sure to not close the page after generating the api key.
6. Create a watsonx.ai instance if you do not have one already and locate your space id. These can be found [here](https://dataplatform.cloud.ibm.com/developer-access?context=wx).
7. Create an env file with the following contents
```env
DOCKER_IAM_KEY=<your ibm cloud api key>
WATSONX_APIKEY=<your ibm cloud api key>
WATSONX_SPACE_ID=<your watsonx ai space id>
```
Do note, if your team has a shared watsonx instance your WATSONX_APIKEY may be different from your DOCKER_IAM_KEY
if your team uses a shared ibm cloud account other than your own.
8. Start your Watson Orchestrate Light server. For more details check out [server_start](./1_server_start.md)
```bash
orchestrate server start --env-file path/to/.env
```
9. Login to your local server so that all future import commands target the local environment.
```bash
orchestrate login --local
```
10. Import your first tool(s). For more details on this check out [docs/tools](./2_tools.md)
```bash
orchestrate tools import -k python -f path/to/python/tool.py
orchestrate tools import -k openapi -f path/to/python/openapi_spec.yaml
```
11. Create an expert agent who can use your tools. For more details on this check out [docs/agents](./2_agents.md)
```bash
orchestrate agents import -f path/to/expert_agent_spec.yaml
```
12. Create an orchestrator agent who can coordinate work between your expert agents
```bash
orchestrate agents import -f path/to/orchestrator_agent_spec.yaml
```
13. Start chatting with your newly created orchestrator agent. For more details on this check out [docs/agents](./2_agents.md)
```bash
orchestrate chat start --env-file path/to/.env --orchestrator-agent-name <name of orchestrator agent>
```

Samples of these tools and agents can be found in the examples folder.
