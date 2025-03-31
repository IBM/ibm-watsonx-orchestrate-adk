# Agents

## Import Agents
#### `orchestrate agents import`
  This command allows the user to import agents into the WXO platform. It can import agents from 3 different file types. All files are passed in with the `--file` or `-f` flag.

   ```bash
   orchestrate agents import -f <path to .yaml/.json/.py file>
   ```
    1. **YAML files (.yaml/.yml)**

   **Native Agent**
   ```yaml
   spec_version: v1
   kind: native
   name: agent_name
   description: A description of what the agent does and how it should carry out its objecting
   llm: watsonx/ibm/granite-3-8b-instruct
   style: default
   collaborators:
    - name_of_collaborator_agent_1
    - name_of_collaborator_agent_1
   tools:
    - name_of_tool_1
   ```

   **External Agent**
   ```yaml
spec_version: v1
kind: external 
name: news_agent
title: News Agent
description: >
   An agent running in a custom langchain container capable of communicating with multiple news sources to
    combat disinformation.
tags:
  - test
  - other
api_url: "https://someurl.com"
chat_params:
  stream: true
config:
    hidden: false
    enable_cot: true
nickname: news_agent
app_id: my_news_agent 
auth_scheme: BEARER_TOKEN
auth_config:
    token: "123" 
provider: external_chat
   ```

    2. **JSON files (.json)**

   **Native Agent**
   ```json
   {
      "spec_version": "v1",
      "kind": "native",
      "name": "agent_name",
      "description": "A description of what the agent does and how it should carry out its objecting",
      "llm": "watsonx/ibm/granite-3-8b-instruct",
      "style": "default",
      "collaborators":[
         "name_of_collaborator_agent_1",
         "name_of_collaborator_agent_1"
      ],
      "tools":[
         "name_of_tool_1"
      ]
   }
   ```

   **External Agent**

   ```json
   {
      "spec_version": "v1",
      "kind": "external",
      "name": "news_agent",
      "title": "News Agent",
      "description": "An agent running in a custom langchain container capable of communicating with multiple news sources to\n combat disinformation.\n",
      "tags": [
         "test",
         "other"
      ],
      "api_url": "https://someurl.com",
      "chat_params": {
         "stream": true
      },
      "config": {
         "hidden": false,
         "enable_cot": true
      },
      "nickname": "news_agent",
      "app_id": "my_news_agent",
      "auth_scheme": "BEARER_TOKEN",
      "auth_config": {
         "token": "123"
      },
      "provider": "external-chat"
   }
   ```


   #### `orchestrate agents import`


    3. **Python files (.py)**

  Python is unique as it can import multiple agents from the same file. It can also import tools (see `orchestrate tools import`) used by the agents.
   ```python
   from ibm_watsonx_orchestrate.agent_builder.agents import Agent, AgentStyle
   from sample_project.tools import my_tool

   agent = Agent(
      name="agent_name",
      description="A description of what the agent does and how it should carry out its objecting",
      llm="watsonx/ibm/granite-3-8b-instruct",
      style=AgentStyle.REACT,
      collaborators=[],
      tools=[my_tool]
   )
   ```
## Create Agents
#### `orchestrate agents create`
  This command allows you to create an agent fully defined through the command line.

  <!-- Depending on which type of agent you are creating the flags you need to provide are different -->

  **Native Agent**

  Flags

   * `--name` / `-n` is the name of the agent you want to create
   * `--kind` / `-k` is the kind of agent you wish to create. For native agents the value should be `native`
   * `--description` is the description of the agent
   * `--llm` what large language model the agent in the format of provider/model_id e.g. watsonx/ibm/granite-3-8b-instruct
   * `--style` is the style of agent you want to create. Either `default` or `react`
   * `--collaborators` is a list of agents that the agent should be able to call out to. Multiple collaborators can be specified .e.g. `--collaborators agent_1 --collaborators agent_2`
   * `--tools` is a list of tools that the agent should be able to use. Multiple tools can be specified .e.g. `--tools tool_1 --tools tool_2`

   ```bash
   orchestrate agents create \
   --name agent_name \
   --kind native \
   --description "Sample agent description" \
   --llm watsonx/ibm/granite-3-8b-instruct \
   --style default \
   --collaborators agent_1
   --collaborators agent_2
   --tools tool_1
   ```

   **External Agent**

   Allows you to call out to an External Agent that is hosted on a different platform such as Salesforce etc.
   [External Agent Documentation](https://github.com/watson-developer-cloud/watsonx-orchestrate-developer-toolkit/tree/main/external_agent/examples)

   Flags

   * `--name` / `-n`    is the name of the agent you want to create
   * `--kind` / `-k`    is the kind of agent you wish to create. For external agents the value should be `external`
   * `--title` / `-t`   is the title of the agent you wish to create
   * `--description`    is the description of the agent
   * `--api` / `-a`      is External Api url your Agent will use
   * `--tags`           is the list of tags for the agent. Format: --tags tag1 --tags tag2 ... Only needed for External and Assistant Agents
   * `--chat-params`    is the chat parameters in JSON format (e.g., '{"stream": true}'). Only needed for External and Assistant Agents
   * `--config`         is the Agent configuration in JSON format (e.g., '{"hidden": false, "enable_cot": false}')
   * `--nickname`       is the Agent's nickname
   * `--app-id`         is Application connection name used by the agent


   ```bash
   orchestrate agents create \
    --name news_agent \
    --title "News Agent" \
    --description "Sample agent description" \
    --api "http://some_url.com" \
    --kind external \
    --tags "test,other" \
    --chat-params '{"stream": true}' \
    --config '{"hidden": false, "enable_cot": false}' \
    --nickname "news_agent" \
    --app-id "my-basic-app"
   ```

   **WX.AI External Agent**
   
   In order to call out to agents on the WX.AI platform, set the Provider to `wx.ai`. 
    Flags

   * `--name` / `-n`    is the name of the agent you want to create
   * `--kind` / `-k`    is the kind of agent you wish to create. For external agents the value should be `external`
   * `--title` / `-t`   is the title of the agent you wish to create
   * `--description`    is the description of the agent
   * `--api` / `-a`     is External Api url your Agent will use
   * `--auth-config`    is External Api Auth Config in JSON format (e.g., '{"token": "sometoken"}')
   * `--auth-scheme`    is External Api Auth Scheme (e.g., API_KEY for WX.AI)
   * `--tags`           is the list of tags for the agent. Format: --tags tag1 --tags tag2 ... Only needed for External and Assistant Agents
   * `--chat-params`    is the chat parameters in JSON format (e.g., '{"stream": true}'). Only needed for External and Assistant Agents
   * `--config`         is the Agent configuration in JSON format (e.g., '{"hidden": false, "enable_cot": false}')
   * `--nickname`       is the Agent's nickname
   * `--app-id`         is Application connection name used by the agent
   * `--provider`       is External Agent Provider. It will be `wx.ai` for WX.AI agent

   ```bash
   orchestrate agents create \
    --name science_agent \
    --title "Sciene Agent" \
    --description "This external agent answers questions about Space" \
    --api "http://some_url.com" \
    --auth-config '{"token": "sometoken"}' \
    --auth-scheme 'API_KEY' \
    --kind external \
    --tags "wx.ai" \
    --chat-params '{"stream": true}' \
    --config '{"hidden": false, "enable_cot": false}' \
    --nickname "Science Agent" \
    --provider "wx.ai"
   ```


## Remove Agent
To remove an existing agent simply run the following: 
```bash
orchestrate agents remove --name my-agent --kind native
```

## List Agents
To list all agents simply run the following: 
```bash
orchestrate agents list
```

