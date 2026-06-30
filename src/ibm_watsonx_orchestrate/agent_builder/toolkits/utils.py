import os
import sys
import shutil
import logging
import tempfile

from pathlib import Path
from typing import Optional, List

from ibm_watsonx_orchestrate_core.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate_core.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.agent_builder.tools.base_tool import BaseTool
from ibm_watsonx_orchestrate.agent_builder.tools.utils import get_package_root, get_formated_requirements_lines, extract_python_tools

logger = logging.getLogger(__name__)


def _is_skill_script(file: Path, base: Path) -> bool:
    """Return True if file lives under a scripts/ directory — skill scripts must not be registered as tools."""
    parts = file.relative_to(base).parts
    return 'scripts' in parts[:-1]


def extract_python_toolkit_tools_from_folder(folder_path:str| Path, app_ids: Optional[List[str]] = None) -> List[BaseTool]:
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise BadRequest(f"Provided Python bundle '{folder_path}', does not exist")
        if not folder_path.is_dir():
            raise BadRequest("The package root for python toolkits must be a valid folder")

        with tempfile.TemporaryDirectory(prefix=f"{folder_path.stem}_") as temp_dir:
            shutil.copytree(folder_path, temp_dir, dirs_exist_ok=True)
            sys.path.insert(0, temp_dir)
            temp_path = Path(temp_dir)
            tools = []
            try:
                requirements_file_path = folder_path.absolute().joinpath("requirements.txt")
                resolved_requirements_file = str(requirements_file_path) if requirements_file_path.exists() else None
                requirements_lines = get_formated_requirements_lines(requirement_file=resolved_requirements_file)

                temp_requirements_path = temp_path / "requirements.txt"

                with safe_open(temp_requirements_path, 'w') as fp:
                    fp.writelines(requirements_lines)

                # Get all Python files
                python_files = list(temp_path.rglob('*.py'))
                for file in python_files:
                    if _is_skill_script(file, temp_path):
                        rel = file.relative_to(temp_path)
                        logger.warning(f"Skipping skill script '{rel}': files under 'scripts/' directories are not loaded as tools")
                        continue
                    

                    tools.extend(extract_python_tools(file=file, package_root=temp_dir, app_ids=app_ids, requirements_file=temp_requirements_path, log_requirements_path=False, requirements_file_required=False, belongs_to_toolkit=True))

            finally:
                # Remove temp directory from path
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

            return tools
