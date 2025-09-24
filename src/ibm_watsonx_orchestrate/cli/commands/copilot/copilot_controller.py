import logging
import os
import sys
import csv

import rich
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from requests import ConnectionError
from typing import List
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import KnowledgeBaseSpec
from ibm_watsonx_orchestrate.agent_builder.tools import ToolSpec, ToolPermission, ToolRequestBody, ToolResponseBody
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController, AgentKind, SpecVersion
from ibm_watsonx_orchestrate.agent_builder.agents.types import DEFAULT_LLM, BaseAgentSpec
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.copilot.cpe.copilot_cpe_client import CPEClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)


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


def get_cpe_client() -> CPEClient:
    url = os.getenv('CPE_URL', "http://localhost:8081")
    return instantiate_client(client=CPEClient, url=url)


def get_tool_client(*args, **kwargs):
    return instantiate_client(ToolClient)


def get_knowledge_bases_client(*args, **kwargs):
    return instantiate_client(KnowledgeBaseClient)


def get_native_client(*args, **kwargs):
    return instantiate_client(AgentClient)


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


def pre_cpe_step(cpe_client):
    tools_agents_and_knowledge_bases = get_deployed_tools_agents_and_knowledge_bases()
    user_message = ""
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Initializing Prompt Engine", total=None)
        response = cpe_client.submit_pre_cpe_chat(user_message=user_message)
        progress.remove_task(task)

    res = {}
    while True:
        if "message" in response and response["message"]:
            rich.print('\n🤖 Copilot: ' + response["message"])
            user_message = Prompt.ask("\n👤 You").strip()
            message_content = {"user_message": user_message}
        elif "description" in response and response["description"]:  # after we have a description, we pass the all tools
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
        elif "knowledge_bases" in response and response['knowledge_bases'] is not None:  # after we have knowledge bases, we pass selected=True to mark that all selection were done
            res["knowledge_bases"] = [a for a in tools_agents_and_knowledge_bases["knowledge_bases"] if
                                      a["name"] in response["knowledge_bases"]]
            message_content = {"selected": True}
        elif "agent_name" in response and response['agent_name'] is not None:  # once we have a name and style, this phase has ended
            res["agent_name"] = response["agent_name"]
            res["agent_style"] = response["agent_style"]
            return res
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Thinking...", total=None)
            response = cpe_client.submit_pre_cpe_chat(**message_content)
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
            with open(samples_file) as f:
                examples = f.read().split('\n')
        elif samples_file.endswith('.csv'):
            with open(samples_file, 'r', encoding='utf-8') as f:
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


def talk_to_cpe(cpe_client, samples_file=None, context_data=None):
    context_data = context_data or {}
    examples = gather_examples(samples_file)
    # upload or gather input examples
    context_data['examples'] = examples
    response = None
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Thinking...", total=None)
        response = cpe_client.init_with_context(context_data=context_data)
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
                response = cpe_client.invoke(prompt=message)
                progress.remove_task(task)

    return accepted_prompt


def prompt_tune(agent_spec: str, output_file: str | None, samples_file: str | None, dry_run_flag: bool) -> None:
    agent = AgentsController.import_agent(file=agent_spec, app_id=None)[0]
    agent_kind = agent.kind

    if agent_kind != AgentKind.NATIVE:
        logger.error(
            f"Only native agents are supported for prompt tuning. Provided agent spec is on kind '{agent_kind}'")
        sys.exit(1)

    if not output_file and not dry_run_flag:
        output_file = agent_spec

    _validate_output_file(output_file, dry_run_flag)

    client = get_cpe_client()

    instr = agent.instructions

    tools = _get_tools_from_names(agent.tools)

    collaborators = _get_agents_from_names(agent.collaborators)

    knowledge_bases = _get_knowledge_bases_from_names(agent.knowledge_base)
    try:
        new_prompt = talk_to_cpe(cpe_client=client,
                                samples_file=samples_file,
                                context_data={
                                    "initial_instruction": instr,
                                    'tools': tools,
                                    'description': agent.description,
                                    "collaborators": collaborators,
                                    "knowledge_bases": knowledge_bases
                                })
    except ConnectionError:
        logger.error(
            "Failed to connect to Copilot server. Please ensure Copilot is running via `orchestrate copilot start`")
        sys.exit(1)
    except ClientAPIException:
        logger.error(
            "An unexpected server error has occur with in the Copilot server. Please check the logs via `orchestrate server logs`")
        sys.exit(1)

    if new_prompt:
        logger.info(f"The new instruction is: {new_prompt}")
        agent.instructions = new_prompt

        if dry_run_flag:
            rich.print(agent.model_dump(exclude_none=True))
        else:
            if os.path.dirname(output_file):
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
            AgentsController.persist_record(agent, output_file=output_file)


def create_agent(output_file: str, llm: str, samples_file: str | None, dry_run_flag: bool = False) -> None:
    _validate_output_file(output_file, dry_run_flag)
    # 1. prepare the clients
    cpe_client = get_cpe_client()

    # 2. Pre-CPE stage:
    try:
        res = pre_cpe_step(cpe_client)
    except ConnectionError:
        logger.error(
            "Failed to connect to Copilot server. Please ensure Copilot is running via `orchestrate copilot start`")
        sys.exit(1)
    except ClientAPIException:
        logger.error(
            "An unexpected server error has occur with in the Copilot server. Please check the logs via `orchestrate server logs`")
        sys.exit(1)

    tools = res["tools"]
    collaborators = res["collaborators"]
    knowledge_bases = res["knowledge_bases"]
    description = res["description"]
    agent_name = res["agent_name"]
    agent_style = res["agent_style"]

    # 4. discuss the instructions
    instructions = talk_to_cpe(cpe_client, samples_file,
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
        rich.print(agent.model_dump(exclude_none=True))
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
