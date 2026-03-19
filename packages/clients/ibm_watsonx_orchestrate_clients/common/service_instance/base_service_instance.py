from abc import ABC, abstractmethod


class BaseServiceInstance(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def _create_token(self) -> str:
        raise NotImplementedError("_create_token must be implemented")
