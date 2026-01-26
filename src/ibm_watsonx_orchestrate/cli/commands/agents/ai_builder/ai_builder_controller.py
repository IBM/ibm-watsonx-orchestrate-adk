import logging
import os
import sys
import difflib
import re
from datetime import datetime
from functools import wraps
from pathlib import Path

import rich
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box
from rich.json import JSON
from rich.console import Group
from requests import ConnectionError
from typing import List, Dict, Any
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import KnowledgeBaseSpec
from ibm_watsonx_orchestrate.agent_builder.tools import ToolSpec, ToolPermission, ToolRequestBody, ToolResponseBody
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController, AgentKind, get_agent_details
from ibm_watsonx_orchestrate.cli.commands.models.models_controller import ModelsController
from ibm_watsonx_orchestrate.agent_builder.agents.types import DEFAULT_LLM, BaseAgentSpec
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.ai_builder.agent_builder_client import AgentBuilderClient
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient
from ibm_watsonx_orchestrate.client.threads.threads_client import ThreadsClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.ai_builder.cpe.cpe_client import CPEClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)

def __box_print(message_lines: List[str | Dict[Any, Any]], title: str | None = None):
    content_parts = []
    
    for item in message_lines:
        if isinstance(item, dict):
            # Create rich JSON representation for dictionaries
            json_content = JSON.from_data(item)
            content_parts.append(json_content)
        else:
            # Treat as string (convert if needed)
            content_parts.append(str(item))
    
    # If we have mixed content (strings and JSON), we need to handle them differently
    if any(isinstance(item, dict) for item in message_lines):
        # Create a group of renderables for mixed content
        panel = Panel(Group(*content_parts), box=box.DOUBLE, padding=(0, 1), title=title)
    else:
        # All strings - join with newlines as before
        message = "\n".join(str(item) for item in message_lines)
        panel = Panel(message, box=box.DOUBLE, padding=(0, 1), title=title)
    
    rich.print(panel)

def _handle_agent_builder_server_errors(func=None, *args, **kwargs):
    def decorator(inner_func):
        @wraps(inner_func)
        def wrapper(*args, **kwargs):
            try:
                return inner_func(*args, **kwargs)
            except ConnectionError:
                logger.error(
                    "Failed to connect to AI Builder server. Please ensure AI Builder is running via `orchestrate server start --with-ai-builder`")
                sys.exit(1)
            except ClientAPIException:
                logger.error(
                    "An unexpected server error has occurred with in the AI Builder server. Please check the logs via `orchestrate server logs`")
                sys.exit(1)
        return wrapper

    # If func is not None, it means the decorator is used without arguments
    if func is not None and callable(func):
        return decorator(func)(*args, **kwargs)

    # Otherwise, return the actual decorator
    return decorator


def _validate_output_file(output_file: Path, dry_run_flag: bool) -> None:
    output_file = Path(output_file) if output_file else None
    if not output_file and not dry_run_flag:
        logger.error(
            "Please provide a valid yaml output file. Or use the `--dry-run` flag to output generated agent content to terminal")
        sys.exit(1)

    if output_file and dry_run_flag:
        logger.error("Cannot set output file when performing a dry run")
        sys.exit(1)

    if output_file:
        if output_file.suffix not in {".yaml", ".yml"}:
            logger.error("Output file must be of type '.yaml' or '.yml'")
            sys.exit(1)


def _get_progress_spinner() -> Progress:
    console = Console()
    return Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    )


def _get_incomplete_tool_from_name(tool_name: str) -> dict:
    input_schema = ToolRequestBody(**{"type": "object", "properties": {}})
    output_schema = ToolResponseBody(**{"description": "None"})
    spec = ToolSpec(**{"name": tool_name, "description": tool_name, "permission": ToolPermission.ADMIN,
                       "input_schema": input_schema, "output_schema": output_schema})
    return spec.model_dump()


def _get_incomplete_agent_from_name(agent_name: str) -> dict:
    spec = BaseAgentSpec(**{"name": agent_name, "description": agent_name, "kind": AgentKind.NATIVE, "id": agent_name})
    return spec.model_dump()


