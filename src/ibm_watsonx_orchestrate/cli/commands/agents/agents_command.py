import typer
from typing_extensions import Annotated, List, Optional
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController
from ibm_watsonx_orchestrate.agent_builder.agents.types import DEFAULT_LLM, AgentKind, AgentStyle, ExternalAgentAuthScheme, AgentProvider
from ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_command import ai_builder_app
from ibm_watsonx_orchestrate.client.utils import is_local_dev
import json
import os
import datetime
import logging
import sys

logger = logging.getLogger(__name__)

agents_app = typer.Typer(no_args_is_help=True)
agents_app.add_typer(
    ai_builder_app,
    name="ai-builder",
    help="AI tools to help create and refine agents."
)

@agents_app.command(name="import", help='Import an agent definition into the active env from a file')
def agent_import(
    file: Annotated[
        Optional[str],
        typer.Option("--file", "-f", help="Path to a file: YAML file with agent definition"),
    ] = None,
    experimental_package_root: Annotated[
        Optional[str],
        typer.Option("--experimental-package-root", help="Path to the directory containing custom agent code (for custom style agents). The directory will be automatically zipped and uploaded.", hidden=True),
    ] = None,
    experimental_config_file: Annotated[
        Optional[str],
        typer.Option("--experimental-config-file", help="Path to a config.yaml file to include in the custom agent package. Only used with --experimental-package-root.", hidden=True),
    ] = None,
    app_id: Annotated[
        Optional[str], typer.Option(
            '--app-id', '-a',
            help='The app id of the connection to associate with this external agent. An application connection represents the server authentication credentials needed to connection to this agent (for example Api Keys, Basic, Bearer or OAuth credentials).'
        )
    ] = None,
):
    
    # Validate that either file or experimental_package_root is provided
    if not file and not experimental_package_root:
        raise ValueError("Either --file or --experimental-package-root is required")
    
    if file and experimental_package_root:
        raise ValueError("Specify either --file or --experimental-package-root, not both")
    
    if experimental_config_file and not experimental_package_root:
        raise ValueError("--experimental-config-file can only be used with --experimental-package-root")
    
    custom_agent_file_path = None
    custom_agent_config_file = None
    
    if experimental_package_root:
        # Validate the directory exists
        if not os.path.exists(experimental_package_root):
            raise ValueError(f"Package root directory not found: {experimental_package_root}")
        if not os.path.isdir(experimental_package_root):
            raise ValueError(f"Package root must be a directory: {experimental_package_root}")
        
        # Validate config file if provided
        if experimental_config_file:
            if not os.path.exists(experimental_config_file):
                raise ValueError(f"Config file not found: {experimental_config_file}")
            if not os.path.isfile(experimental_config_file):
                raise ValueError(f"Config file must be a file: {experimental_config_file}")
            custom_agent_config_file = experimental_config_file
        
        custom_agent_file_path = experimental_package_root
        file = experimental_package_root
    elif file:
        # Validate the file exists
        if not os.path.exists(file):
            raise ValueError(f"File not found: {file}")
    
    agents_controller = AgentsController()
    agent_specs = agents_controller.import_agent(
        file=file,
        app_id=app_id,
        custom_agent_file_path=custom_agent_file_path,
        custom_agent_config_file=custom_agent_config_file
    )
    agents_controller.publish_or_update_agents(agent_specs)


