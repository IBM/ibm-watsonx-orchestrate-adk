import os
        
from pathlib import Path
from typing import Optional

from ibm_watsonx_orchestrate.cli.commands.chat.chat_controller import (
    create_run_client,
    create_threads_client,
    execute_agent_interaction_with_fallback_async,
    detect_file_upload_request,
    extract_downloadable_files
)
from ibm_watsonx_orchestrate_mcp_server.src.agents.mcp_tools import __get_existing_agent
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentKind
from ibm_watsonx_orchestrate.client.chat.run_client import RunClient
from ibm_watsonx_orchestrate.client.threads.threads_client import ThreadsClient
from ibm_watsonx_orchestrate_mcp_server.src.chat.types import (
    ChatResponse,
    ChatRequest,
    FileUploadRequest,
    DownloadableFile
)
from ibm_watsonx_orchestrate.cli.commands.chat.types import AgentInteractionResult
from ibm_watsonx_orchestrate_mcp_server.src.agents.types import AnyAgent
from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path
from ibm_watsonx_orchestrate_mcp_server.utils.common import async_silent_call

def __get_agent_by_name(name: str) -> Optional[AnyAgent]:
    """
    Get an agent by name, searching across all agent kinds (native, external, assistant).
    Returns the first agent found with the given name.
    """
    # Try each kind in order
    for kind in [AgentKind.NATIVE, AgentKind.EXTERNAL, AgentKind.ASSISTANT]:
        agent = __get_existing_agent(name, kind)
        if agent:
            return agent
    return None


def __handle_file_upload(
    chat_request: ChatRequest,
    agent_id: str,
    run_client: RunClient,
    threads_client: ThreadsClient
) -> ChatResponse:
    """
    Handle file upload to agent and return response.
    
    Args:
        chat_request: The chat request containing file path
        agent_id: The agent ID to send the file to
        run_client: RunClient instance
        threads_client: ThreadsClient instance
        
    Returns:
        ChatResponse with the agent's response after processing the file
    """
    try:
        # Validate file path is within working directory
        # This will raise an exception if path is outside working directory
        get_working_directory_path(chat_request.file_path)
        
        # Get the absolute path for file operations
        absolute_path = str(Path(chat_request.file_path).resolve())
        
        # Check if file exists
        if not os.path.exists(absolute_path):
            return ChatResponse(
                error=f"File not found: {absolute_path}",
                response=None,
                thread_id=chat_request.thread_id,
                reasoning=None,
                thinking_trace=[]
            )
        
        # Upload file to S3
        file_urls = run_client.upload_file_to_s3(absolute_path, chat_request.message)
        
        # Create run with file attachment
        run_response = run_client.create_run_with_files(
            message=chat_request.message,
            file_urls=file_urls,
            agent_id=agent_id,
            thread_id=chat_request.thread_id
        )
        
        thread_id = run_response["thread_id"]
        run_id = run_response["run_id"]
        
        # Wait for run completion
        run_status = run_client.wait_for_run_completion(run_id)
        
        if run_status.get("status") == "failed":
            error_msg = run_status.get("error", "Unknown error")
            return ChatResponse(
                error=f"Agent interaction failed: {error_msg}",
                response=None,
                thread_id=thread_id,
                reasoning=None,
                thinking_trace=[]
            )
        
        # Get the response messages
        thread_messages_response = threads_client.get_thread_messages(thread_id)
        
        if isinstance(thread_messages_response, list):
            messages = thread_messages_response
        elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
            messages = thread_messages_response["data"]
        else:
            messages = []
        
        # Find the most recent assistant message
        final_message = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                final_message = msg
                break
        
        if not final_message:
            return ChatResponse(
                error="No response received from agent after file upload.",
                response=None,
                thread_id=thread_id,
                reasoning=None,
                thinking_trace=[]
            )
        
        # Extract content from the message
        content = final_message.get("content", "No response")
        
        # Handle structured content (list of response objects)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("response_type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif "text" in item:
                        text_parts.append(item["text"])
            content = "\n".join(text_parts) if text_parts else str(content)
        
        # Extract reasoning trace if requested
        reasoning_trace = None
        if chat_request.include_reasoning:
            steps = final_message.get("step_history", [])
            if steps:
                reasoning_trace = {"steps": steps}
        
        # Check for downloadable files
        downloadable_files = __extract_downloadable_files_from_response(thread_messages_response)
        
        return ChatResponse(
            response=content,
            thread_id=thread_id,
            reasoning=reasoning_trace,
            thinking_trace=[],
            error=None,
            file_upload_request=None,
            file_upload_required=False,
            downloadable_files=downloadable_files
        )
        
    except Exception as e:
        return ChatResponse(
            error=f"Error uploading file: {str(e)}",
            response=None,
            thread_id=chat_request.thread_id,
            reasoning=None,
            thinking_trace=[]
        )


