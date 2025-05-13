import json
from typing import Any, cast
import uuid

import yaml
from pydantic import BaseModel, SerializeAsAny

from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject, ToolResponseBody
from .utils import get_valid_name

from .types import EndNodeSpec, JsonSchemaObjectRef, NodeSpec, AgentNodeSpec, StartNodeSpec, ToolNodeSpec
from .flows.data_map import DataMap

class Node(BaseModel):
    spec: SerializeAsAny[NodeSpec]
    input_map: DataMap | None = None

    def __call__(self, **kwargs):
        pass

    def dump_spec(self, file: str) -> None:
        dumped = self.spec.model_dump(mode='json',
                                      exclude_unset=True, exclude_none=True, by_alias=True)
        with open(file, 'w', encoding="utf-8") as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f)
            elif file.endswith('.json'):
                json.dump(dumped, f, indent=2)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

    def dumps_spec(self) -> str:
        dumped = self.spec.model_dump(mode='json',
                                      exclude_unset=True, exclude_none=True, by_alias=True)
        return json.dumps(dumped, indent=2)

    def __repr__(self):
        return f"Node(name='{self.spec.name}', description='{self.spec.description}')"

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        model_spec["spec"] = self.spec.to_json()
        if self.input_map is not None:
            model_spec['input_map'] = self.input_map.to_json()
        if hasattr(self, "output_map") and self.output_map is not None:
            model_spec["output_map"] = self.output_map.to_json()

        return model_spec

class StartNode(Node):
    def __repr__(self):
        return f"StartNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> StartNodeSpec:

        return cast(StartNodeSpec, self.spec)

class EndNode(Node):
    def __repr__(self):
        return f"EndNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> EndNodeSpec:

        return cast(EndNodeSpec, self.spec)
    
class ToolNode(Node):
    def __repr__(self):
        return f"ToolNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> ToolNodeSpec:

        return cast(ToolNodeSpec, self.spec)

class UserNode(Node):
    def __repr__(self):
        return f"UserNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> NodeSpec:

        return cast(NodeSpec, self.spec)

class AgentNode(Node):
    def __repr__(self):
        return f"AgentNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> AgentNodeSpec:

        return cast(AgentNodeSpec, self.spec)

class NodeInstance(BaseModel):
    node: Node
    id: str # unique id of this task instance
    flow: Any # the flow this task belongs to

    def __init__(self, **kwargs): # type: ignore
        super().__init__(**kwargs)
        self.id = uuid.uuid4().hex
