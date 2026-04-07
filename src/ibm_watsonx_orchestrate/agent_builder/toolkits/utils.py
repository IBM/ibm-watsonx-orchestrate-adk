import os
import sys
import shutil
import tempfile

from pathlib import Path
from typing import Optional, List

from ibm_watsonx_orchestrate_core.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate_core.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.agent_builder.tools.base_tool import BaseTool
from ibm_watsonx_orchestrate.agent_builder.tools.utils import get_package_root, get_formated_requirements_lines, extract_python_tools

def extract_python_toolkit_tools_from_folder(folder_path:str| Path, app_ids: Optional[List[str]] = None) -> List[BaseTool]:
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise BadRequest(f"Provided Python bundle '{folder_path}', does not exist")
        if not folder_path.is_dir():
            raise BadRequest("The package root for python toolkits must be a valid folder")
        
        with tempfile.TemporaryDirectory(prefix=f"{folder_path.stem}_", dir='/tmp') as temp_dir:
            shutil.copytree(folder_path, temp_dir, dirs_exist_ok=True)
            sys.path.insert(0, temp_dir)
            temp_path = Path(temp_dir)
            tools = []
            try:
                resolved_requirements_file = folder_path.absolute().joinpath("requirements.txt") if get_package_root(str(folder_path)) is not None else None

                requirements_lines = get_formated_requirements_lines(requirement_file=resolved_requirements_file)

                temp_requirements_path = temp_path / "requirements.txt"

                with safe_open(temp_requirements_path, 'w') as fp:
                    fp.writelines(requirements_lines)

                # Get all Python files
                python_files = python_files = list(temp_path.rglob('*.py'))
                for file in python_files:
                    tools.extend(extract_python_tools(file=file, package_root=temp_dir, app_ids=app_ids, requirements_file=temp_requirements_path))
            finally:
                # Remove temp directory from path
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)
            
            return tools