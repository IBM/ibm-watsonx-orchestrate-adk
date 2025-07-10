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
from ibm_watsonx_orchestrate.agent_builder.tools import ToolSpec, ToolPermission, ToolRequestBody, ToolResponseBody
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController, AgentKind
from ibm_watsonx_orchestrate.agent_builder.agents.types import DEFAULT_LLM
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.copilot.cpe.copilot_cpe_client import CPEClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)

def _validate_output_file(output_file: str, dry_run_flag: bool) -> None:
    if not output_file and not dry_run_flag:
        logger.error("Please provide a valid yaml output file. Or use the `--dry-run` flag to output generated agent content to terminal")
        sys.exit(1)
    
    if output_file and dry_run_flag:
        logger.error("Cannot set output file when performing a dry run")
        sys.exit(1)
    
    if output_file:
        _, file_extension = os.path.splitext(output_file)
        if file_extension not in  {".yaml", ".yml", ".json"}:
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
    spec = ToolSpec(**{"name": tool_name, "description": tool_name, "permission": ToolPermission.ADMIN, "input_schema": input_schema, "output_schema": output_schema})
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
            rich.print("\n")
            for tool_name in tool_names:
                if tool_name not in found_tools:
                    logger.warning(f"Failed to find tool named '{tool_name}'. Falling back to incomplete tool definition. Copilot performance maybe effected.")
                    tools.append(_get_incomplete_tool_from_name(tool_name))
            progress.remove_task(task)
    except ConnectionError:
        logger.warning(f"Failed to fetch tools from server. For optimal results please start the server and import the relevant tools {', '.join(tool_names)}.")
        tools = []
        for tool_name in tool_names:
            tools.append(_get_incomplete_tool_from_name(tool_name))

    return tools

def get_cpe_client() -> CPEClient:
    url = os.getenv('CPE_URL', "http://localhost:8081")
    return instantiate_client(client=CPEClient, url=url)


def gather_utterances(max: int) -> list[str]:
    utterances = []
    logger.info("Please provide 3 sample utterances you expect your agent to handle:")

    count = 0

    while count < max:
        utterance = Prompt.ask("  [green]>[/green]").strip()

        if utterance.lower() == 'q':
            break

        if utterance:
            utterances.append(utterance)
            count += 1

    return utterances

def pre_cpe_step(cpe_client, tool_client):
    user_message = ""
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Initilizing Prompt Engine", total=None)
        response = cpe_client.submit_pre_cpe_chat(user_message=user_message)
        progress.remove_task(task)

    res = {}
    while True:
        if "message" in response and response["message"]:
            rich.print('\n🤖 Copilot: ' + response["message"])
            user_message = Prompt.ask("\n👤 You").strip()
            message_content = {"user_message": user_message}
        elif "description" in response and response["description"]:
            res["description"] = response["description"]
            tools = find_tools_by_description(res["description"], tool_client)
            message_content = {"tools": tools}
        elif "metadata" in response:
            res["agent_name"] = response["metadata"]["agent_name"]
            res["agent_style"] = response["metadata"]["style"]
            res["tools"] = [t for t in tools if t["name"] in response["metadata"]["tools"]]
            return res
        with _get_progress_spinner() as progress:
            task = progress.add_task(description="Thinking...", total=None)
            response = cpe_client.submit_pre_cpe_chat(**message_content)
            progress.remove_task(task)

# TODO: Add description RAG search
def find_tools_by_description(description, tool_client):
    with _get_progress_spinner() as progress:
        task = progress.add_task(description="Fetching Tools", total=None)
        try:
            tools = tool_client.get()
        except ConnectionError:
            tools = []
            rich.print("\n")
            logger.warning("Failed to contact wxo server to fetch tools. Proceeding with empty tool list")
        progress.remove_task(task)
    return tools

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
    response=None
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
    prompt = 'My current prompt is:\n' + instr if instr else "I don't have an initial prompt."

    tools = _get_tools_from_names(agent.tools)

    try:
        new_prompt = talk_to_cpe(cpe_client=client, samples_file=samples_file, context_data={"prompt": prompt, 'tools': tools, 'description': agent.description})
    except ConnectionError:
        logger.error("Failed to connect to Copilot server. Please ensure Copilot is running via `orchestrate copilot start`")
        sys.exit(1)
    except ClientAPIException:
        logger.error("An unexpected server error has occur with in the Copilot server. Please check the logs via `orchestrate server logs`")
        sys.exit(1)

    if new_prompt:
        logger.info(f"The new instruction is: {new_prompt}")
        agent.instructions = new_prompt

        if dry_run_flag:
            rich.print(agent.model_dump())
        else:
            if os.path.dirname(output_file):
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
            AgentsController.persist_record(agent, output_file=output_file)


def get_tool_client(*args, **kwargs):
    return instantiate_client(ToolClient)

def create_agent(output_file: str, llm: str, samples_file: str | None, dry_run_flag: bool = False) -> None:
    _validate_output_file(output_file, dry_run_flag)
    # 1. prepare the clients
    cpe_client = get_cpe_client()
    tool_client = get_tool_client()

    # 2. Pre-CPE stage:
    try:
        res = pre_cpe_step(cpe_client, tool_client)
    except ConnectionError:
        logger.error("Failed to connect to Copilot server. Please ensure Copilot is running via `orchestrate copilot start`")
        sys.exit(1)
    except ClientAPIException:
        logger.error("An unexpected server error has occur with in the Copilot server. Please check the logs via `orchestrate server logs`")
        sys.exit(1)
        
    tools = res["tools"]
    description = res["description"]
    agent_name = res["agent_name"]
    agent_style = res["agent_style"]

    # 4. discuss the instructions
    instructions = talk_to_cpe(cpe_client, samples_file, {'tools': tools, 'description': description})

    # 6. create and save the agent
    llm = llm if llm else DEFAULT_LLM
    params = {
        'style': agent_style,
        'tools': [t['name'] for t in tools],
        'llm': llm
    }
    agent = AgentsController.generate_agent_spec(agent_name, AgentKind.NATIVE, description, **params)
    agent.instructions = instructions

    if dry_run_flag:
        rich.print(agent.model_dump())
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