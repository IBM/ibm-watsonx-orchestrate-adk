import json
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import ExpertAgentSpec


class ExpertAgent(ExpertAgentSpec):

    @staticmethod
    def from_spec(file: str) -> 'ExpertAgent':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                agent = ExpertAgent.model_validate(yaml_safe_load(f))
            elif file.endswith('.json'):
                agent = ExpertAgent.model_validate(json.load(f))
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

        return agent
    
    def __repr__(self):
        return f"ExpertAgent(name='{self.name}', description='{self.description}')"

    def __str__(self):
        return self.__repr__()