# Agents

#### orchestrate agents import
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
#### orchestrate agents create
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