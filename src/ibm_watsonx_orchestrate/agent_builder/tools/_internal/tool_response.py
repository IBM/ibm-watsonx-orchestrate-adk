"""
ToolResponse class for returning tool results with context updates.
This class can be serialized to JSON for cross-environment compatibility.
"""
import json
from typing import Any, Dict, Optional


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

  def __init__(self, content: Any, context_updates: Optional[Dict[str, Any]] = None):
    """
    Initialize ToolResponse.
    
    Args:
        content: The tool execution result
        context_updates: Optional dictionary of context updates
    """
    self.content = content
    self.context_updates = context_updates if context_updates is not None else {}

  def has_context_updates(self) -> bool:
    """Check if there are any context updates."""
    return bool(self.context_updates)

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert to dictionary.
    
    Returns:
        Dictionary with 'content' and 'context_updates' keys
    """
    return {
        "content": self.content,
        "context_updates": self.context_updates
    }

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
        context_updates=data.get("context_updates", {})
    )

  def __repr__(self) -> str:
    """String representation."""
    return f"ToolResponse(content={self.content}, context_updates={self.context_updates})"

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
    else:
        raise KeyError(f"Invalid key: {key}. Use 'content' or 'context_updates'")