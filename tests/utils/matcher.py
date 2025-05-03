import json
from typing import Dict, Any

from pydantic import BaseModel


class MatchesObjectContaining:
    def __init__(self, **kwargs):
        self.matches = kwargs

    def __eq__(self, other) -> bool:
        if isinstance(other, BaseModel):
            other = other.model_dump()

        if isinstance(other, Dict):
            for k, v in self.matches.items():
                if other[k] != v:
                    return False
        else:
            raise RuntimeError(
                f"MatchesObjectContaining not implemented for type: {type(other)}, must be an instance of dict or BaseModel")

        return True

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"MatchesObjectContaining({json.dumps(self.matches, indent=2)})"


class MatchesObject:
    def __init__(self, **kwargs):
        self.matches = kwargs

    def __eq__(self, other) -> bool:
        if isinstance(other, BaseModel):
            other = other.model_dump()

        if isinstance(other, Dict):

            for k, v in self.matches.items():
                if other[k] != v:
                    return False
        else:
            raise RuntimeError(
                f"MatchesObject not implemented for type: {type(other)}, must be an instance of dict or BaseModel")

        return True

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"MatchesObjectContaining({json.dumps(self.matches, indent=2)})"


class MatchAny:
    def __init__(self, type: Any = None):
        self.type = type

    def __eq__(self, other: Any):
        if self.type is not None:
            return isinstance(other, self.type)
        return True

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.type is not None:
            return f"Any({self.type})"

        return 'Any'


class MatchesStringContaining:
    def __init__(self, containing):
        self.str = containing

    def __eq__(self, other) -> bool:
        return self.str in other

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"MatchesStringContaining({self.str})"