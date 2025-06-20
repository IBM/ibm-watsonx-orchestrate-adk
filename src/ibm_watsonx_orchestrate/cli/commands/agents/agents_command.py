import typer
from typing_extensions import Annotated, List
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController
from ibm_watsonx_orchestrate.agent_builder.agents.types import DEFAULT_LLM, AgentKind, AgentStyle, ExternalAgentAuthScheme, AgentProvider
import json

agents_app = typer.Typer(no_args_is_help=True)


@agents_app.command(name="import", help='Import an agent definition into the active env from a file')
def agent_import(
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="YAML file with agent definition"),
    ],
    app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id of the connection to associate with this external agent. An application connection represents the server authentication credentials needed to connection to this agent (for example Api Keys, Basic, Bearer or OAuth credentials).'
        )
    ] = None,
):
    agents_controller = AgentsController()
    agent_specs = agents_controller.import_agent(file=file, app_id=app_id)
    agents_controller.publish_or_update_agents(agent_specs)


@agents_app.command(name="create", help='Create and import an agent into the active env')
def agent_create(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the agent you wish to create"),
    ],
    title: Annotated[
        str,
        typer.Option("--title", "-t", help="Title of the agent you wish to create. Only needed for External and Assistant Agents"),
    ] = None,
    kind: Annotated[
        AgentKind,
        typer.Option("--kind", "-k", help="The kind of agent you wish to create"),
    ] = AgentKind.NATIVE,
    api_url: Annotated[
        str,
        typer.Option("--api", "-a", help="External Api url your Agent will use"),
    ] = None,
    auth_scheme: Annotated[
        ExternalAgentAuthScheme,
        typer.Option("--auth-scheme", help="External Api auth schema to be used"),
    ] = ExternalAgentAuthScheme.NONE,
    provider: Annotated[
        AgentProvider,
        typer.Option("--provider", "-p", help="Agent Provider to be used.")
    ] = AgentProvider.EXT_CHAT,
    auth_config: Annotated[
        str,
        typer.Option(
            "--auth-config",
            help="Auth configuration to be used in JSON format (e.g., '{\"token\": \"test-api-key1\"')",
        ),
    ] = {},
    tags: Annotated[
        List[str],
        typer.Option(
            "--tags",
            help="A list of tags for the agent. Format: --tags tag1 --tags tag2 ... Only needed for External and Assistant Agents",
        ),
    ] = None,
    chat_params: Annotated[
        str,
        typer.Option(
            "--chat-params",
            help="Chat parameters in JSON format (e.g., '{\"stream\": true}'). Only needed for External and Assistant Agents",
        ),
    ] = None,
    config: Annotated[
        str,
        typer.Option(
            "--config",
            help="Agent configuration in JSON format (e.g., '{\"hidden\": false, \"enable_cot\": false}')",
        ),
    ] = None,
    nickname: Annotated[
        str,
        typer.Option("--nickname", help="Agent's nickname"),
    ] = None,
    app_id: Annotated[
        str,
        typer.Option("--app-id", help="Application ID for the agent"),
    ] = None,
    description: Annotated[
        str,
        typer.Option(
            "--description",
            help="Description of the agent",
        ),
    ] = None,
    llm: Annotated[
        str,
        typer.Option(
            "--llm",
            help="The LLM used by the agent",
        ),
    ] = DEFAULT_LLM,
    style: Annotated[
        AgentStyle,
        typer.Option("--style", help="The style of agent you wish to create"),
    ] = AgentStyle.DEFAULT,
    custom_join_tool: Annotated[
        str | None,
        typer.Option(
            "--custom-join-tool",
            help='The name of the python tool to be used by the agent to format and generate the final output. Only needed for "planner" style agents.',
        ),
    ] = None,
    structured_output: Annotated[
        str | None,
        typer.Option(
            "--structured-output",
            help='A JSON Schema object that defines the desired structure of the agent\'s final output. Only needed for "planner" style agents.',
        ),
    ] = None,
    collaborators: Annotated[
        List[str],
        typer.Option(
            "--collaborators",
            help="A list of agent names you wish for the agent to be able to collaborate with. Format --colaborators agent1 --collaborators agent2 ...",
        ),
    ] = None,
    tools: Annotated[
        List[str],
        typer.Option(
            "--tools",
            help="A list of tool names you wish for the agent to be able to utilise. Format --tools tool1 --tools agent2 ...",
        ),
    ] = None,
    knowledge_base: Annotated[
        List[str],
        typer.Option(
            "--knowledge-bases",
            help="A list of knowledge bases names you wish for the agent to be able to utilise. Format --knowledge-bases base1 --knowledge-bases base2 ...",
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
    context_access_enabled: Annotated[
        bool,
        typer.Option(
            "--context-access-enabled",
            help="Whether the agent has access to context variables (default: True)",
        ),
    ] = True,
    context_variables: Annotated[
        List[str],
        typer.Option(
            "--context-variable",
            "-v",
            help="A list of context variable names the agent can access. Format: --context-variable var1 --context-variable var2 ... or -v var1 -v var2 ...",
        ),
    ] = None,
):
    chat_params_dict = json.loads(chat_params) if chat_params else {}
    config_dict = json.loads(config) if config else {}
    auth_config_dict = json.loads(auth_config) if auth_config else {}
    structured_output_dict = json.loads(structured_output) if structured_output else None

    agents_controller = AgentsController()
    agent = agents_controller.generate_agent_spec(
        name=name,
        kind=kind,
        description=description,
        title=title,
        api_url=api_url,
        auth_scheme=auth_scheme,
        auth_config=auth_config_dict,
        provider=provider,
        llm=llm,
        style=style,
        custom_join_tool=custom_join_tool,
        structured_output=structured_output_dict,
        collaborators=collaborators,
        tools=tools,
        knowledge_base=knowledge_base,
        tags=tags,
        chat_params=chat_params_dict,
        config=config_dict,
        nickname=nickname,
        app_id=app_id,
        output_file=output_file,
        context_access_enabled=context_access_enabled,
        context_variables=context_variables,
    )
    agents_controller.publish_or_update_agents([agent])

@agents_app.command(name="list", help='List all agents in the active env')
def list_agents(
    kind: Annotated[
        AgentKind,
        typer.Option("--kind", "-k", help="The kind of agent you wish to create"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="List full details of all agents in json format"),
    ] = False,
):  
    agents_controller = AgentsController()
    agents_controller.list_agents(kind=kind, verbose=verbose)

@agents_app.command(name="remove", help='Remove an agent from the active env')
def remove_agent(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the agent you wish to remove"),
    ],
    kind: Annotated[
        AgentKind,
        typer.Option("--kind", "-k", help="The kind of agent you wish to remove"),
    ]
):  
    agents_controller = AgentsController()
    agents_controller.remove_agent(name=name, kind=kind)

@agents_app.command(name="export", help='Export an agent and its dependencies to a zip file or yaml')
def export_agent(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the agent you wish to export"),
    ],
    kind: Annotated[
        AgentKind,
        typer.Option("--kind", "-k", help="The kind of agent you wish to export"),
    ],
    output_file: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Path to a where the file containing the exported data should be saved",
        ),
    ],
    agent_only_flag: Annotated[
        bool,
        typer.Option(
            "--agent-only",
            help="Export only the yaml to the specified agent, excluding its dependencies",
        ),
    ]=False
):  
    agents_controller = AgentsController()
    agents_controller.export_agent(name=name, kind=kind, output_path=output_file, agent_only_flag=agent_only_flag)
