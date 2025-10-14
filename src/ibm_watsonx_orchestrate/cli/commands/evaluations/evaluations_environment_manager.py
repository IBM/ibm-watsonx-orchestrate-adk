import logging
import yaml
from typing import Mapping, Any
from enum import StrEnum
from pathlib import Path

from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import (
    AgentsController,
    Agent,
    ExternalAgent,
    AssistantAgent,
)
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import (
    ToolsController,
    BaseTool,
)
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import (
    KnowledgeBaseController,
    KnowledgeBase,
)
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import (
    parse_file as kb_parse_file,
)
from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller import (
    EvaluationsController,
    EvaluateMode,
)
from ibm_watsonx_orchestrate.utils.file_manager import safe_open

logger = logging.getLogger(__name__)


class ArtifactTypes(StrEnum):
    """The allowed artifacts in the environment manager path.

    The environment manager config looks like this:
    ```json
        env1:
            agent:
                agents_path: None
            tools:
                tools_path: None
                tool_kind: None
                # any other tool flags
            knowledge:
                knowledge_base_path: None
        test_config: # path to config.yaml
        clean_up: True
    ```
    The allowed artifacts/keys are "agent", "tools", "knowledge"
    """

    agent = "agent"
    tools = "tools"
    knowledge = "knowledge"


class TestCaseManager:
    def __init__(
        self,
        env_settings: Mapping[str, Any],
        output_dir: str,
        mode: EvaluateMode = EvaluateMode.default,
    ):
        self.env_settings = env_settings
        self.cleanup = env_settings.get("clean_up", False)
        self.output_dir = output_dir
        self.mode = mode

        self.agent_controller = AgentsController()
        self.knowledge_controller = KnowledgeBaseController()
        self.tool_controller = None
        if (tool_settings := env_settings.get(ArtifactTypes.tools)):
            self.tool_controller = ToolsController(
                tool_kind=tool_settings.get("kind"),
                file=tool_settings.get("file"),
                requirements_file=tool_settings.get("requirements_file")
            )

        self.imported_artifacts = []

    def __enter__(self):
        for artifact in [
            ArtifactTypes.tools,
            ArtifactTypes.knowledge,
            ArtifactTypes.agent,
        ]:
            if artifact not in self.env_settings:
                continue

            artifact_settings = self.env_settings.get(artifact)
            if artifact == ArtifactTypes.tools:
                tools = ToolsController.import_tool(**artifact_settings)
                # import_tool returns Iterator[BaseTool], copy the iterator into a list for preservation
                # this is needed if user wants environment cleanup
                tools = [tool for tool in tools]
                self.imported_artifacts.append(tools)
                self.tool_controller.publish_or_update_tools(tools)
            elif artifact == ArtifactTypes.knowledge:
                KnowledgeBaseController.import_knowledge_base(**artifact_settings)
                kb_spec = kb_parse_file(artifact_settings.get("file"))
                self.imported_artifacts.append(kb_spec)
            elif artifact == ArtifactTypes.agent:
                artifact_settings["app_id"] = artifact_settings.get("app_id", None)
                agents = AgentsController.import_agent(**artifact_settings)
                self.agent_controller.publish_or_update_agents(agents)
                self.imported_artifacts.append(agents)

        eval = EvaluationsController()
        eval.evaluate(
            test_paths=self.env_settings.get("test_paths"),
            output_dir=self.output_dir,
            mode=self.mode,
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cleanup:
            logger.info("Cleaning environment")
            for artifact in self.imported_artifacts:
                # artifact can be a list of agents, tools
                for item in artifact:
                    if isinstance(item, BaseTool):
                        self.tool_controller.remove_tool(item.__tool_spec__.name)
                    if isinstance(item, KnowledgeBase):
                        self.knowledge_controller.remove_knowledge_base(
                            item.id, item.name
                        )
                    if isinstance(item, (Agent, AssistantAgent, ExternalAgent)):
                        self.agent_controller.remove_agent(item.name, item.kind)


def run_environment_manager(
    environment_manager_path: str,
    mode: EvaluateMode = EvaluateMode.default,
    output_dir: str = None,
):
    with safe_open(environment_manager_path, encoding="utf-8", mode="r") as f:
        env_settings = yaml.load(f, Loader=yaml.SafeLoader)

    for env in env_settings:
        if not env_settings.get(env).get("enabled"):
            continue
        results_folder = Path(output_dir) / env
        results_folder.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Processing environment: '%s'. Results will be saved to '%s'",
            env,
            results_folder,
        )

        with TestCaseManager(
            env_settings=env_settings.get(env),
            output_dir=str(results_folder),
            mode=mode,
        ):
            logger.info("Finished evaluation for environment: '%s'", env)
