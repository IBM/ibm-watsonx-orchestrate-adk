import json
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import OrchestrateAgentSpec


class OrchestrateAgent(OrchestrateAgentSpec):
    @staticmethod
    def from_spec(file: str) -> 'OrchestrateAgent':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                spec = OrchestrateAgentSpec.model_validate(yaml_safe_load(f))
            elif file.endswith('.json'):
                spec = OrchestrateAgentSpec.model_validate(json.load(f))
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

        return OrchestrateAgent(spec=spec)
    
    def __repr__(self):
        return f"OrchestrateAgent(name='{self.name}')"

    def __str__(self):
        return self.__repr__()