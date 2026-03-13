from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class FileUploadRequest(BaseModel):
    """Information about a file upload request from the agent"""
    text: str = Field(
        description="The message from the agent requesting the file"
    )
    supported_formats: str = Field(
        description="Comma-separated list of supported file formats (e.g., 'PDF,DOCX,CSV')"
    )
    size_limit: str = Field(
        description="Maximum file size allowed (e.g., '10MB')"
    )


class DownloadableFile(BaseModel):
    """Information about a file available for download"""
    file_name: str = Field(
        description="Name of the file"
    )
    url: str = Field(
        description="Download URL for the file"
    )
    file_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the file"
    )


class ChatResponse(BaseModel):
    """Response from chatting with an agent"""
    response: Optional[str] = Field(
        default=None,
        description="The text response from the agent. Contains the agent's reply to your message."
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="The conversation thread ID. Use this to continue the conversation in subsequent messages."
    )
    reasoning: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The agent's reasoning trace showing the steps it took to generate the response. Only included if include_reasoning=True."
    )
    thinking_trace: List[str] = Field(
        default_factory=list,
        description="List of intermediate thinking/progress messages captured during agent execution"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the chat failed. None if successful."
    )
    file_upload_required: bool = Field(
        default=False,
        description=(
            "Indicates whether the agent should ask the user for a file path to upload a file. If this is true, the agent requires a file upload to continue: Ask the user to provide the file path and Make a follow-up chat_with_agent request with the file_path parameter for the same chat using the same thread-id. \n"
        )
    )
    file_upload_request: Optional[FileUploadRequest] = Field(
        default=None,
        description="Contains the file upload requirements (text, supported_formats, size_limit) when the agent needs a file. Check file_upload_required for workflow instructions."
    )
    downloadable_files: List[DownloadableFile] = Field(
        default_factory=list,
        description="List of files available for download from the agent's response"
    )


class ChatRequest(BaseModel):
    """Request to chat with an agent"""
    
    agent_name: str = Field(
        description="The name of the watsonx Orchestrate agent to interact with. The agent name is case-sensitive. Use the 'list_agents' MCP tool to discover available agents."
    )
    message: str = Field(
        default="",
        description="The message or question to send to the agent. Can be an empty string when uploading a file."
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="The conversation thread ID. Use this to continue the conversation in subsequent messages."
    )
    include_reasoning: Optional[bool] = Field(
        default=None,
        description="Whether to include the agent's reasoning trace in the response. When set to True, the response will contain detailed information."
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Path to a file to upload with the message. The file must be within the working directory configured for the MCP server."
    )