def _get_incomplete_knowledge_base_from_name(kb_name: str) -> dict:
    spec = KnowledgeBaseSpec(**{"name": kb_name, "description": kb_name})
    return spec.model_dump()


def _get_tools_from_names(tool_names: List[str]) -> List[dict]:
    if not len(tool_names):
        return []

    tool_client = get_tool_client()

    try:
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Fetching tools", total=None)
            tools = tool_client.get_drafts_by_names(tool_names)
            found_tools = {tool.get("name") for tool in tools}
            progress.remove_task(task)
            progress.refresh()
            for tool_name in tool_names:
                if tool_name not in found_tools:
                    logger.warning(
                        f"Failed to find tool named '{tool_name}'. Falling back to incomplete tool definition. Prompt generation performance maybe effected.")
                    tools.append(_get_incomplete_tool_from_name(tool_name))
    except ConnectionError:
        logger.warning(
            f"Failed to fetch tools from server. For optimal results please start the server and import the relevant tools {', '.join(tool_names)}.")
        tools = []
        for tool_name in tool_names:
            tools.append(_get_incomplete_tool_from_name(tool_name))

    return tools


def _get_agents_from_names(collaborators_names: List[str]) -> List[dict]:
    if not len(collaborators_names):
        return []

    agent_controller = AgentsController()

    try:
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Fetching agents", total=None)
            agents = agent_controller.get_agent_by_names(collaborators_names)
            found_agents = {tool.get("name") for tool in agents}
            progress.remove_task(task)
            progress.refresh()
            for collaborator_name in collaborators_names:
                if collaborator_name not in found_agents:
                    logger.warning(
                        f"Failed to find agent named '{collaborator_name}'. Falling back to incomplete agent definition. Prompt generation performance maybe effected.")
                    agents.append(_get_incomplete_agent_from_name(collaborator_name))
    except ConnectionError:
        logger.warning(
            f"Failed to fetch tools from server. For optimal results please start the server and import the relevant tools {', '.join(collaborators_names)}.")
        agents = []
        for collaborator_name in collaborators_names:
            agents.append(_get_incomplete_agent_from_name(collaborator_name))

    return agents


def _get_knowledge_bases_from_names(kb_names: List[str]) -> List[dict]:
    if not len(kb_names):
        return []

    kb_client = get_knowledge_bases_client()

    try:
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Fetching Knowledge Bases", total=None)
            knowledge_bases = kb_client.get_by_names(kb_names)
            found_kbs = {kb.get("name") for kb in knowledge_bases}
            progress.remove_task(task)
            progress.refresh()
            for kb_name in kb_names:
                if kb_name not in found_kbs:
                    logger.warning(
                        f"Failed to find knowledge base named '{kb_name}'. Falling back to incomplete knowledge base definition. Prompt generation performance maybe effected.")
                    knowledge_bases.append(_get_incomplete_knowledge_base_from_name(kb_name))
    except ConnectionError:
        logger.warning(
            f"Failed to fetch knowledge bases from server. For optimal results please start the server and import the relevant knowledge bases {', '.join(kb_names)}.")
        knowledge_bases = []
        for kb_name in kb_names:
            knowledge_bases.append(_get_incomplete_knowledge_base_from_name(kb_name))

    return knowledge_bases

def _get_excluded_fields(agent = None):
    excluded_fields = {"llm_config"}
    if agent:
        for attr in vars(agent):
            if not getattr(agent, attr, None):
                excluded_fields.add(attr)
    else:
        excluded_fields.add("chat_with_docs")
        excluded_fields.add("guidelines")
    return list(excluded_fields)

def get_cpe_client() -> CPEClient:
    url = os.getenv('CPE_URL', "http://localhost:8081")
    return instantiate_client(client=CPEClient, url=url)


def get_agent_builder_client() -> AgentBuilderClient:
    url = os.getenv('AGENT_ARCHITECT_URL', "http://localhost:5321")
    return instantiate_client(client=AgentBuilderClient, url=url)

@_handle_agent_builder_server_errors()
def _healthcheck_cpe_server(client: CPEClient | None = None):
    if not client:
        client = get_cpe_client()
    client.healthcheck()

