import json
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from .types import KnowledgeBaseSpec, KnowledgeBaseKind, ConversationalSearchConfig
from pydantic import model_validator

class KnowledgeBase(KnowledgeBaseSpec):

    @staticmethod
    def from_spec(file: str) -> 'KnowledgeBase':
        with safe_open(file, 'r') as f:
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
        has_documents = bool(self.documents)
        has_index_config = bool(
            isinstance(self.conversational_search_tool, ConversationalSearchConfig)
            and self.conversational_search_tool.index_config
        )
        has_content_source = bool(self.content_source)

        if has_documents and has_index_config:
            raise ValueError("Must provide either \"documents\" or \"conversational_search_tool.index_config\", but not both")
        if not has_documents and not has_index_config and not has_content_source:
            raise ValueError("Must provide either \"documents\", \"conversational_search_tool.index_config\", or \"content_source\"")
        if has_content_source and not has_documents:
            raise ValueError("\"documents\" is required when \"content_source\" is specified")
        return self
    
    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind != KnowledgeBaseKind.KNOWLEDGE_BASE:
            raise ValueError(f"The specified kind '{self.kind}' cannot be used to create a knowledge base")
        return self