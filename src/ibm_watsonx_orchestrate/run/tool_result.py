"""
Tool Result and Content Block types for structured tool responses.

Based on the MCP (Model Context Protocol) specification for ContentBlock and ToolCallResult.
These classes provide a unified way for Python tools to return structured responses with
content, widgets, and metadata.
"""

from pydantic import BaseModel, Field, model_validator, model_serializer
from typing import List, Dict, Any, Optional, Union, Literal
from enum import Enum


# ---------------------------------------------------------------------------
# Content Block Types (MCP Standard)
# ---------------------------------------------------------------------------

class Role(str, Enum):
    """Role for content annotations"""
    USER = "user"
    ASSISTANT = "assistant"


class Annotations(BaseModel):
    """Annotations for content blocks"""
    audience: Optional[List[Role]] = None


class ContentBlockType(str, Enum):
    """Types of content blocks, supports text"""
    TEXT = "text"


class ContentBlock(BaseModel):
    """Base class for content blocks following MCP standard"""
    type: ContentBlockType
    annotations: Optional[Annotations] = None


class TextContent(ContentBlock):
    """Text content block"""
    type: Literal[ContentBlockType.TEXT] = ContentBlockType.TEXT
    text: str
    annotations: Optional[Annotations] = None


# ---------------------------------------------------------------------------
# Tool Result
# ---------------------------------------------------------------------------

class ToolResult(BaseModel):
    """Structured tool result that provides granular control over returned content.
    
    Based on MCP ToolCallResult specification. This class allows tools to return:
    - Content blocks (text) visible to LLM and user
    - Structured data for programmatic use
    - Widgets for custom UI rendering
    - Metadata for additional context
    
    Example usage:
        ```python
        from ibm_watsonx_orchestrate.run.tool_result import ToolResult, TextContent
        from ibm_watsonx_orchestrate.run.forms.types import FormWidget, TextInput
        
        # Simple text response
        result = ToolResult(
            content=[TextContent(text="Operation completed successfully")]
        )
        
        # Response with a form widget
        form = FormWidget(
            title="User Registration",
            inputs=[TextInput(name="email", title="Email", required=True)]
        )
        result = ToolResult(
            content=[TextContent(text="Please fill out the registration form")],
            widget=form
        )
        
        # Response with structured data
        result = ToolResult(
            content=[TextContent(text="User data retrieved")],
            structuredContent={"user_id": 123, "name": "John Doe"}
        )
        ```
    
    The ToolResult is automatically converted to the ToolResponse format expected
    by the wxO runtime:
    - ToolResponse.content = ToolResult.content
    - ToolResponse.structuredContent = ToolResult.structuredContent
    - ToolResponse._meta.update(ToolResult.meta)
    """
    
    content: List[Union[ContentBlock, str]] = Field(
        description="Content blocks or strings to display to user/LLM"
    )
    structuredContent: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured data for programmatic use"
    )
    widget: Optional[Any] = Field(
        default=None,
        description="Widget to render (e.g., FormWidget)"
    )
    meta: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    @model_validator(mode="before")
    @classmethod
    def validate_content(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Convert string content to TextContent blocks"""
        content = values.get("content", [])
        normalized_content = []
        
        for item in content:
            if isinstance(item, str):
                # Convert plain strings to TextContent
                normalized_content.append(
                    TextContent(text=item)
                )
            elif isinstance(item, dict) and "type" not in item:
                # If it's a dict without type, assume it's text
                normalized_content.append(
                    TextContent(text=str(item))
                )
            else:
                # Already a ContentBlock or will be validated by Pydantic
                normalized_content.append(item)
        
        values["content"] = normalized_content
        return values
    
    @model_validator(mode="after")
    def parse_widget(self) -> "ToolResult":
        """Parse widget into meta if provided"""
        if not self.widget:
            return self
        
        # Initialize meta if not present
        if self.meta is None:
            self.meta = {}
        
        # Add widget to metadata
        # Check if widget has model_dump method (Pydantic models)
        # Use mode='python' to preserve Python types (True/False instead of true/false)
        if hasattr(self.widget, "model_dump"):
            self.meta["com.ibm.orchestrate/widget"] = self.widget.model_dump(mode='python')
        elif hasattr(self.widget, "dict"):
            # Fallback for Pydantic v1
            self.meta["com.ibm.orchestrate/widget"] = self.widget.dict()
        else:
            # Fallback to __dict__
            self.meta["com.ibm.orchestrate/widget"] = self.widget.__dict__
        
        return self
    
    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """Custom serializer to properly serialize content blocks"""
        # Serialize content blocks
        serialized_content = []
        for item in self.content:
            if hasattr(item, 'model_dump'):
                serialized_content.append(item.model_dump())
            else:
                serialized_content.append(item)
        
        result = {
            "content": serialized_content,
        }
        
        # Only include structuredContent if it's not None
        if self.structuredContent is not None:
            result["structuredContent"] = self.structuredContent
        
        # Only include widget if it's not None
        if self.widget is not None:
            result["widget"] = self.widget
        
        # Use _meta (with underscore) for output, but only if meta has content
        if self.meta:
            result["_meta"] = self.meta
        
        return result