******************************************
## Welcome to `ibm-watsonx-orchestrate`
******************************************

`ibm-watsonx-orchestrate` is a Python SDK that allows you to build expert and orchestrator agents and interact with the watsonx.orchestrate service. It also provides a convenient interface for managing credentials, sending requests, and handling responses from the service’s APIs.

------------------------------------------

## Prerequisites

- **Python 3.12+**  
  Ensure you have Python 3.12 or later installed.

- **Dependencies**  
  All required dependencies will be automatically installed when you install the package.

------------------------------------------

## How to Install the Library

Once you have cloned the repo, you can install it locally with `pip`:

```bash
pip install -e ".[dev]"
```

### Why `-e`?  
The `-e` flag is optional and stands for "editable mode." This allows you to make changes to the source code of the library and have those changes reflected immediately without needing to reinstall the dependency package. This is useful for development purposes.
---

## How to Build the distributable Package

To build the package, use [Hatch](https://hatch.pypa.io/latest/), a modern Python project management tool. Follow these steps:

1. **Install Hatch**  
   If you don’t already have Hatch installed, install it using `pip`:

   ```bash
   pip install hatch
   ```

2. **Build the Package**  
   Navigate to the root directory of the project and run:

   ```bash
   hatch build
   ```

   This will create the distribution files (e.g., `.whl` and `.tar.gz`) in the `dist` directory.

3. **Install the Package**  
   Once the package is built, you can install it locally:

   ```bash
   pip install dist/<filename>.whl
   ```

*(Replace `<filename>` with the actual name of the wheel file created in the `dist` directory.)*

---

## Usage

After installation, you can import and use the SDK in your Python code:

```python
from ibm_watsonx_orchestrate.client import Client

client = Client(api_key="your-api-key")
response = client.some_function()
print(response)
```

---

## CLI Documentation

After installation you will have access to the WXO CLI tool
This tool can be accessed using the `orchestrate` command

```bash
orchestrate --help

 Usage: orchestrate [OPTIONS] COMMAND [ARGS]...                                 
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ login                                                                        │
│ tools                                                                        │
│ agents                                                                       │
│ server                                                                       │
│ chat                                                                         │
╰──────────────────────────────────────────────────────────────────────────────╯

```
---

### CLI Features
### `orchestrate login`
The SDK will allow user to work with both local development environment and remote service
#### Local development
Prerequisite: local docker setup (under development).  
Once the setup is ready, run the following command:
```
orchestrate login --local
```
#### Working with remote service
The `orchestrate login` command requests 2 values from the user
1. The URL of the WXO instance the user wishes to authenticate against. This can be passed it using the `--url` or `u` flags, or provided at runtime in response to the prompt.
2. The API key for the WXO instance. This can be passed using the `--apikey` or  `-a` flags, or it can be provided at runtime in responce to the prompt

Logging in creates two persistent files
1. The first is `/.config/orchestrate/config.yaml`. This stores the url and other persistent values that the CLI needs to function.
2. The second is `/.cache/orchestrate/credentials.yaml`. This stores the API token returned with successful login and its expiry.

```bash
orchestrate login

Please enter WXO API url:
Please enter WXO API key: 
Successfully Logged In
```

### `orchestrate tools`
* #### `orchestrate tools import`
   This command allows a user to import tools into the WXO platform
   There are 3 kinds of tool imports, the kind is specified with the `--kind` or `-k` flags
   1. `-k python`
   
      This will require a python (.py) file is passed in through the `--file` of `-f` flag. It will extract all the tools referenced in the python file passed in. This includes all functions with the `@tool` decorator and all tools imported into the file.
      ```python
      #test_tool.py
      from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


      @tool(name="myName", description="the description", permission=ToolPermission.ADMIN)
      def my_tool(input: str) -> str:
         #functionality of the tool

      ```
      ```bash
      orchestrator tools import -k python -f /test_tool.py

      {
         "name": "myName",
         "description": "the description",
         "permission": "ADMIN",
         "input_schema": {
            "type": "object",
            "properties": {
               "input": {
               "type": "string",
               "title": "Input"
               }
            },
            "required": [
               "input"
            ]
         },
         "output_schema": {
            "type": "string"
         },
         "binding": {
            "python": {
               "function": "tests.cli.resources.python_samples.tool_w_metadata:my_tool"
            }
         }
      }
      ``` 
   2. `-k openapi`
   This will require a yaml (.yaml/.yml) or json (.json) file is passed in through the `--file` of `-f` flag. This yaml or json should be a valid OpenAPI spec for the API you wish to generate tools from.

   ```bash
   orchestrate -k openapi -f <path to openapi spec>
   ```
   3. `-k skill`
   This will create a tool that can use existing skills defined in the WXO platform. You will need to provide the `--skillset_id`, `--skill_id` and `--skill_operation_path` for the skill you wish to utilise.

   ```bash
   orchestrate -k skill --skillset_id <skill set id> --skill_id <skill id> --skill_operation_path <skill operation path>
   ```

### `orchestrate agents`
* #### `orchestrate agents import`
   This command allows the user to import both Expert and Orchestrator agents into the WXO platform. It can import these agents from 3 diffrent file types. All files are passed in with the `--file` or `-f` flag.
   ```bash
   orchestrate agents import -f <path to .yaml/.json/.py file>
   ```
   1. **YAML files (.yaml/.yml)**
   ```yaml
   #expert agent example
   name: sample_expert_agent
   description: A description of the agent
   type: expert 
   role: A natural language definition of the agents role
   goal: A natural language definition of the agents objective
   instructions: A natural language definition of how the agent is to go about solving the problem
   tools:
      - test_tool
      - web_search
   ```
   ```yaml
   #orchestrator agent example
   name: sample_orchestrator_agent
   type: orchestrator
   management_style: supervisor
   management_style_config:
      reflection_enabled: true
      reflection_retry_count: 3
   llm: granite
   agents:
      - sample_expert_agent
   ```
   2. **JSON files (.json)**
   ```json
   #expert agent example
   {
      "name": "sample_expert_agent",
      "description": "A description of the agent",
      "type": "expert" ,
      "role": "A natural language definition of the agents role",
      "goal": "A natural language definition of the agents objective",
      "instructions": "A natural language definition of how the agent is to go about solving the problem",
      "tools":[
         "test_tool",
         "web_search"
      ]
   }
   ```
   ```json
   #orchestrator agent example
   {
      "name": "sample_orchestrator_agent",
      "type": "orchestrator",
      "management_style": "supervisor",
      "management_style_config": {
         "reflection_enabled": true,
         "reflection_retry_count": 3
      },
      "llm": "granite",
      "agents":[
         "sample_expert_agent"
      ]
   }
   ```
   3. **Python files (.py)**

   Python is unique as it can import multiple Expert and Orchestrator agents from the same file. It can also import tools (see `orchestrate tools import`) used by the agents.
   ```python
   from ibm_watsonx_orchestrate.agent_builder.agents import ExpertAgent, OrchestrateAgent
   from sample_project.tools import my_tool

   expert_agent = ExpertAgent(
      name="sample_expert_agent",
      type="expert",
      description="A natural language definition of the agents role",
      role="A natural language definition of the agents role",
      goal="A natural language definition of the agents objective",
      instructions="A natural language definition of how the agent is to go about solving the problem",
      tools=[my_tool],
   )

   orchestrator_agent = OrchestrateAgent(
      name="sample_orchestrator_agent",
      type="orchestrator",
      management_style="supervisor",
      management_style_config=SupervisorConfig(reflection_enabled=True, reflection_retry_count=3),
      llm="granite",
      agents=["expert_agent"]
   )
   ```
* #### `orchestrate agents create`
   This command allows you to create either an Expert of Orchestrator agent fully defined through the command line.

   Depending on which type of agent you are creating the flags you need to provide are diffrent

   **Expert Agent**
   
   Flags
   * `--name` / `-n` is the name of the Expert agent you want to create
   * `--type` / `-t` is the type of agent you wish to create. For expert agents the value should be `expert`
   * `--description` is the description of the expert agent
   * `--role` is a natural lanuague description of the role you want the agent to carry out
   * `--goal` is a natural lanuague description of the goal you want the agent to achieve
   * `--instructions` is a natural lanuague description of how you want the agent to go about carrying out its role
   * `--tools` is a comma seperated list of `tools` that the agent can leverage in order to complete its goal

   ```bash
   orchestrate agents create \
   --name sample_expert_agent \
   --type expert \
   --description "Sample agent description" \
   --role "You are a sample agent meant to demonstrate the syntax" \
   --goal "Your mission is to teach people the syntax of the WXO CLI" \
   --instructions "Use the tools provided to ..." \
   --tools web_search,my_tool
   ```

  **Orchestrator Agent**
   
   Flags
   * `--name` / `-n` is the name of the Orchestrator agent you want to create
   * `--type` / `-t` is the type of agent you wish to create. For orchestrator agents the value should be `orchestrator`
   * `--management_style` what style of management the agent should use
   * `--management_style_config` configuable aspects of the agents management style like `refection_enabled` and `reflection_retry_count`
   * `--llm` what large language model the agent should use
   * `--agents` what expert agents does this agent manage

   ```bash
   orchestrate agents create \
   --name sample_orchestrator_agent \
   --type orchestrator \
   --management_style supervisor \
   --management_style_config reflection_enabled=true,reflection_retry_count=3 \
   --llm granite \
   --agents sample_expert_agent,sales_agent
   ```
### `orchestrate server`
Not implemented yet
### `orchestrate chat`
Not implemented yet

---
### CLI Development Setup

In order to work on the CLI, first make sure you have `hatch` installed

After you have ran `pip install -e ".[dev]"`

You should be able to run `hatch run orchestrate` which should perform identicallly to the `orchestrate` command

Additionally, you can run `hatch run test` to run the tests for both the CLI and SDK and `hatch run cov` to see the test coverage

------------------------------------------

## Starting the orchestrate service on your machine
- See [Server Start](docs/ServerStart.md) command
