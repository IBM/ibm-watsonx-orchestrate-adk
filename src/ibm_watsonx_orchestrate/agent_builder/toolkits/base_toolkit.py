import json

import yaml

from .types import ToolkitSpec


class BaseToolkit:
    __toolkit_spec__: ToolkitSpec

    def __init__(self, spec: ToolkitSpec):
        self.__toolkit_spec__ = spec

    def __call__(self, **kwargs):
        pass

    def dump_spec(self, file: str) -> None:
        dumped = self.__toolkit_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)
        with open(file, 'w') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f)
            elif file.endswith('.json'):
                json.dump(dumped, f, indent=2)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

    def dumps_spec(self) -> str:
        dumped = self.__toolkit_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)
        return json.dumps(dumped, indent=2)

    def __repr__(self):
        return f"Toolkit(name='{self.__toolkit_spec__.name}', description='{self.__toolkit_spec__.description}')"
