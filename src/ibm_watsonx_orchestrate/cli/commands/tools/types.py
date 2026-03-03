from enum import Enum


class RegistryType(str, Enum):
    PYPI = 'pypi'
    TESTPYPI = 'testpypi'
    LOCAL = 'local'
    SKIP= 'skip'

    def __str__(self):
        return str(self.value)