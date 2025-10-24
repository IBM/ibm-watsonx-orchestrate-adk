import logging
import os
import sys
import csv
import difflib
import re
from datetime import datetime
from functools import wraps

import rich
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from requests import ConnectionError
from typing import List, Dict
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import KnowledgeBaseSpec
from ibm_watsonx_orchestrate.agent_builder.tools import ToolSpec, ToolPermission, ToolRequestBody, ToolResponseBody
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController, AgentKind, SpecVersion
from ibm_watsonx_orchestrate.agent_builder.agents.types import DEFAULT_LLM, BaseAgentSpec
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient
from ibm_watsonx_orchestrate.client.threads.threads_client import ThreadsClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.copilot.cpe.copilot_cpe_client import CPEClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)


def _handle_cpe_server_errors(func=None, *args, **kwargs):
    def decorator(inner_func):
        @wraps(inner_func)
        def wrapper(*args, **kwargs):
            try:
                return inner_func(*args, **kwargs)
            except ConnectionError:
                logger.error(
                    "Failed to connect to Copilot server. Please ensure Copilot is running via `orchestrate copilot start`")
                sys.exit(1)
            except ClientAPIException:
                logger.error(
                    "An unexpected server error has occurred with in the Copilot server. Please check the logs via `orchestrate server logs`")
                sys.exit(1)
        return wrapper

    # If func is not None, it means the decorator is used without arguments
    if func is not None and callable(func):
        return decorator(func)(*args, **kwargs)

    # Otherwise, return the actual decorator
    return decorator


def _validate_output_file(output_file: str, dry_run_flag: bool) -> None:
    if not output_file and not dry_run_flag:
        logger.error(
            "Please provide a valid yaml output file. Or use the `--dry-run` flag to output generated agent content to terminal")
        sys.exit(1)

    if output_file and dry_run_flag:
        logger.error("Cannot set output file when performing a dry run")
        sys.exit(1)

    if output_file:
        _, file_extension = os.path.splitext(output_file)
        if file_extension not in {".yaml", ".yml", ".json"}:
            logger.error("Output file must be of type '.yaml', '.yml' or '.json'")
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
    spec = BaseAgentSpec(**{"name": agent_name, "description": agent_name, "kind": AgentKind.NATIVE})
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
                        f"Failed to find tool named '{tool_name}'. Falling back to incomplete tool definition. Copilot performance maybe effected.")
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

    native_agents_client = get_native_client()

    try:
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Fetching agents", total=None)
            agents = native_agents_client.get_drafts_by_names(collaborators_names)
            found_agents = {tool.get("name") for tool in agents}
            progress.remove_task(task)
            progress.refresh()
            for collaborator_name in collaborators_names:
                if collaborator_name not in found_agents:
                    logger.warning(
                        f"Failed to find agent named '{collaborator_name}'. Falling back to incomplete agent definition. Copilot performance maybe effected.")
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
                        f"Failed to find knowledge base named '{kb_name}'. Falling back to incomplete knowledge base definition. Copilot performance maybe effected.")
                    knowledge_bases.append(_get_incomplete_knowledge_base_from_name(kb_name))
    except ConnectionError:
        logger.warning(
            f"Failed to fetch knowledge bases from server. For optimal results please start the server and import the relevant knowledge bases {', '.join(kb_names)}.")
        knowledge_bases = []
        for kb_name in kb_names:
            knowledge_bases.append(_get_incomplete_knowledge_base_from_name(kb_name))

    return knowledge_bases

@_handle_cpe_server_errors()
def _healthcheck_cpe_server(client: CPEClient | None = None):
    if not client:
        client = get_cpe_client()
    client.healthcheck()

def get_cpe_client() -> CPEClient:
    url = os.getenv('CPE_URL', "http://localhost:8081")
    return instantiate_client(client=CPEClient, url=url)


def get_tool_client(*args, **kwargs):
    return instantiate_client(ToolClient)