@agents_app.command(name="create", help='Create and import an agent into the active env')
def agent_create(
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Name of the agent you wish to create. Not required for custom agents (read from config.yaml)."),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option(
            "--description",
            help="Description of the agent. Not required for custom agents (read from config.yaml).",
        ),
    ] = None,
    file: Annotated[
        Optional[str],
        typer.Option("--file", "-f", help="Path to a file: YAML file with agent definition or ZIP file for custom style agents"),
    ] = None,
    experimental_package_root: Annotated[
        Optional[str],
        typer.Option("--experimental-package-root", help="Path to the directory containing custom agent code (for custom style agents). The directory will be automatically zipped and uploaded.", hidden=True),
    ] = None,
    experimental_config_file: Annotated[
        Optional[str],
        typer.Option("--experimental-config-file", help="Path to a config.yaml file to include in the custom agent package. Only used with --experimental-package-root.", hidden=True),
    ] = None,
    title: Annotated[
        str,
        typer.Option("--title", "-t", help="Title of the agent you wish to create. Only needed for External and Assistant Agents"),
    ] = None,
    kind: Annotated[
        AgentKind,
        typer.Option("--kind", "-k", help="The kind of agent you wish to create"),
    ] = AgentKind.NATIVE,
    instructions: Annotated[
        str,
        typer.Option(
            "--instructions",
            help="A set of instructions for how the agent should preform actions.",
        ),
    ] = None,
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
    
    custom_agent_file_path = None
    custom_agent_config_file = None
    
    if style == AgentStyle.CUSTOM:
        if not file and not experimental_package_root:
            raise ValueError("For custom style agents, either --file or --experimental-package-root is required")
        
        if file and experimental_package_root:
            raise ValueError("For custom style agents, specify either --file or --experimental-package-root, not both")
        
        if experimental_config_file and not experimental_package_root:
            raise ValueError("--experimental-config-file can only be used with --experimental-package-root")
        
        if file:
            # Validate the zip file exists
            if not os.path.exists(file):
                raise ValueError(f"Custom code package file not found: {file}")
            custom_agent_file_path = file
        
        if experimental_package_root:
            # Validate the directory exists
            if not os.path.exists(experimental_package_root):
                raise ValueError(f"Package root directory not found: {experimental_package_root}")
            if not os.path.isdir(experimental_package_root):
                raise ValueError(f"Package root must be a directory: {experimental_package_root}")
            
            # Validate config file if provided
            if experimental_config_file:
                if not os.path.exists(experimental_config_file):
                    raise ValueError(f"Config file not found: {experimental_config_file}")
                if not os.path.isfile(experimental_config_file):
                    raise ValueError(f"Config file must be a file: {experimental_config_file}")
                custom_agent_config_file = experimental_config_file
            
            # The directory path will be passed and zipped in the controller
            custom_agent_file_path = experimental_package_root

    agents_controller = AgentsController()
    
    # For custom agents, name and description are optional (read from config.yaml by backend)
    # For other agent types, they are required
    if style != AgentStyle.CUSTOM:
        if not name:
            raise ValueError("--name is required for non-custom agents")
        if not description:
            raise ValueError("--description is required for non-custom agents")
    else:
        # For custom agents, use placeholders if not provided - backend will read from config.yaml
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        if not name:
            name = f"placeholder_{timestamp_str}"
        if not description:
            description = f"placeholder_{timestamp_str}"
    
    agent = agents_controller.generate_agent_spec(
        name=name,
        kind=kind,
        description=description,
        title=title,
        instructions=instructions,
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
        custom_agent_file_path=custom_agent_file_path,
        custom_agent_config_file=custom_agent_config_file,
    )
    agents_controller.publish_or_update_agents([agent])

@agents_app.command(name="list", help='List all agents in the active env')
def list_agents(
    kind: Annotated[
        AgentKind,
        typer.Option("--kind", "-k", help="The kind of agent you wish to list"),
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

@agents_app.command(name="deploy", help="Deploy Agent")
def deploy_agent(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the agent you wish to deploy"),
    ]
):
    agents_controller = AgentsController()
    agents_controller.deploy_agent(name=name)

@agents_app.command(name="undeploy", help="Undeploy Agent")
def undeploy_agent(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the agent you wish to undeploy"),
    ]
):
    agents_controller = AgentsController()
    agents_controller.undeploy_agent(name=name)

@agents_app.command(name="experimental-connect", help="Connect connections to an agent", hidden=True)
def experimental_connect_connections(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the agent to connect connections to"),
    ],
    connection_ids: Annotated[
        List[str],
        typer.Option(
            "--connection-id",
            "-c",
            help="Connection app_id to connect. Multiple can be specified: --connection-id conn1 --connection-id conn2",
        ),
    ],
):
    """
    Connect one or more connections to a custom agent.
    
    This command uses the PATCH /orchestrate/agents/{id} endpoint to associate
    connections with an agent by their connection IDs.
    
    Example:
        wxo agents experimental-connect --name my-agent --connection-id conn1 --connection-id conn2
    """
    agents_controller = AgentsController()
    agents_controller.connect_connections_to_agent(agent_name=name, connection_ids=connection_ids)

@agents_app.command(name="experimental-run", help="Send a message to a custom agent", hidden=True)
def experimental_run(
    message: Annotated[
        str,
        typer.Option("--message", "-m", help="The message to send to the agent"),
    ],
    agent_name: Annotated[
        str,
        typer.Option("--agent-name", "-a", help="The custom agent name to send the message to (required)"),
    ],
    thread_id: Annotated[
        Optional[str],
        typer.Option("--thread-id", "-t", help="Existing thread ID to continue conversation (optional)"),
    ] = None,
    capture_logs: Annotated[
        bool,
        typer.Option("--capture-logs", help="Capture and display logs from the agent execution (only available for custom agents)"),
    ] = False,
):
    """
    Send a message to a custom agent, optionally capturing and displaying execution logs.
    
    This command only works with custom style agents.
    
    Examples:
        adk agents experimental-run --message "What is the weather today?" --agent-name "my-custom-agent"
        adk agents experimental-run --message "Tell me more" --agent-name "my-custom-agent" --thread-id "thread-456"
        adk agents experimental-run --message "Debug this" --agent-name "my-custom-agent" --capture-logs
    """
    agents_controller = AgentsController()
    agents_controller.run_agent(message=message, agent_name=agent_name, thread_id=thread_id, capture_logs=capture_logs)
