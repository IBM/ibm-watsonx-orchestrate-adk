from enum import Enum


class RegistryType(str, Enum):
    PYPI = 'pypi'
    TESTPYPI = 'testpypi'
    LOCAL = 'local'

    def __str__(self):
        return str(self.value)