@_handle_agent_builder_server_errors()
def _healthcheck_agent_builder_server(client: AgentBuilderClient | None = None):
    if not client:
        client = get_agent_builder_client()
    client.healthcheck()


def get_tool_client(*args, **kwargs):
    return instantiate_client(ToolClient)


def get_knowledge_bases_client(*args, **kwargs):
    return instantiate_client(KnowledgeBaseClient)


def get_native_client(*args, **kwargs):
    return instantiate_client(AgentClient)


def get_threads_client():
    return instantiate_client(ThreadsClient)


def get_knowledge_bases(client):
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Fetching Knowledge Bases", total=None)
        try:
            knowledge_bases = client.get()
            progress.remove_task(task)
        except ConnectionError:
            knowledge_bases = []
            progress.remove_task(task)
            progress.refresh()
            logger.warning("Failed to contact wxo server to fetch knowledge_bases. Proceeding with empty agent list")
    return knowledge_bases


def get_deployed_tools_agents_and_knowledge_bases():
    all_tools = find_tools_by_description(tool_client=get_tool_client(), description=None)
    # TODO: this brings only the "native" agents. Can external and assistant agents also be collaborators?
    all_agents = find_agents(agent_client=get_native_client())
    all_knowledge_bases = get_knowledge_bases(get_knowledge_bases_client())

    return {"tools": all_tools, "collaborators": all_agents, "knowledge_bases": all_knowledge_bases}

def find_tools_by_description(description, tool_client):
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Fetching Tools", total=None)
        try:
            tools = tool_client.get()
            progress.remove_task(task)
        except ConnectionError:
            tools = []
            progress.remove_task(task)
            progress.refresh()
            logger.warning("Failed to contact wxo server to fetch tools. Proceeding with empty tool list")
    return tools


def find_agents(agent_client):
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Fetching Agents", total=None)
        try:
            agents = agent_client.get()
            progress.remove_task(task)
        except ConnectionError:
            agents = []
            progress.remove_task(task)
            progress.refresh()
            logger.warning("Failed to contact wxo server to fetch agents. Proceeding with empty agent list")
    return agents

@_handle_agent_builder_server_errors()
def chat_with_agent_builder(
    client: AgentBuilderClient,
    chat_llm: str,
    llm: str,
    description: str,
    dry_run_flag: bool,
    output_file: Path,
    agent_id: str | None=None,
    excluded_fields: List[str] = None):

    user_message = "" if not description else description
    notified_user = False

    agents_controller = AgentsController()
    while True:
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Thinking...", total=None)
            response = client.submit_chat(user_message=user_message,
                                            chat_llm=chat_llm,
                                           agent_id=agent_id)
            
            #    LOCAL_CLI = "LOCAL_CLI" we know what to do
            #    LOCAL_UI = "LOCAL_UI"
            #    SAAS_UI = "SAAS_UI"
            #    SAAS_CLI = "SAAS_CLI"
        if response.get('agent_id'):
            # read agent from runtime and save it to yaml
            agent_id = response.get('agent_id')
            agent = _save_agent_info_as_yaml(agents_controller, agent_id, dry_run_flag=dry_run_flag, llm=llm, output_file=output_file, excluded_fields=excluded_fields)
        progress.remove_task(task)

        end_conversation = response.get("conversation_state") == "conversation_ended"
        if end_conversation:
            #no need to save here because when conversation ended, the agent is not updated.
            return agent
        else:
            if response.get("conversation_state") == "artifacts_gathering_is_done":
                user_message = "Create"
                continue # another call to the agent builder, user input is not needed (parallel to the click on the "create" button in the UI)
            elif agent_id is not None:
                # This happens after the first version of the instruction is generated
                if not notified_user:
                    if not dry_run_flag:
                        rich.print('\n🤖 Builder: ' +
                                f"Based on the information you provided so far, an initial Agent Definitions YAML file has been created and is located in: {output_file}.\n"
                                "We will now continue our conversion to further adjust the agent definitions according to your feedback and requests,"
                                "and the YAML file will be automatically updated throughout our conversation. "
                                "You may manually edit any of the fields in the YAML file, and Agent Architect will incorporate those changes in real time. "
                                "For the best experience, it is recommended to open the file in your preferred IDE to view and manage the most up-to-date version.")

                    else:
                        rich.print("[italic dim]dry-run flag is true. Agent instructions will be printed on every message[/italic dim]")
                notified_user = True

            if "formatted_message" in response and response["formatted_message"]:
                rich.print('\n🤖 Builder: ' + response["formatted_message"]["content"][0]["text"])
                user_message = Prompt.ask("\n👤 You").strip()
                # it is verified that we first write to the yaml file (in the previos else block, and only then read this file.
                if agent_id is not None:
                    # Read the latest yaml file
                    if not dry_run_flag and output_file.exists():  # edits not possible in a dry run
                        read_agent_yaml_and_publish_to_runtime(output_file, llm)

            else:
                raise ValueError(
                    f"Wrong structure of response. Should contain 'formatted_message'`. {response}")