def __extract_downloadable_files_from_response(thread_messages_response) -> list[DownloadableFile]:
    """
    Extract downloadable files from thread messages response.
    
    Args:
        thread_messages_response: Response from threads_client.get_thread_messages()
        
    Returns:
        List of DownloadableFile objects
    """
    downloadable_files_list = extract_downloadable_files(thread_messages_response)
    return [
        DownloadableFile(
            file_name=f.get("fileName", "unknown"),
            url=f.get("url", ""),
            file_id=f.get("id")
        )
        for f in downloadable_files_list
    ]


def __check_for_file_upload_request(
    threads_client: ThreadsClient,
    thread_id: Optional[str],
    final_message_content: Optional[str]
) -> Optional[FileUploadRequest]:
    """
    Check if the agent is requesting a file upload.
    
    Args:
        threads_client: ThreadsClient instance
        thread_id: The thread ID to check
        final_message_content: The final message content (if available)
        
    Returns:
        FileUploadRequest if agent is requesting file upload, None otherwise
    """
    if not thread_id:
        return None
        
    try:
        thread_messages_response = threads_client.get_thread_messages(thread_id)
        if isinstance(thread_messages_response, list):
            messages = thread_messages_response
        elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
            messages = thread_messages_response["data"]
        else:
            messages = []
        
        # Find the most recent assistant message
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                content = msg.get("content", [])
                upload_request = detect_file_upload_request(content)
                if upload_request:
                    return FileUploadRequest(
                        text=upload_request["text"],
                        supported_formats=upload_request["supported_formats"],
                        size_limit=upload_request["size_limit"]
                    )
                break
    except Exception:
        # If we can't get thread messages, just return None
        pass
    
    return None


