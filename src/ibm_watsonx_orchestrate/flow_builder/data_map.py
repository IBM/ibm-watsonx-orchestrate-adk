from typing import Any, Optional, Self
from pydantic import BaseModel, Field, SerializeAsAny

from .types import (
    Assignment
)


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
        self.maps.append(line)