def _save_agent_info_as_yaml(agents_controller: AgentsController, agent_id: str, dry_run_flag, llm, output_file, excluded_fields):
    agent = agents_controller.get_agent_by_id(agent_id)
    if llm:
        agent.llm = llm

    if dry_run_flag:
        __box_print([
            agent.instructions
        ], title="Instructions")
    else:
        agents_controller.export_agent(name=agent.name, kind=agent.kind, output_path=output_file, agent_only_flag=True, exclude=excluded_fields)
    return agent

def prompt_tune(agent_spec: Path, chat_llm: str | None, llm:str, output_file: Path | None, dry_run_flag: bool) -> None:
    if not output_file and not dry_run_flag:
        output_file = agent_spec

    _validate_output_file(output_file, dry_run_flag)
    _validate_chat_llm(chat_llm)

    agent_spec = Path(agent_spec)
    output_file = Path(output_file) if output_file else None

    client = get_agent_builder_client()
    _healthcheck_agent_builder_server(client=client)

    agent = read_agent_yaml_and_publish_to_runtime(agent_spec, llm=llm)
    agent_id = get_agent_details(agent.name, client=get_native_client()).get("id")
    excluded_fields = _get_excluded_fields(agent)
    try:
        agent = chat_with_agent_builder(client=client,
                                          chat_llm=chat_llm,
                                          llm=llm if llm else agent.llm,
                                          description=None,
                                          output_file=output_file,
                                          agent_id=agent_id,
                                          dry_run_flag=dry_run_flag,
                                          excluded_fields=excluded_fields)


    except ConnectionError:
        logger.error(
            "Failed to connect to AI Builder server. Please ensure AI Builder is running via `orchestrate server start --with-ai-builder`")
        sys.exit(1)
    except ClientAPIException:
        logger.error(
            "An unexpected server error has occurred with in the AI Builder server. Please check the logs via `orchestrate server logs`")
        sys.exit(1)

    if not dry_run_flag:
        message_lines = [
            "Your agent refinement session finished successfully!",
            f"Agent YAML saved in file:",
            f"{output_file.absolute()}"
        ]
    else:
        agents_controller = AgentsController()
        agent = agents_controller.reference_agent_dependencies(agent)
        message_lines = [
            "Your agent refinement session finished successfully!",
            agent.model_dump(exclude_none=True, exclude_unset=True, exclude=excluded_fields)
        ]

    __box_print(message_lines)

def _validate_chat_llm(chat_llm):
    if chat_llm:
        mc = ModelsController()
        if not mc.does_model_exist(chat_llm):
            raise BadRequest(f"The model provided for '--chat-llm' '{chat_llm}' does not exist in the current tenant. Ensure the provided '--chat-llm' model name matches the name in `orchestrate models list`")
        
        formatted_chat_llm = re.sub(r'[^a-zA-Z0-9/]', '-', chat_llm)
        if not re.fullmatch(r'^.+\/(?:llama-3-3-70b-instruct|claude-sonnet-4-5|gpt-oss-120b)$', formatted_chat_llm):
            
            raise BadRequest(f"Unsupported chat model for AI Builder {chat_llm}. AI Builder supports only llama-3-3-70b-instruct and gpt-oss-120b at this point.`")