async def chat_with_agent(
    chat_request: ChatRequest
) -> ChatResponse:
    """
    Send a message to a watsonx Orchestrate agent and receive a response.
    
    """
    # Get agent by name - search across all kinds (native, external, assistant)
    agent = __get_agent_by_name(chat_request.agent_name)
    
    if not agent:
        return ChatResponse(
            error=f"Agent '{chat_request.agent_name}' not found. Please check the agent name and try again. Use the 'list_agents' tool to see available agents.",
            response=None,
            thread_id=None,
            reasoning=None,
            thinking_trace=[]
        )
    
    agent_id: str = agent.id
    
    # Create clients for API interaction
    run_client: RunClient = create_run_client()
    threads_client: ThreadsClient = create_threads_client()
    
    # Handle file upload if file_path is provided
    if chat_request.file_path:
        return __handle_file_upload(chat_request, agent_id, run_client, threads_client)
    
    try:
        result = await async_silent_call(
            fn=execute_agent_interaction_with_fallback_async,
            run_client=run_client,
            threads_client=threads_client,
            message=chat_request.message,
            agent_id=agent_id,
            include_reasoning=chat_request.include_reasoning,
            agent_name=chat_request.agent_name,
            thread_id=chat_request.thread_id,
            capture_logs=False,
            return_agent_interaction_result=True
        )
        
        # When return_agent_interaction_result=True, result is an AgentInteractionResult
        # When return_agent_interaction_result=False, result is a thread_id (str)
        if isinstance(result, AgentInteractionResult):
            # We have an AgentInteractionResult - use it directly
            interaction_result: AgentInteractionResult = result
            
            # Check for file upload request and downloadable files
            file_upload_req = __check_for_file_upload_request(
                threads_client,
                interaction_result.thread_id,
                interaction_result.final_message
            )
            
            downloadable_files = []
            if interaction_result.thread_id:
                try:
                    thread_messages_response = threads_client.get_thread_messages(interaction_result.thread_id)
                    downloadable_files = __extract_downloadable_files_from_response(thread_messages_response)
                except Exception:
                    # If we can't get thread messages, just continue without file info
                    pass
            
            if interaction_result.status == "error":
                return ChatResponse(
                    error=interaction_result.error,
                    response=interaction_result.final_message,
                    thread_id=interaction_result.thread_id,
                    reasoning=interaction_result.reasoning_trace,
                    thinking_trace=interaction_result.thinking_trace,
                    file_upload_request=file_upload_req,
                    file_upload_required=file_upload_req is not None,
                    downloadable_files=downloadable_files
                )
            else:
                return ChatResponse(
                    response=interaction_result.final_message,
                    thread_id=interaction_result.thread_id,
                    reasoning=interaction_result.reasoning_trace,
                    thinking_trace=interaction_result.thinking_trace,
                    error=None,
                    file_upload_request=file_upload_req,
                    file_upload_required=file_upload_req is not None,
                    downloadable_files=downloadable_files
                )
        
        # Fallback: result is a thread_id string (backward compatibility)
        # This shouldn't happen when return_agent_interaction_result=True, but handle it just in case
        returned_thread_id = result
        
        if returned_thread_id is None:
            return ChatResponse(
                error="Agent interaction failed or was interrupted. This may be due to a widget requirement, flow error, or unexpected termination.",
                response=None,
                thread_id=chat_request.thread_id,
                reasoning=None,
                thinking_trace=[]
            )
        
        # Get the final messages to extract the response
        thread_messages_response = threads_client.get_thread_messages(returned_thread_id)
        
        if isinstance(thread_messages_response, list):
            messages = thread_messages_response
        elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
            messages = thread_messages_response["data"]
        else:
            messages = []
        
        # Find the most recent assistant message
        final_message = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                final_message = msg
                break
        
        if not final_message:
            return ChatResponse(
                error="No response received from agent. The agent may have failed to generate a response.",
                response=None,
                thread_id=returned_thread_id,
                reasoning=None,
                thinking_trace=[]
            )
        
        # Extract content from the message
        content = final_message.get("content", "No response")
        
        # Handle structured content (list of response objects)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("response_type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif "text" in item:
                        text_parts.append(item["text"])
            content = "\n".join(text_parts) if text_parts else str(content)
        
        # Extract reasoning trace if requested
        reasoning_trace = None
        if chat_request.include_reasoning:
            steps = final_message.get("step_history", [])
            if steps:
                reasoning_trace = {"steps": steps}
        
        # Check for file upload request
        file_upload_req = __check_for_file_upload_request(
            threads_client,
            returned_thread_id,
            content
        )
        
        # Check for downloadable files
        downloadable_files = __extract_downloadable_files_from_response(thread_messages_response)
        
        return ChatResponse(
            response=content,
            thread_id=returned_thread_id,
            reasoning=reasoning_trace,
            thinking_trace=[],
            error=None,
            file_upload_request=file_upload_req,
            file_upload_required=file_upload_req is not None,
            downloadable_files=downloadable_files
        )
        
    except Exception as e:
        return ChatResponse(
            error=f"Unexpected error during agent interaction: {str(e)}",
            response=None,
            thread_id=chat_request.thread_id,
            reasoning=None,
            thinking_trace=[]
        )


__tools__ = [chat_with_agent]

