import json
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import KnowledgeBaseSpec


class KnowledgeBase(KnowledgeBaseSpec):

    @staticmethod
    def from_spec(file: str) -> 'KnowledgeBase':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                content = yaml_safe_load(f)
            elif file.endswith('.json'):
                content = json.load(f)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')
            if not content.get("spec_version"):
                raise ValueError(f"Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format")
            knowledge_base = KnowledgeBase.model_validate(content)

        return knowledge_base
    
    def __repr__(self):
        return f"KnowledgeBase(id='{self.id}', name='{self.name}', description='{self.description}')"

    def __str__(self):
        return self.__repr__()