def read_agent_yaml_and_publish_to_runtime(agent_spec: Path, llm: str | None = None) -> dict[Any, Any]:
    agent = AgentsController.import_agent(file=str(agent_spec), app_id=None)[0]

    agent_kind = agent.kind
    if agent_kind != AgentKind.NATIVE:
        logger.error(
            f"Only native agents are supported for prompt tuning. Provided agent spec is on kind '{agent_kind}'")
        sys.exit(1)
    
    if llm:
        agent.llm = llm

    agents_controller = AgentsController()
    agents_controller.publish_or_update_agents([agent])

    return agent



def create_agent(output_file: Path, llm: str, chat_llm: str | None, dry_run_flag: bool = False, description: str=None) -> None:
    _validate_output_file(output_file, dry_run_flag)
    _validate_chat_llm(chat_llm)

    output_file = Path(output_file) if output_file else None

    # 1. prepare the client
    agent_builder_client = get_agent_builder_client()
    _healthcheck_agent_builder_server(client=agent_builder_client)

    # 3. Agent Builder
    excluded_fields = _get_excluded_fields()
    try:
        agent = chat_with_agent_builder(agent_builder_client,chat_llm=chat_llm, description=description, dry_run_flag=dry_run_flag, output_file=output_file, llm=llm if llm else DEFAULT_LLM, excluded_fields=excluded_fields)
    except ConnectionError:
        logger.error(
            "Failed to connect to AI Builder server. Please ensure AI Builder is running via `orchestrate sever start --with-ai-builder`")
        sys.exit(1)
    except ClientAPIException:
        logger.error(
            "An unexpected server error has occurred with in the AI Builder server. Please check the logs via `orchestrate server logs`")
        sys.exit(1)

    if not dry_run_flag:
        message_lines = [
            "Your agent building session finished successfully!",
            f"Agent YAML saved in file:",
            f"{output_file.absolute()}"
        ]
    else:
        agents_controller = AgentsController()
        agent = agents_controller.reference_agent_dependencies(agent)
        message_lines = [
            "Your agent building session finished successfully!",
            agent.model_dump(exclude_none=True, exclude_unset=True, exclude=excluded_fields)
        ]
    __box_print(message_lines)


def _format_thread_messages(messages:List[dict]) -> List[dict]:
    """
        restructure and keep only the content relevant for refining the agent before sending to the refinement process
    :param messages: List of messages as returned from the threads endpoint
    :param messages:
    :return: List of dictionaries where each dictionary represents a message
    """
    new_messages = []
    for m in messages:
        m_dict = {'role': m['role'], 'content': m['content'][0]['text'], 'type': 'text'} # text message
        if m['step_history']:
            step_history = m['step_history']
            for step in step_history:
                step_details = step['step_details'][0]
                if step_details['type'] == 'tool_calls':  # tool call
                    for t in step_details['tool_calls']:
                        new_messages.append(
                            {'role': m['role'], 'type': 'tool_call', 'args': t['args'], 'name': t['name']})
                elif step_details['type'] == 'tool_response':  # tool response
                    new_messages.append({'role': m['role'], 'type': 'tool_response', 'content': step_details['content']})
        new_messages.append(m_dict)
        if m['message_state']:
            new_messages.append({'feedback': m['message_state']['content']['1']['feedback']})
    return new_messages


def _suggest_sorted(user_input: str, options: List[str]) -> List[str]:
    # Sort by similarity score
    return sorted(options, key=lambda x: difflib.SequenceMatcher(None, user_input, x).ratio(), reverse=True)

