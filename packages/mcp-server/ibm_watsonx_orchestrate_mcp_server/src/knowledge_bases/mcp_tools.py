from typing import List, Literal, Optional
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import KnowledgeBaseController
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call
from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path

def list_knowledge_bases(verbose:bool=False)-> List[dict]:
    """
    Lists the avalible knowledge bases available on the watsonx Orchestrate platform.
    """
    kbc: KnowledgeBaseController = KnowledgeBaseController()
    format: Literal[ListFormats.JSON] | None = ListFormats.JSON if not verbose else None
    knowledge_bases: List[dict] = silent_call(fn=kbc.list_knowledge_bases, verbose=verbose, format=format)
    return knowledge_bases

def import_knowledge_bases(file_path: str, app_id: Optional[str] = None) -> str:
    """
    Import a knowledge base from a spec file into the watsonx Orchestrate platform.

    Args:
        file_path (str): The path to the knowledge base spec file.
        app_id (str, optional): The app id of a connection in the watsonx Orchestrate platform. Used to authenticate to external knowledge base systems like Milvus or Elastic Search. Defaults to None.

    Returns:
        str: A success message indicating the knowledge base was imported successfully.
    """
    working_directory_file_path: str = get_working_directory_path(file_path)

    kbc: KnowledgeBaseController = KnowledgeBaseController()
    silent_call(fn=kbc.import_knowledge_base, file=working_directory_file_path, app_id=app_id)
    return "Knowledge base imported successfully."

def remove_knowledge_base(id:  Optional[str] = None, name: Optional[str] = None) -> str:
    """
    Remove a knowledge base from the watsonx Orchestrate platform.
    Requires either a name or id to identify the knowledge base to remove. If both are provided, the id will be used.

    Args:
        id (str, optional): The id of the knowledge base to remove. Defaults to None.
        name (str, optional): The name of the knowledge base to remove. Defaults to None.

        Returns:
    """
    kbc: KnowledgeBaseController = KnowledgeBaseController()
    silent_call(fn=kbc.remove_knowledge_base, id=id, name=name)
    identifier: str | None = id if id else name
    return f"Knowledge base '{identifier}' removed successfully."

def check_knowledge_base_status(id:  Optional[str] = None, name: Optional[str] = None) -> dict:
    """
    Check the status of a knowledge base in the watsonx Orchestrate platform.
    This will show if the knowledge base has been indexed and if ready to be used.
    Requires either a name or id to identify the knowledge base to check. If both are provided, the id will be used.

    Args:
        id (str, optional): The id of the knowledge base to check. Defaults to None.
        name (str, optional): The name of the knowledge base to check. Defaults to None.
    
    Returns:
        str: The status of the knowledge base.
    """
    kbc: KnowledgeBaseController = KnowledgeBaseController()
    knowledge_base: dict = silent_call(fn=kbc.knowledge_base_status, id=id, name=name, format=ListFormats.JSON)
    return knowledge_base

__tools__ = [list_knowledge_bases, import_knowledge_bases, remove_knowledge_base, check_knowledge_base_status]