"""
ToolResponse class for returning tool results with context updates.
This class can be serialized to JSON for cross-environment compatibility.
"""
import json
from typing import Any, Dict, Optional
from ibm_watsonx_orchestrate.run.tool_result import ToolResult


class ToolResponse:
  """
  Response wrapper for tool execution results with context updates.
  
  This class can be:
  - Serialized to JSON string for cross-environment compatibility
  - Deserialized from JSON string
  - Accessed like a dict for backward compatibility
  
  Example:
      >>> response = ToolResponse(content={"data": "value"}, context_updates={"key": "val"})
      >>> json_str = response.to_json()
      >>> restored = ToolResponse.from_json(json_str)
  """

  def __init__(self, content: Any, context_updates: Optional[Dict[str, Any]] = None,_meta:Optional[Dict[str,Any]]={}):
    """
    Initialize ToolResponse.
    
    Args:
        content: The tool execution result (can be a ToolResult instance or plain dict)
        context_updates: Optional dictionary of context updates
    """
    if isinstance(content, ToolResult):
      self.content = content.content
      self._meta = content.meta if content.meta else {}
      self.structuredContent = content.structuredContent
      self.context_updates = context_updates if context_updates is not None else {}
    else:
      self.content = content
      self.context_updates = context_updates if context_updates is not None else {}
      self._meta = _meta
      self.structuredContent = None

  def has_context_updates(self) -> bool:
    """Check if there are any context updates."""
    return bool(self.context_updates)

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert to dictionary matching the expected format.
    
    Returns:
        Dictionary with 'content' and optionally '_meta' and 'structuredContent'
    """
    # Serialize content - handle Pydantic models in lists
    serialized_content = self.content
    if isinstance(self.content, list):
        serialized_content = []
        for item in self.content:
            # Check if item is a Pydantic model (has model_dump method)
            if hasattr(item, 'model_dump'):
                serialized_content.append(item.model_dump(mode='python'))
            else:
                serialized_content.append(item)
    elif hasattr(self.content, 'model_dump'):
        serialized_content = self.content.model_dump(mode='python')
    
    # Build result matching show_laptop_request_form.py format
    result = {
        "content": serialized_content
    }
    
    # Add _meta if present and not empty
    if self._meta:
        result["_meta"] = self._meta
    
    # Only add structuredContent if it's not None
    if self.structuredContent is not None:
        result["structuredContent"] = self.structuredContent
    
    # Add context_updates only if present and not empty
    if self.context_updates:
        result["context_updates"] = self.context_updates
    
    return result

  def to_json(self) -> str:
    """
    Serialize to JSON string.
    
    Returns:
        JSON string representation
        
    Example:
        >>> response = ToolResponse(content={"data": "value"})
        >>> json_str = response.to_json()
        >>> # Can be sent over network, saved to file, etc.
    """
    return json.dumps(self.to_dict())

  @classmethod
  def from_json(cls, json_str: str) -> 'ToolResponse':
    """
    Deserialize from JSON string.
    
    Args:
        json_str: JSON string representation
        
    Returns:
        ToolResponse instance
        
    Example:
        >>> json_str = '{"content": {"data": "value"}, "context_updates": {"key": "val"}}'
        >>> response = ToolResponse.from_json(json_str)
    """
    data = json.loads(json_str)
    return cls(
        content=data.get("content"),
        context_updates=data.get("context_updates", {}),
        _meta=data.get("_meta",{})
    )

  def __repr__(self) -> str:
    """String representation."""
    return f"ToolResponse(content={self.content}, context_updates={self.context_updates}, _meta={self._meta})"

  def __getitem__(self, key: str) -> Any:
    """
    Allow dict-like access for backward compatibility.
    
    Example:
        >>> response = ToolResponse(content={"data": "value"})
        >>> response["content"]  # Returns {"data": "value"}
        >>> response["context_updates"]  # Returns {}
    """
    if key == "result":
        return self.content
    elif key == "context_updates":
        return self.context_updates
    elif key=="_meta":
        return self._meta
    else:
        raise KeyError(f"Invalid key: {key}. Use 'content' or 'context_updates'")