def submit_refine_agent_with_chats(agent_name: str, chat_llm: str | None, output_file: Path | None,
                                   use_last_chat: bool=False, dry_run_flag: bool = False) -> None:
    """
    Refines an existing agent's instructions using user selected chat trajectories and saves the updated agent configuration.

    This function performs a multi-step process to enhance an agent's prompt instructions based on user interactions:

    1. **Validation**: Ensures the output file path is valid and checks if the specified agent exists. If not found,
       it suggests similar agent names.
    2. **Chat Retrieval**: Fetches the 10 most recent chat threads associated with the agent. If no chats are found,
       the user is prompted to initiate a conversation.
    3. **User Selection**: Displays a summary of recent chats and allows the user to select which ones to use for refinement.
    4. **Refinement**: Sends selected chat messages to the AI Builder to generate refined instructions.
    5. **Update and Save**: Updates the agent's instructions and either prints the
       updated agent (if `dry_run_flag` is True) or saves it to the specified output file.

    Parameters:
        agent_name (str): The name of the agent to refine.
        chat_llm (str): The name of the model used by the refiner. If None, default model (llama-3-3-70b) is used.
        output_file (str): Path to the file where the refined agent configuration will be saved.
        use_last_chat(bool): If true, optimize by using the last conversation with the agent, otherwise let the use choose
        dry_run_flag (bool): If True, prints the refined agent configuration without saving it to disk.

    Returns:
        None
    """
    _validate_output_file(output_file, dry_run_flag)
    _validate_chat_llm(chat_llm)

    output_file = Path(output_file) if output_file else None

    agents_controller = AgentsController()
    agents_client = get_native_client()
    threads_client = get_threads_client()
    all_agents = agents_controller.get_all_agents(client=agents_client)
    cpe_client = get_cpe_client()
    _healthcheck_cpe_server(cpe_client)

    # Step 1 - validate agent exist. If not - list the agents sorted by their distance from the user input name
    agent_id = all_agents.get(agent_name)
    if agent_id is None:
        if len(all_agents) == 0:
            raise BadRequest("No agents in workspace\nCreate your first agent using `orchestrate agents ai-builder prompt-tune`")
        else:
            available_sorted_str = "\n".join(_suggest_sorted(agent_name, all_agents.keys()))
            raise BadRequest(f'Agent "{agent_name}" does not exist.\n\n'
                             f'Available agents:\n'
                             f'{available_sorted_str}')

    # Step 2 - retrieve chats (threads)
    try:
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Retrieve chats", total=None)
            all_threads = threads_client.get_all_threads(agent_id)
            if len(all_threads) == 0:
                progress.remove_task(task)
                progress.refresh()
                raise BadRequest(
                    f"No chats found for agent '{agent_name}'. To use autotune, please initiate at least one conversation with the agent. You can start a chat using `orchestrate chat start`.",
                   )
            last_10_threads = all_threads[:10] #TODO use batching when server allows
            last_10_chats = [_format_thread_messages(chat) for chat in
                             threads_client.get_threads_messages([thread['id'] for thread in last_10_threads])]

            progress.remove_task(task)
            progress.refresh()
    except ConnectionError:
        logger.error(
            f"Failed to retrieve threads (chats) for agent {agent_name}")
        sys.exit(1)
    except ClientAPIException:
        logger.error(
            f"An unexpected server error has occurred while retrieving threads for agent {agent_name}. Please check the logs via `orchestrate server logs`")
        sys.exit(1)

    # Step 3 - show chats and let the user choose
    if use_last_chat:
        title = "Selected chat"
    else:
        title = "10 Most Recent Chats"
    table = Table(title=title)
    table.add_column("Number", justify="right")
    table.add_column("Chat Date", justify="left")
    table.add_column("Title", justify="left")
    table.add_column("Last User Message", justify="left")
    table.add_column("Last User Feedback", justify="left")

    for i, (thread, chat) in enumerate(zip(last_10_threads, last_10_chats), start=1):
        all_user_messages = [msg for msg in chat if 'role' in msg and msg['role'] == 'user']

        if len(all_user_messages) == 0:
            last_user_message = ""
        else:
            last_user_message = all_user_messages[-1]['content']
        all_feedbacks = [msg for msg in chat if 'feedback' in msg and 'text' in msg['feedback']]
        if len(all_feedbacks) == 0:
            last_feedback = ""
        else:
            last_feedback = f"{'👍' if all_feedbacks[-1]['feedback']['is_positive'] else '👎'} {all_feedbacks[-1]['feedback']['text']}"

        table.add_row(str(i), datetime.strptime(thread['created_on'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime(
            '%B %d, %Y at %I:%M %p'), thread['title'], last_user_message, last_feedback)
        table.add_row("", "", "")
        if  use_last_chat:
            break

    rich.print(table)

    if use_last_chat:
        rich.print("Tuning using the last conversation with the agent")
        threads_messages = [last_10_chats[0]]
    else:
        threads_messages = get_user_selection(last_10_chats)

    # Step 4 - run the refiner
    try:
        with _get_progress_spinner() as progress:
            agent = agents_controller.get_agent_by_id(id=agent_id)
            tools_client = get_tool_client()
            if agent.guidelines:
                for guideline in agent.guidelines:
                    if not guideline.tool:
                        continue
                    tool_draft = tools_client.get_draft_by_id(guideline.tool)
                    guideline.tool = tool_draft["name"]
            excluded_fields = _get_excluded_fields(agent)
            task = progress.add_task(description="Running Prompt Refiner", total=None)
            knowledge_base_client = get_knowledge_bases_client()
            # loaded agent contains the ids of the tools/collabs/knowledge bases, convert them back to names.
            agent.tools = [tools_client.get_draft_by_id(id)['name'] for id in agent.tools]
            agent.knowledge_base = [knowledge_base_client.get_by_id(id)['name'] for id in agent.knowledge_base]
            agent.collaborators = agents_controller.reference_collaborators(agent).collaborators
            tools = _get_tools_from_names(agent.tools)
            collaborators = _get_agents_from_names(agent.collaborators)
            knowledge_bases = _get_knowledge_bases_from_names(agent.knowledge_base)
            if agent.instructions is None:
                raise BadRequest("Agent must have instructions in order to use the autotune command. To build an instruction use `orchestrate agents ai-builder prompt-tune -f <path_to_agent_yaml> -o <path_to_new_agent_yaml>`")

            response = _handle_agent_builder_server_errors(
                func=cpe_client.submit_refine_agent_with_chats,  # TODO @@@ make sure it exists
                instruction=agent.instructions,
                chat_llm=chat_llm,
                tools=tools,
                collaborators=collaborators,
                knowledge_bases=knowledge_bases,
                trajectories_with_feedback=threads_messages
            )

            progress.remove_task(task)
            progress.refresh()
    except ConnectionError:
        logger.error(
            "Failed to connect to AI Builder server. Please ensure AI Builder is running via `orchestrate server start --with-ai-builder`")
        sys.exit(1)
    except ClientAPIException:
        logger.error(
            "An unexpected server error has occurred with in the AI Builder server. Please check the logs via `orchestrate server logs`")
        sys.exit(1)

    # Step 5 - update the agent and print/save the results
    agent.instructions = response['instruction']
    agent.llm_config = None

    if dry_run_flag:
        rich.print(agent.model_dump(exclude_none=True, mode="json", exclude_unset=True, exclude=excluded_fields))
        return

    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    agent.id = None # remove existing agent id before saving
    AgentsController.persist_record(agent, output_file=str(output_file))

    logger.info(f"Your agent refinement session finished successfully!")
    logger.info(f"Agent YAML with the updated instruction saved in file: {os.path.abspath(output_file)}")



def get_user_selection(chats: List[List[Dict]]) -> List[List[Dict]]:
    """
    Prompts the user to select up to 5 chat threads by entering their indices.

    Parameters:
        chats (List[List[Dict]]): A list of chat threads, where each thread is a list of message dictionaries.

    Returns:
        List[List[Dict]]: A list of selected chat threads based on user input.
    """
    while True:
        try:
            eg_str = "1" if len(chats) < 2 else "1, 2"
            input_str = input(
                f"Please enter up to 5 indices of chats you'd like to select, separated by commas (e.g. {eg_str}): "
            )

            choices = [int(choice.strip()) for choice in input_str.split(',')]

            if len(choices) > 5:
                rich.print("You can select up to 5 chats only. Please try again.")
                continue

            if all(1 <= choice <= len(chats) for choice in choices):
                selected_threads = [chats[choice - 1] for choice in choices]
                return selected_threads
            else:
                rich.print(f"Please enter only numbers between 1 and {len(chats)}.")
        except ValueError:
            rich.print("Invalid input. Please enter valid integers separated by commas.")
