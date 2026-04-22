"""
Tests for ToolResult class

This test suite covers ToolResult functionality to ensure:
1. Content blocks are properly created and normalized
2. Widgets are correctly converted to _meta
3. Structured content is handled properly
4. Convenience functions work correctly
5. Output format matches wxO runtime expectations
"""

from ibm_watsonx_orchestrate.run import (
    ToolResult,
    TextContent,
    Annotations,
    Role,
)
from ibm_watsonx_orchestrate.run.widgets.forms import FormWidget, TextInput, Checkbox


class TestContentBlocks:
    """
    Test ContentBlock types
    
    Why: Ensures content blocks follow MCP standard
    Covers: TextContent structure
    """
    
    def test_text_content_structure(self):
        """Test TextContent creates correct structure"""
        content = TextContent(text="Hello, world!")
        
        assert content.type == "text"
        assert content.text == "Hello, world!"
    
    def test_text_content_with_annotations(self):
        """Test TextContent with annotations"""
        
        content = TextContent(
            text="Message",
            annotations=Annotations(audience=[Role.USER])
        )
        
        assert content.annotations is not None
        assert Role.USER in content.annotations.audience


class TestToolResultBasic:
    """
    Test basic ToolResult functionality
    
    Why: Ensures ToolResult handles simple cases correctly
    Covers: Content creation, string normalization, basic output
    """
    
    def test_tool_result_with_string_content(self):
        """Test ToolResult automatically converts strings to TextContent"""
        result = ToolResult(content=["Hello"])
        
        output = result.model_dump()
        
        assert len(output["content"]) == 1
        print("\n\n\ HERE",output)
        assert output["content"][0]["type"] == "text"
        assert output["content"][0]["text"] == "Hello"
    
    def test_tool_result_with_text_content(self):
        """Test ToolResult with explicit TextContent"""
        result = ToolResult(
            content=[TextContent(text="Hello")]
        )
        
        output = result.model_dump()
        
        assert output["content"][0]["type"] == "text"
        assert output["content"][0]["text"] == "Hello"
    
    def test_tool_result_with_multiple_content(self):
        """Test ToolResult with multiple content blocks"""
        result = ToolResult(
            content=[
                "First message",
                "Second message",
                TextContent(text="Third message")
            ]
        )
        
        output = result.model_dump()
        
        assert len(output["content"]) == 3
        assert all(c["type"] == "text" for c in output["content"])


class TestToolResultWithWidget:
    """
    Test ToolResult with form widgets
    
    Why: Ensures widgets are correctly converted to _meta structure
    Covers: Widget parameter, automatic conversion, meta structure
    """
    
    def test_tool_result_with_widget(self):
        """Test ToolResult automatically converts widget to meta"""
        form = FormWidget(
            title="Test Form",
            inputs=[TextInput(name="name", title="Name")]
        )
        
        result = ToolResult(
            content=["Fill the form"],
            widget=form
        )
        
        output = result.model_dump()
        
        assert "_meta" in output
        assert "com.ibm.orchestrate/widget" in output["_meta"]
        assert output["_meta"]["com.ibm.orchestrate/widget"]["response_type"] == "forms"
        assert output["_meta"]["com.ibm.orchestrate/widget"]["json_schema"]["title"] == "Test Form"
    
    def test_tool_result_widget_and_meta_combine(self):
        """Test widget and meta parameters combine correctly"""
        form = FormWidget(
            title="Test Form",
            inputs=[TextInput(name="name", title="Name")]
        )
        
        result = ToolResult(
            content=["Fill the form"],
            widget=form,
            meta={"custom_field": "custom_value", "priority": "high"}
        )
        
        output = result.model_dump()
        
        # Should have both widget and custom meta
        assert "com.ibm.orchestrate/widget" in output["_meta"]
        assert output["_meta"]["custom_field"] == "custom_value"
        assert output["_meta"]["priority"] == "high"
    
    def test_tool_result_without_widget(self):
        """Test ToolResult without widget doesn't create widget meta"""
        result = ToolResult(
            content=["No form"],
            meta={"custom": "value"}
        )
        
        output = result.model_dump()
        
        assert "com.ibm.orchestrate/widget" not in output.get("_meta", {})
        assert output["_meta"]["custom"] == "value"


class TestToolResultWithStructuredContent:
    """
    Test ToolResult with structured data
    
    Why: Ensures structured content is properly included in output
    Covers: Structured data parameter, output format
    """
    
    def test_tool_result_with_structured_content(self):
        """Test ToolResult with structured data"""
        result = ToolResult(
            content=["User data retrieved"],
            structuredContent={"user_id": 123, "name": "John Doe"}
        )
        
        output = result.model_dump()
        
        assert "structuredContent" in output
        assert output["structuredContent"]["user_id"] == 123
        assert output["structuredContent"]["name"] == "John Doe"
    
    def test_tool_result_without_structured_content(self):
        """Test ToolResult without structured content"""
        result = ToolResult(content=["Simple message"])
        
        output = result.model_dump()
        
        assert "structuredContent" not in output


class TestToolResultCombined:
    """
    Test ToolResult with all parameters
    
    Why: Ensures all parameters work together correctly
    Covers: Content + widget + structured data + meta
    """
    
    def test_tool_result_all_parameters(self):
        """Test ToolResult with all parameters combined"""
        form = FormWidget(
            title="Budget Form",
            inputs=[TextInput(name="amount", title="Amount")]
        )
        
        result = ToolResult(
            content=["Current budget: $50,000"],
            structuredContent={"current_budget": 50000, "currency": "USD"},
            widget=form,
            meta={"priority": "high", "department": "finance"}
        )
        
        output = result.model_dump()
        
        # Check all components are present
        
        assert output["structuredContent"]["current_budget"] == 50000
        assert "com.ibm.orchestrate/widget" in output["_meta"]
        assert output["_meta"]["priority"] == "high"
        assert output["_meta"]["department"] == "finance"

