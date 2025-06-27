import json
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import KnowledgeBaseSpec, KnowledgeBaseKind
from pydantic import model_validator

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
    
    # Not a model validator since we only want to validate this on import
    def validate_documents_or_index_exists(self):
        if self.documents and self.conversational_search_tool and self.conversational_search_tool.index_config or \
            (not self.documents and (not self.conversational_search_tool or not self.conversational_search_tool.index_config)):
            raise ValueError("Must provide either \"documents\" or \"conversational_search_tool.index_config\", but not both")
        return self
    
    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind != KnowledgeBaseKind.KNOWLEDGE_BASE:
            raise ValueError(f"The specified kind '{self.kind}' cannot be used to create a knowledge base")
        return self