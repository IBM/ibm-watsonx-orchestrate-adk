import typer
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import (
    AgentsController,
    AgentTypes,
)
from ibm_watsonx_orchestrate.agent_builder.agents.types import (
    AgentManagementStyle,
    DEFAULT_LLM,
)

agents_app = typer.Typer(no_args_is_help=True)


@agents_app.command(name="import")
def agent_import(
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="YAML file with agent definition"),
    ],
):
    agents_controller = AgentsController()
    agent_specs = agents_controller.import_agent(file=file)
    agents_controller.publish_or_update_agents(agent_specs)


@agents_app.command(name="create")
def agent_create(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the agent you wish to create"),
    ],
    type: Annotated[
        AgentTypes,
        typer.Option("--type", "-t", help="The type of agent you wish to create"),
    ],
    # Expert requirements
    description: Annotated[
        str,
        typer.Option(
            "--description",
            help="Description of Expert agent. Required for type=['expert']",
        ),
    ] = None,
    role: Annotated[
        str,
        typer.Option(
            "--role",
            help="A description of the role that the Expert agent is to carry out. Required for type=['expert']",
        ),
    ] = None,
    goal: Annotated[
        str,
        typer.Option(
            "--goal",
            help="The goal the Expert agent is trying to achieve. Required for type=['expert']",
        ),
    ] = None,
    instructions: Annotated[
        str,
        typer.Option(
            "--instructions",
            help="Instructions for how the Expert agent is to carry out its objective. Required for type=['expert']",
        ),
    ] = None,
    backstory: Annotated[
        str,
        typer.Option(
            "--backstory",
            help="The backstory of the Expert agent. This provides further context as to how the agent should behave. Optional for type=['expert']",
        ),
    ] = None,
    tools: Annotated[
        str,
        typer.Option(
            "--tools",
            help="A comma sepertaed list of tools that the Expert agent can use (.e.g 'web_search,conversational_search'). Required for type=['expert']",
        ),
    ] = None,
    # Orchestrator requirements
    management_style: Annotated[
        AgentManagementStyle,
        typer.Option(
            "--management_style",
            help="The management style of the Orchestrator agent. Required for type=['orchestrator']",
        ),
    ] = AgentManagementStyle.SUPERVISOR,
    management_style_config: Annotated[
        str,
        typer.Option(
            "--management_style_config",
            help="Config for management style\nValues:\n -reflection_enabled=[true|false]\n -reflection_retry_count=(int) (.e.g 'reflection_enabled=true,reflection_retry_count=3') . Required for type=['orchestrator']",
        ),
    ] = None,
    llm: Annotated[
        str,
        typer.Option(
            "--llm",
            help="The LLM used by the Orchestrator agent. Required for type=['orchestrator']",
        ),
    ] = DEFAULT_LLM,
    agents: Annotated[
        str,
        typer.Option(
            "--agents",
            help="A comma sepertaed list of agents that the Orchestrator agent manages (.e.g 'research_agent,sales_agent'). Required for type=['orchestrator']",
        ),
    ] = None,
    output_file: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Write the agent definition out to a YAML (.yaml/.yml) file or a JSON (.json) file.",
        ),
    ] = None,
):
    agents_controller = AgentsController()
    agent = agents_controller.generate_agent_spec(
        name=name,
        type=type,
        description=description,
        role=role,
        goal=goal,
        instructions=instructions,
        backstory=backstory,
        tools=tools,
        management_style=management_style,
        management_style_config=management_style_config,
        llm=llm,
        agents=agents,
        output_file=output_file,
    )
    agents_controller.publish_or_update_agents([agent])
