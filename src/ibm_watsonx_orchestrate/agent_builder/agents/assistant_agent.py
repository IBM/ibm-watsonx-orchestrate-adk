import json
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import AssistantAgentSpec
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


class AssistantAgent(AssistantAgentSpec):

    @staticmethod
    def from_spec(file: str) -> 'AssistantAgent':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                content = yaml_safe_load(f)
            elif file.endswith('.json'):
                content = json.load(f)
            else:
                raise BadRequest('file must end in .json, .yaml, or .yml')
            
            if not content.get("spec_version"):
                raise BadRequest(f"Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format")
            agent = AssistantAgent.model_validate(content)

        return agent
    
    def __repr__(self):
        return f"AssistantAgent(name='{self.name}', description='{self.description}')"

    def __str__(self):
        return self.__repr__()
