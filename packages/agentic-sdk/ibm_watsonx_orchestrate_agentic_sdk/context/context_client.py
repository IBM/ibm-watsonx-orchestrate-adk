from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate_agentic_sdk.common.base_client import BaseAgenticClient


class OpenAIMessage(BaseModel):
    """Represents a single message in OpenAI format."""
    role: str = Field(..., description="Message role: user, assistant, system, or tool")
    content: Optional[str] = Field(None, description="Message content")
    name: Optional[str] = Field(None, description="Optional name field")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls made by assistant")
    tool_call_id: Optional[str] = Field(None, description="ID of the tool call this message is responding to")
    reasoning: Optional[str] = Field(None, description="Optional reasoning field")


class SummarizationRequest(BaseModel):
    """Request model for message summarization."""
    messages: List[OpenAIMessage] = Field(..., min_length=2, description="List of messages to summarize")
    model: Optional[str] = Field(None, description="Optional model name for summarization")


class SummarizationResponse(BaseModel):
    """Response model for message summarization."""
    summary: str = Field(..., description="The generated summary")
    original_message_count: int = Field(..., ge=2, description="Number of messages summarized")
    model_used: str = Field(..., description="Model used for summarization")


class ContextClient(BaseAgenticClient):
    """
    Client to handle operations for the Context service endpoint
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/context"
    
    def summarize(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> SummarizationResponse:
        """
        Summarize a conversation history using the context service
        
        Args:
            messages: List of message dictionaries in OpenAI format
            model: Optional model name to use for summarization
        
        Returns:
            SummarizationResponse containing summary, message count, and model used
        
        Raises:
            ValueError: If fewer than 2 messages provided
            ClientAPIException: If the API request fails
        """
        if len(messages) < 2:
            raise ValueError("At least 2 messages are required for summarization")
        
        payload: Dict[str, Any] = {"messages": messages}
        if model is not None:
            payload["model"] = model
        
        endpoint = f"{self.base_endpoint}/summarize"
        response = self._post(endpoint, data=payload)
        return SummarizationResponse.model_validate(response)