class TestToolResultOutputFormat:
    """
    Test ToolResult output format
    
    Why: Ensures output matches wxO runtime expectations
    Covers: Output structure, field names, format
    """
    
    def test_output_has_content(self):
        """Test output always has content field"""
        result = ToolResult(content=["Message"])
        output = result.model_dump()
        
        assert "content" in output
        assert isinstance(output["content"], list)
    
    def test_output_meta_field_name(self):
        """Test output uses _meta (with underscore) for metadata"""
        result = ToolResult(
            content=["Message"],
            meta={"key": "value"}
        )
        output = result.model_dump()
        
        # Output should use _meta (with underscore)
        assert "_meta" in output
        assert output["_meta"]["key"] == "value"
    
    def test_output_structured_content_field_name(self):
        """Test output uses structuredContent (camelCase)"""
        result = ToolResult(
            content=["Message"],
            structuredContent={"key": "value"}
        )
        output = result.model_dump()
        
        assert "structuredContent" in output
        assert output["structuredContent"]["key"] == "value"


class TestToolResultEdgeCases:
    """
    Test edge cases and error handling
    
    Why: Ensures robustness in unusual scenarios
    Covers: Empty content, None values, complex structures
    """
    
    def test_empty_content_list(self):
        """Test ToolResult with empty content list"""
        result = ToolResult(content=[])
        output = result.model_dump()
        
        assert output["content"] == []
    
    def test_none_meta(self):
        """Test ToolResult with None meta"""
        result = ToolResult(content=["Message"], meta=None)
        output = result.model_dump()
        
        # Should not include _meta if None or empty
        assert "_meta" not in output or output["_meta"] == {}
    
    def test_none_structured_content(self):
        """Test ToolResult with None structured content"""
        result = ToolResult(content=["Message"], structuredContent=None)
        output = result.model_dump()
        
        assert "structuredContent" not in output


class TestToolResultIntegration:
    """
    Test ToolResult integration with forms
    
    Why: Ensures ToolResult works correctly with real form widgets
    Covers: Real-world usage patterns, complete workflows
    """
    
    def test_registration_form_workflow(self):
        """Test complete registration form workflow"""
        form = FormWidget(
            title="User Registration",
            description="Create your account",
            submit_text="Register",
            cancel_text="Cancel",
            inputs=[
                TextInput(name="email", title="Email", required=True),
                TextInput(name="username", title="Username", required=True),
                Checkbox(name="agree_terms", title="I agree to terms", required=True)
            ]
        )
        
        result = ToolResult(
            content=["Welcome! Please complete your registration."],
            widget=form,
            meta={"flow_step": "registration", "session_id": "abc123"}
        )
        
        output = result.model_dump()
        
        # Verify complete structure
        assert output["content"][0]["text"] == "Welcome! Please complete your registration."
        assert output["_meta"]["com.ibm.orchestrate/widget"]["response_type"] == "forms"
        assert len(output["_meta"]["com.ibm.orchestrate/widget"]["json_schema"]["properties"]) == 3
        assert output["_meta"]["flow_step"] == "registration"
    
    def test_data_retrieval_workflow(self):
        """Test data retrieval with structured content"""
        result = ToolResult(
            content=["User profile retrieved successfully"],
            structuredContent={
                "user_id": 12345,
                "username": "john_doe",
                "email": "john@example.com",
                "created_at": "2025-01-15T10:30:00Z",
                "status": "active"
            },
            meta={"cache_hit": True, "response_time_ms": 45}
        )
        
        output = result.model_dump()
        
        assert output["structuredContent"]["user_id"] == 12345
        assert output["structuredContent"]["status"] == "active"
        assert output["_meta"]["cache_hit"] is True
    
    def test_multi_step_form_workflow(self):
        """Test multi-step form with progress tracking"""
        form = FormWidget(
            title="Registration - Step 2 of 3",
            submit_text="Next",
            inputs=[
                TextInput(name="address", title="Address", required=True),
                TextInput(name="city", title="City", required=True)
            ]
        )
        
        result = ToolResult(
            content=["Step 2: Please provide your address"],
            widget=form,
            structuredContent={"step": 2, "total_steps": 3, "completed_steps": [1]},
            meta={"flow_id": "reg_flow_001", "user_id": 123}
        )
        
        output = result.model_dump()
        
        assert output["structuredContent"]["step"] == 2
        assert output["structuredContent"]["total_steps"] == 3
        assert "com.ibm.orchestrate/widget" in output["_meta"]
        assert output["_meta"]["flow_id"] == "reg_flow_001"


class TestBackwardCompatibility:
    """
    Test backward compatibility
    
    Why: Ensures changes don't break existing code
    Covers: dict() method, field access
    """
    
    def test_dict_method_works(self):
        """Test dict() method for Pydantic v1 compatibility"""
        result = ToolResult(content=["Message"])
        
        # Both should work
        output1 = result.model_dump()
        output2 = result.dict()
        
        assert output1 == output2
    
    def test_field_access(self):
        """Test direct field access works"""
        form = FormWidget(
            title="Test",
            inputs=[TextInput(name="name", title="Name")]
        )
        
        result = ToolResult(
            content=["Message"],
            widget=form,
            meta={"key": "value"}
        )
        
        # Should be able to access fields directly
        assert len(result.content) == 1
        assert result.widget is not None
        assert result.meta["key"] == "value"
