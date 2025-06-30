import json

import yaml

from .types import ToolSpec

from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

class BaseTool:
    __tool_spec__: ToolSpec

    def __init__(self, spec: ToolSpec):
        self.__tool_spec__ = spec

    def __call__(self, **kwargs):
        pass

    def dump_spec(self, file: str) -> None:
        dumped = self.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)
        with open(file, 'w') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f)
            elif file.endswith('.json'):
                json.dump(dumped, f, indent=2)
            else:
                raise BadRequest('file must end in .json, .yaml, or .yml')

    def dumps_spec(self) -> str:
        dumped = self.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)
        return json.dumps(dumped, indent=2)

    def to_langchain_tool(self):
        from .integrations.langchain import as_langchain_tool
        return as_langchain_tool(self)

    def __repr__(self):
        return f"Tool(name='{self.__tool_spec__.name}', description='{self.__tool_spec__.description}')"