def get_knowledge_bases_client(*args, **kwargs):
    return instantiate_client(KnowledgeBaseClient)


def get_native_client(*args, **kwargs):
    return instantiate_client(AgentClient)


def get_threads_client():
    return instantiate_client(ThreadsClient)


def gather_utterances(max: int) -> list[str]:
    utterances = []
    logger.info("Please provide 3 sample utterances you expect your agent to handle:")

    count = 0

    while count < max:
        utterance = Prompt.ask("  [green]>[/green]").strip()

        if utterance:
            utterances.append(utterance)
            count += 1

    return utterances


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

@_handle_cpe_server_errors()
def pre_cpe_step(cpe_client, chat_llm):
    tools_agents_and_knowledge_bases = get_deployed_tools_agents_and_knowledge_bases()
    user_message = ""
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Initializing Prompt Engine", total=None)
        response = cpe_client.submit_pre_cpe_chat(chat_llm=chat_llm, user_message=user_message)
        progress.remove_task(task)

    res = {}
    while True:
        if "message" in response and response["message"]:
            rich.print('\n🤖 Copilot: ' + response["message"])
            user_message = Prompt.ask("\n👤 You").strip()
            message_content = {"user_message": user_message}
        elif "description" in response and response[
            "description"]:  # after we have a description, we pass the all tools
            res["description"] = response["description"]
            message_content = {"tools": tools_agents_and_knowledge_bases['tools']}
        elif "tools" in response and response[
            'tools'] is not None:  # after tools were selected, we pass all collaborators
            res["tools"] = [t for t in tools_agents_and_knowledge_bases["tools"] if
                            t["name"] in response["tools"]]
            message_content = {"collaborators": tools_agents_and_knowledge_bases['collaborators']}
        elif "collaborators" in response and response[
            'collaborators'] is not None:  # after we have collaborators, we pass all knowledge bases
            res["collaborators"] = [a for a in tools_agents_and_knowledge_bases["collaborators"] if
                                    a["name"] in response["collaborators"]]
            message_content = {"knowledge_bases": tools_agents_and_knowledge_bases['knowledge_bases']}
        elif "knowledge_bases" in response and response[
            'knowledge_bases'] is not None:  # after we have knowledge bases, we pass selected=True to mark that all selection were done
            res["knowledge_bases"] = [a for a in tools_agents_and_knowledge_bases["knowledge_bases"] if
                                      a["name"] in response["knowledge_bases"]]
            message_content = {"selected": True}
        elif "agent_name" in response and response[
            'agent_name'] is not None:  # once we have a name and style, this phase has ended
            res["agent_name"] = response["agent_name"]
            res["agent_style"] = response["agent_style"]
            return res
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Thinking...", total=None)
            response = cpe_client.submit_pre_cpe_chat(chat_llm=chat_llm,**message_content)
            progress.remove_task(task)


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


