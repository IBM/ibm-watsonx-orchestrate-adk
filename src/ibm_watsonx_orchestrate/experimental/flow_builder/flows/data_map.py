from typing import Any, List, cast
import uuid
import json
import yaml
from pydantic import BaseModel, Field, SerializeAsAny

from ibm_watsonx_orchestrate.agent_builder.tools.types import (
    ToolRequestBody, ToolResponseBody, JsonSchemaObject
)
from ..types import (
    _to_json_from_input_schema, _to_json_from_output_schema, SchemaRef, Assignment
)

class DataMapSpec(BaseModel):
 
    name: str

    def __init__(self, **data: Any) -> None:
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        super().__init__(**data)

    def to_json(self) -> dict[Any, dict]:
        '''Create a JSON object representing the data'''
        model_spec = {}
        model_spec["name"] = self.name
        return model_spec



class AssignmentDataMapSpec(DataMapSpec):
 
    maps: List[Assignment] 

    def to_json(self) -> dict[str, Any]:
        '''Create a JSON object representing the data'''
        model_spec = super().to_json()

        if self.maps:
            model_spec["maps"] = [assignment.model_dump() for assignment in self.maps]

        return model_spec


class DataMap(BaseModel):
 
    spec: SerializeAsAny[DataMapSpec]

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
        return f"DataMap(name='{self.spec.name}', description='{self.spec.description}')"

    def to_json(self) -> dict[str, Any]:
     
        obj = self.get_spec().to_json()

        return { "spec": obj }
    
    def get_spec(self) -> DataMapSpec:
     
        return self.spec
    
class AssignmentDataMap(DataMap):
    def get_spec(self) -> AssignmentDataMapSpec:
        return cast(AssignmentDataMapSpec, self.spec)
    
    def to_json(self) -> dict[str, Any]:
     
        obj = super().to_json()
        return obj
    
