import json
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import CreateKnowledgeBase, PatchKnowledgeBase, KnowledgeBaseKind


class KnowledgeBaseCreateRequest(CreateKnowledgeBase):

    @staticmethod
    def from_spec(file: str) -> 'CreateKnowledgeBase':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                content = yaml_safe_load(f)
            elif file.endswith('.json'):
                content = json.load(f)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')
            
            if (content.get('documents') and content.get("conversational_search_tool", {}).get("index_config")) or \
                  (not content.get('documents') and not content.get("conversational_search_tool", {}).get("index_config")):
                raise ValueError("Must provide either \"documents\" or \"conversational_search_tool.index_config\", but not both")
            
            if not content.get("spec_version"):
                raise ValueError(f"Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format")
            
            if not content.get("kind"):
                raise ValueError(f"Field 'kind' not provided. Should be 'knowledge_base'")

            if content.get("kind") != KnowledgeBaseKind.KNOWLEDGE_BASE:
                raise ValueError(f"Field 'kind' should be 'knowledge_base', but is set to '{content.get('kind')}'")
            
            knowledge_base = CreateKnowledgeBase.model_validate(content)

        return knowledge_base
    

class KnowledgeBaseUpdateRequest(PatchKnowledgeBase):

    @staticmethod
    def from_spec(file: str) -> 'PatchKnowledgeBase':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                content = yaml_safe_load(f)
            elif file.endswith('.json'):
                content = json.load(f)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')
            
            if not content.get("spec_version"):
                raise ValueError(f"Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format")
            
            if not content.get("kind"):
                raise ValueError(f"Field 'kind' not provided. Should be 'knowledge_base'")

            if content.get("kind") != KnowledgeBaseKind.KNOWLEDGE_BASE:
                raise ValueError(f"Field 'kind' should be 'knowledge_base', but is set to '{content.get('kind')}'")
            
            patch = PatchKnowledgeBase.model_validate(content)

        return patch