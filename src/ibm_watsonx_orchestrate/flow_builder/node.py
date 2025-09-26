import json
from typing import Any, cast, Type
import uuid

import yaml
from pydantic import BaseModel, Field, SerializeAsAny, create_model
from enum import Enum

from .types import Assignment, DocExtConfigField, EndNodeSpec, NodeSpec, AgentNodeSpec, PromptNodeSpec, ScriptNodeSpec, TimerNodeSpec, StartNodeSpec, ToolNodeSpec, UserFieldKind, UserFieldOption, UserNodeSpec, DocProcSpec, \
                    DocExtSpec, DocExtConfig, DocClassifierSpec, DecisionsNodeSpec, DocClassifierConfig

from .data_map import DataMap

class Node(BaseModel):
    spec: SerializeAsAny[NodeSpec]
    input_map: dict[str, DataMap] | None = None

    def __call__(self, **kwargs):
        pass

    def dump_spec(self, file: str) -> None:
        dumped = self.spec.model_dump(mode='json',
                                      exclude_unset=True, exclude_none=True, by_alias=True)
        with open(file, 'w', encoding="utf-8") as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f, allow_unicode=True)
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
        if self.input_map is not None and "spec" in self.input_map:
            model_spec['input_map'] = {
                "spec": self.input_map["spec"].to_json()
            }

        return model_spec
    
    def map_node_input_with_variable(self, target_input_variable: str, variable: str, default_value: str = None) -> None:
        if self.input_map and "spec" in self.input_map:
            maps = self.input_map["spec"].maps or []
        else:
            maps = []
        
        curr_map_metadata = {
            "assignmentType": "variable"
        }

        target_variable = "self.input." + target_input_variable
        value_expression = "flow." + variable

        if default_value:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, default_value=default_value, metadata=curr_map_metadata))
        else:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, metadata=curr_map_metadata))

        node_input_map_spec = DataMap(maps=maps)
        if self.input_map and "spec" in self.input_map:
            self.input_map["spec"] = node_input_map_spec
        else:
            self.input_map = {"spec": node_input_map_spec}

    def map_input(self, input_variable: str, expression: str, default_value: str = None) -> None:
        if self.input_map and "spec" in self.input_map:
            maps = self.input_map["spec"].maps or []
        else:
            maps = []
        
        curr_map_metadata = {
            "assignmentType": "pyExpression"
        }

        target_variable = "self.input." + input_variable
        value_expression = expression

        if default_value:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, default_value=default_value, metadata=curr_map_metadata))
        else:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, metadata=curr_map_metadata))

        node_input_map_spec = DataMap(maps=maps)
        if self.input_map and "spec" in self.input_map:
            self.input_map["spec"] = node_input_map_spec
        else:
            self.input_map = {"spec": node_input_map_spec}

    def map_node_input_with_none(self, target_input_variable: str) -> None:
        if self.input_map and "spec" in self.input_map:
            maps = self.input_map["spec"].maps or []
        else:
            maps = []
        

        target_variable = "self.input." + target_input_variable

        maps.append(Assignment(target_variable=target_variable, value_expression=None))

        node_input_map_spec = DataMap(maps=maps)
        if self.input_map and "spec" in self.input_map:
            self.input_map["spec"] = node_input_map_spec
        else:
            self.input_map = {"spec": node_input_map_spec}

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
    

class ScriptNode(Node):
    def __repr__(self):
        return f"ScriptNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> ScriptNodeSpec:
        return cast(ScriptNodeSpec, self.spec)
    
    def updateScript(self, script: str):
        '''Update the script of a script node'''
        self.spec.fn = script

class UserNode(Node):
    def __repr__(self):
        return f"UserNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> UserNodeSpec:
        return cast(UserNodeSpec, self.spec)
    
    def field(self, 
              name: str,
              kind: UserFieldKind = UserFieldKind.Text,
              text: str | None = None,
              display_name: str | None = None,
              description: str | None = None,
              default: Any | None = None,
              option: UserFieldOption | None = None,
              min: Any | None = None,
              max: Any | None = None,
              direction: str | None = None,
              input_map: DataMap | None = None,
              is_list: bool = False,
              custom: dict[str, Any] | None = None,
              widget: str | None = None):
        self.get_spec().field(name=name,
                              kind=kind,
                              text=text,
                              display_name=display_name,
                              description=description,
                              default=default,
                              option=option,
                              min=min,
                              max=max,
                              is_list=is_list,
                              custom=custom,
                              widget=widget,
                              direction=direction,
                              input_map=input_map)

class AgentNode(Node):
    def __repr__(self):
        return f"AgentNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> AgentNodeSpec:
        return cast(AgentNodeSpec, self.spec)

class PromptNode(Node):
    def __repr__(self):
        return f"PromptNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> PromptNodeSpec:
        return cast(PromptNodeSpec, self.spec)
    
class DocProcNode(Node):
    def __repr__(self):
        return f"DocProcNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> DocProcSpec:
        return cast(DocProcSpec, self.spec)
    
class DocClassifierNode(Node):
    def __repr__(self):
        return f"DocClassifierNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> DocClassifierSpec:
        return cast(DocClassifierSpec, self.spec)

    @staticmethod
    def generate_config(llm: str, input_classes: type[BaseModel], min_confidence: float) -> DocClassifierConfig:
        return DocClassifierConfig(llm=llm, classes=input_classes.__dict__.values(), min_confidence=min_confidence)
    
class TimerNode(Node):
    def __repr__(self):
        return f"TimerNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> TimerNodeSpec:
        return cast(TimerNodeSpec, self.spec)
    
class DocExtNode(Node):
    def __repr__(self):
        return f"DocExtNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> DocExtSpec:
        return cast(DocExtSpec, self.spec)
    
    @staticmethod
    def generate_config(llm: str, fields: type[BaseModel]) -> DocExtConfig:
        return DocExtConfig(llm=llm, fields=fields.__dict__.values())
    
    @staticmethod
    def generate_docext_field_value_model(fields: type[BaseModel]) -> type[BaseModel]:
        create_field_value_description = lambda field_name: "Extracted value for " + field_name
        field_definitions = {}

        for name, value in fields.model_dump().items():
            field_type = str  
            field_kwargs = {
                "title": value['name'],
                "description": create_field_value_description(value['name']),
                "type": value["type"] if value["type"] != "date" else "string"
            }

            # Add json_schema_extra if type is 'date'
            if value["type"] == "date":
                field_kwargs["json_schema_extra"] = {"format": "date"}

            field_definitions[name] = (field_type, Field(**field_kwargs))

        DocExtFieldValue = create_model("DocExtFieldValue", **field_definitions)
        return DocExtFieldValue
    
class DecisionsNode(Node):
    def __repr__(self):
        return f"DecisionsNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> DecisionsNodeSpec:
        return cast(DecisionsNodeSpec, self.spec)
    
class NodeInstance(BaseModel):
    node: Node
    id: str # unique id of this task instance
    flow: Any # the flow this task belongs to

    def __init__(self, **kwargs): # type: ignore
        super().__init__(**kwargs)
        self.id = uuid.uuid4().hex
