import json
import inspect
import importlib
import sys
import yaml

from typing import List
from pathlib import Path
from .types import ToolkitSpec, ToolkitMCPInputSpec
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

class BaseToolkit:
    __toolkit_spec__: ToolkitSpec

    def __init__(self, spec: ToolkitSpec):
        self.__toolkit_spec__ = spec

    def __call__(self, **kwargs):
        pass

    def dump_spec(self, file: str) -> None:
        dumped = self.__toolkit_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)
        with safe_open(file, 'w') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f, allow_unicode=True)
            elif file.endswith('.json'):
                json.dump(dumped, f, indent=2)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

    def dumps_spec(self) -> str:
        dumped = self.__toolkit_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)
        return json.dumps(dumped, indent=2)

    def __repr__(self):
        return f"Toolkit(name='{self.__toolkit_spec__.name}', description='{self.__toolkit_spec__.description}')"

    @staticmethod
    def from_python(file: Path | str) -> List['BaseToolkit']:
        """Import all Toolkit instances from a Python file."""
        file_path = Path(file)
        file_directory = file_path.parent
        file_name = file_path.stem

        sys.path.append(str(file_directory))
        try:
            module = importlib.import_module(file_name)

            toolkits = []
            for _, obj in inspect.getmembers(module):
                if isinstance(obj, BaseToolkit):
                    toolkits.append(obj)
            return toolkits
        finally:
            # Always clean up sys.path
            if str(file_directory) in sys.path:
                sys.path.remove(str(file_directory))
    
    @staticmethod
    def from_spec(file: Path | str) -> 'BaseToolkit':
        """Load a toolkit configuration from a spec file."""
        file_path = Path(file)

        # Handle YAML/JSON spec files
        with safe_open(file_path, 'r') as f:
            if file_path.suffix in {'.yaml', '.yml'}:
                content = yaml_safe_load(f)
            elif file_path.suffix == '.json':
                content = json.load(f)
            else:
                raise BadRequest('file must end in .json, .yaml, or .yml. For Python files, use BaseToolkit.from_python() instead.')
        if not content.get("spec_version"):
                raise BadRequest(f"Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format")
        
        input_spec = ToolkitMCPInputSpec.model_validate(content)
        spec = ToolkitSpec.generate_toolkit_spec(input_spec)

        return BaseToolkit(spec=spec)
