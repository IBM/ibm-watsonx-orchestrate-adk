import json

import yaml

from .types import ToolSpec

from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.file_manager import safe_open

class BaseTool:
    __tool_spec__: ToolSpec

    def __init__(self, spec: ToolSpec):
        self.__tool_spec__ = spec

    def __call__(self, **kwargs):
        pass

    def dump_spec(self, file: str, exclude_none=True) -> None:
        dumped = self.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=exclude_none, by_alias=True)
        with safe_open(file, 'w') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f, allow_unicode=True)
            elif file.endswith('.json'):
                json.dump(dumped, f, indent=2)
            else:
                raise BadRequest('file must end in .json, .yaml, or .yml')

    def dumps_spec(self, exclude_none=True) -> str:
        dumped = self.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=exclude_none, by_alias=True)
        return json.dumps(dumped, indent=2)

    def to_langchain_tool(self):
        from .integrations.langchain import as_langchain_tool
        return as_langchain_tool(self)

    def __repr__(self):
        return f"Tool(name='{self.__tool_spec__.name}', description='{self.__tool_spec__.description}')"