def gather_examples(samples_file=None):
    if samples_file:
        if samples_file.endswith('.txt'):
            with safe_open(samples_file) as f:
                examples = f.read().split('\n')
        elif samples_file.endswith('.csv'):
            with safe_open(samples_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if 'utterance' not in reader.fieldnames:
                    raise BadRequest("CSV must have a column named 'utterance'")
                examples = [row['utterance'].strip() for row in reader if row['utterance'].strip()]
        else:
            raise BadRequest(f'Unsupported samples file format: {os.path.basename(samples_file)}')
    else:
        examples = gather_utterances(3)

    console = Console()
    logger.info("You provided the following samples:")
    for i, utterance in enumerate(examples, 1):
        console.print(f"  {i}. {utterance}")

    return examples

@_handle_cpe_server_errors()
def talk_to_cpe(cpe_client, chat_llm, samples_file=None, context_data=None):
    context_data = context_data or {}
    examples = gather_examples(samples_file)
    # upload or gather input examples
    context_data['examples'] = examples
    response = None
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Thinking...", total=None)
        response = cpe_client.init_with_context(chat_llm=chat_llm, context_data=context_data)
        progress.remove_task(task)
    accepted_prompt = None
    while accepted_prompt is None:
        resp = response.get('response')[0]
        accepted_prompt = resp.get("final_zsh_prompt", None)
        if not accepted_prompt:
            cpe_message = resp.get("message", "")
            rich.print('\n🤖 Copilot: ' + cpe_message)
            message = Prompt.ask("\n👤 You").strip()
            with _get_progress_spinner() as progress:
                task = progress.add_task(description="Thinking...", total=None)
                response = cpe_client.invoke(chat_llm=chat_llm, prompt=message)
                progress.remove_task(task)

    return accepted_prompt


def prompt_tune(agent_spec: str, chat_llm: str | None, output_file: str | None, samples_file: str | None, dry_run_flag: bool) -> None:
    agent = AgentsController.import_agent(file=agent_spec, app_id=None)[0]
    agent_kind = agent.kind

    if agent_kind != AgentKind.NATIVE:
        logger.error(
            f"Only native agents are supported for prompt tuning. Provided agent spec is on kind '{agent_kind}'")
        sys.exit(1)

    if not output_file and not dry_run_flag:
        output_file = agent_spec

    _validate_output_file(output_file, dry_run_flag)
    _validate_chat_llm(chat_llm)

    client = get_cpe_client()
    _healthcheck_cpe_server(client)

    instr = agent.instructions

    tools = _get_tools_from_names(agent.tools)

    collaborators = _get_agents_from_names(agent.collaborators)

    knowledge_bases = _get_knowledge_bases_from_names(agent.knowledge_base)
    new_prompt = talk_to_cpe(cpe_client=client,
                                chat_llm=chat_llm,
                                samples_file=samples_file,
                                context_data={
                                    "initial_instruction": instr,
                                    'tools': tools,
                                    'description': agent.description,
                                    "collaborators": collaborators,
                                    "knowledge_bases": knowledge_bases
                                })

    if new_prompt:
        logger.info(f"The new instruction is: {new_prompt}")
        agent.instructions = new_prompt

        if dry_run_flag:
            rich.print(agent.model_dump(exclude_none=True, mode="json"))
        else:
            if os.path.dirname(output_file):
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
            AgentsController.persist_record(agent, output_file=output_file)

def _validate_chat_llm(chat_llm):
    if chat_llm:
        formatted_chat_llm = re.sub(r'[^a-zA-Z0-9/]', '-', chat_llm)
        if "llama-3-3-70b-instruct" not in formatted_chat_llm:
            raise BadRequest(f"Unsupported chat model for copilot {chat_llm}. Copilot supports only llama-3-3-70b-instruct at this point.")

def create_agent(output_file: str, llm: str, chat_llm: str | None, samples_file: str | None, dry_run_flag: bool = False) -> None:
    _validate_output_file(output_file, dry_run_flag)
    _validate_chat_llm(chat_llm)
    # 1. prepare the clients
    cpe_client = get_cpe_client()

    # 2. Ensure the copilto server is started
    _healthcheck_cpe_server(cpe_client)

    # 3. Pre-CPE stage:
    res = pre_cpe_step(cpe_client, chat_llm=chat_llm)

    tools = res["tools"]
    collaborators = res["collaborators"]
    knowledge_bases = res["knowledge_bases"]
    description = res["description"]
    agent_name = res["agent_name"]
    agent_style = res["agent_style"]

    # 4. discuss the instructions
    instructions = talk_to_cpe(cpe_client, chat_llm, samples_file,
                               {'description': description, 'tools': tools, 'collaborators': collaborators,
                                'knowledge_bases': knowledge_bases})

    # 6. create and save the agent
    llm = llm if llm else DEFAULT_LLM
    params = {
        'style': agent_style,
        'tools': [t['name'] for t in tools],
        'llm': llm,
        'collaborators': [c['name'] for c in collaborators],
        'knowledge_base': [k['name'] for k in knowledge_bases]
        # generate_agent_spec expects knowledge_base and not knowledge_bases
    }
    agent = AgentsController.generate_agent_spec(agent_name, AgentKind.NATIVE, description, **params)
    agent.instructions = instructions
    agent.spec_version = SpecVersion.V1

    if dry_run_flag:
        rich.print(agent.model_dump(exclude_none=True, mode="json"))
        return

    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    AgentsController.persist_record(agent, output_file=output_file)

    message_lines = [
        "Your agent building session finished successfully!",
        f"Agent YAML saved in file:",
        f"{os.path.abspath(output_file)}"
    ]

    # Determine the width of the frame
    max_length = max(len(line) for line in message_lines)
    frame_width = max_length + 4  # Padding for aesthetics

    # Print the framed message
    rich.print("╔" + "═" * frame_width + "╗")
    for line in message_lines:
        rich.print("║  " + line.ljust(max_length) + "  ║")
    rich.print("╚" + "═" * frame_width + "╝")


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

def refine_agent_with_trajectories(agent_name: str, chat_llm: str | None, output_file: str | None,
                                   use_last_chat: bool=False, dry_run_flag: bool = False) -> None:
    """
    Refines an existing agent's instructions using user selected chat trajectories and saves the updated agent configuration.

    This function performs a multi-step process to enhance an agent's prompt instructions based on user interactions:

    1. **Validation**: Ensures the output file path is valid and checks if the specified agent exists. If not found,
       it suggests similar agent names.
    2. **Chat Retrieval**: Fetches the 10 most recent chat threads associated with the agent. If no chats are found,
       the user is prompted to initiate a conversation.
    3. **User Selection**: Displays a summary of recent chats and allows the user to select which ones to use for refinement.
    4. **Refinement**: Sends selected chat messages to the Copilot Prompt Engine (CPE) to generate refined instructions.
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
            raise BadRequest("No agents in workspace\nCreate your first agent using `orchestrate copilot prompt-tune`")
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
    with _get_progress_spinner() as progress:
        agent = agents_controller.get_agent_by_id(id=agent_id)
        task = progress.add_task(description="Running Prompt Refiner", total=None)
        tools_client = get_tool_client()
        knowledge_base_client = get_knowledge_bases_client()
        # loaded agent contains the ids of the tools/collabs/knowledge bases, convert them back to names.
        agent.tools = [tools_client.get_draft_by_id(id)['name'] for id in agent.tools]
        agent.knowledge_base = [knowledge_base_client.get_by_id(id)['name'] for id in agent.knowledge_base]
        agent.collaborators = [agents_client.get_draft_by_id(id)['name'] for id in agent.collaborators]
        tools = _get_tools_from_names(agent.tools)
        collaborators = _get_agents_from_names(agent.collaborators)
        knowledge_bases = _get_knowledge_bases_from_names(agent.knowledge_base)
        if agent.instructions is None:
            raise BadRequest("Agent must have instructions in order to use the autotune command. To build an instruction use `orchestrate copilot prompt-tune -f <path_to_agent_yaml> -o <path_to_new_agent_yaml>`")
        response = _handle_cpe_server_errors(
            func=cpe_client.refine_agent_with_chats,
            instruction=agent.instructions,
            chat_llm=chat_llm,
            tools=tools,
            collaborators=collaborators,
            knowledge_bases=knowledge_bases,
            trajectories_with_feedback=threads_messages
            )
        progress.remove_task(task)
        progress.refresh()

    # Step 5 - update the agent and print/save the results
    agent.instructions = response['instruction']

    if dry_run_flag:
        rich.print(agent.model_dump(exclude_none=True, mode="json"))
        return

    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    agent.id = None # remove existing agent id before saving
    AgentsController.persist_record(agent, output_file=output_file)

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
