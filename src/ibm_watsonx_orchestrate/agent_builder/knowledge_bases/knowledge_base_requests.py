import json
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from .types import KnowledgeBaseSpec


class KnowledgeBaseCreateRequest(KnowledgeBaseSpec):

    @staticmethod
    def from_spec(file: str) -> 'KnowledgeBaseSpec':
        with safe_open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                content = yaml_safe_load(f)
            elif file.endswith('.json'):
                content = json.load(f)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')
            
            if not content.get("spec_version"):
                raise ValueError(f"Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format")
            
            knowledge_base = KnowledgeBaseSpec.model_validate(content)

        return knowledge_base
