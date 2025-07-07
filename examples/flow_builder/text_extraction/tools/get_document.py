from typing import Literal, Optional
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


class Document(BaseModel):
    document_ref: str = Field(description="Either an ID or a URL identifying the document to be used.",
                             title="Document Reference", default=None, json_schema_extra={"format": "document_id"})
    language: Optional[Literal['en', 'en_hw', 'fr']] = Field(description="Language of the document, when not specified assumed to be `en`", title="Document language", default="en")
    
@tool(
    permission=ToolPermission.READ_ONLY
)
def get_document(document: bytes) -> Document:
    """
    Returns a Document object

    Args:
        document (str): A str object

    Returns:
        Document: A Document object
    """
    return Document(document_ref=document['path'])