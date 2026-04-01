from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate_agentic_sdk.common.base_client import BaseAgenticClient


class MemoryEntry(BaseModel):
    """Represents a memory entry"""
    id: str = Field(..., description="Unique identifier for the memory entry")
    content: str = Field(..., description="Memory content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class MemoryClient(BaseAgenticClient):
    """
    Client to handle operations for the Memory service endpoint
    
    Example usage for future implementation:
        ```python
        from ibm_watsonx_orchestrate_agentic_sdk import AgenticSDK
        
        sdk = AgenticSDK(api_key="...", instance_url="...")
        
        # Store memory
        sdk.memory.store(content="User prefers dark mode")
        
        # Retrieve memories
        memories = sdk.memory.retrieve(query="user preferences")
        ```
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/memory"
    
    def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> MemoryEntry:
        """
        Store a memory entry
        
        Args:
            content: The content to store
            metadata: Optional metadata associated with the memory
        
        Returns:
            MemoryEntry containing the stored memory details
        """
        payload: Dict[str, Any] = {"content": content}
        if metadata is not None:
            payload["metadata"] = metadata
        
        endpoint = f"{self.base_endpoint}/store"
        response = self._post(endpoint, data=payload)
        return MemoryEntry.model_validate(response)
    
    def retrieve(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """
        Retrieve memory entries based on a query
        
        Args:
            query: Search query for retrieving relevant memories
            limit: Maximum number of memories to retrieve
        
        Returns:
            List of MemoryEntry objects matching the query
        """
        endpoint = f"{self.base_endpoint}/retrieve"
        params = {"query": query, "limit": limit}
        response = self._get(endpoint, params=params)
        return [MemoryEntry.model_validate(entry) for entry in response.get("memories", [])]

# Made with Bob
