from enum import Enum

class SpecVersion(str, Enum):
    V1 = "v1"

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)