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
            model_spec["maps"] = [assignment.model_dump() for assignment in self.maps]

    def add(self, line: Assignment) -> Self:
        self.maps.append(line)

