from typing import Any, Optional, Self
from pydantic import BaseModel, Field, SerializeAsAny

class Assignment(BaseModel):
    '''
    This class represents an assignment in the system.  Specify an expression that 
    can be used to retrieve or set a value in the FlowContext

    Attributes:
        target (str): The target of the assignment.  Always assume the context is the current Node. e.g. "name"
        source (str): The source code of the assignment.  This can be a simple variable name or a more python expression.  
            e.g. "node.input.name" or "=f'{node.output.name}_{node.output.id}'"

    '''
    target_variable: str
    value_expression: str | None = None
    has_no_value: bool = False
    default_value: Any | None = None
    metadata: dict = Field(default_factory=dict[str, Any])


class DataMap(BaseModel):
    maps: Optional[list[Assignment]] = Field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.maps and len(self.maps) > 0:
            model_spec["maps"] = []
            for assignment in self.maps:
                model_spec["maps"].append(assignment.model_dump())
        return model_spec

    def add(self, line: Assignment) -> Self:
        if self.maps is None:
            self.maps = []
        self.maps.append(line)
        return self

def ensure_datamap(obj, name: str):
    if obj and not isinstance(obj, DataMap):
        raise TypeError(f"{name} must be an instance of DataMap")

def add_assignment(target, source):
    if source and getattr(source, "maps", None):
        target.add(source.maps[0])

class DataMapSpec(BaseModel):
    spec: DataMap

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.spec:
            model_spec["spec"] = self.spec.to_json()
        return model_spec
