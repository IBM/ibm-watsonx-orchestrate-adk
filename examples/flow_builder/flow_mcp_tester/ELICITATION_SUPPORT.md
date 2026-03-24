# FlowMCPClient Elicitation Support

## Overview

The `FlowMCPClient` now supports automatic handling of elicitation requests from flows via a callback mechanism. When a flow requires user input (e.g., form submission, URL navigation), the MCP server sends an elicitation request that can be handled by your custom callback function.

## What is Elicitation?

Elicitation is the MCP protocol's mechanism for requesting user interaction during flow execution. Common use cases include:

- **Form Input**: Flow needs user to fill out a form
- **URL Navigation**: Flow needs user to visit a URL (e.g., OAuth, payment gateway)
- **Confirmation**: Flow needs user approval to proceed
- **File Upload**: Flow needs user to provide a file

## How It Works

1. **Client Initialization**: You provide an `elicitation_callback` function when creating the `FlowMCPClient`
2. **Flow Execution**: When you run a flow that requires user input, it reaches an elicitation point
3. **Callback Invocation**: The MCP SDK automatically invokes your callback with the elicitation request
4. **Response Handling**: Your callback returns a response (accept/decline/cancel with optional data)
5. **Flow Continuation**: The flow resumes with your response

## Usage

### Basic Example

```python
from ibm_watsonx_orchestrate.client.tools.flow_mcp_client import FlowMCPClient
from mcp import types
import json

async def handle_elicitation(
    context,
    params: types.ElicitRequestParams,
) -> types.ElicitResult | types.ErrorData:
    """Handle elicitation requests from flows."""
    
    if params.mode == "form":
        # Collect form data from user
        form_data = {"field1": "value1", "field2": "value2"}
        
        return types.ElicitResult(
            action="accept",
            content={
                "form_data": json.dumps(form_data),  # Must be JSON string
                "response_type": "form_operation",
                "form_operation": "submit"
            }
        )
    
    elif params.mode == "url":
        # Handle URL navigation
        url = getattr(params, "url", None)
        print(f"Please visit: {url}")
        
        # Wait for user confirmation
        response = input("Completed? (y/n): ")
        if response.lower() == 'y':
            return types.ElicitResult(action="accept")
        else:
            return types.ElicitResult(action="decline")
    
    else:
        return types.ErrorData(
            code=types.INVALID_REQUEST,
            message=f"Unsupported mode: {params.mode}"
        )

# Create client with callback
async with FlowMCPClient(
    base_url="https://api.example.com",
    api_key="your-key",
    elicitation_callback=handle_elicitation
) as client:
    # Run flow - elicitations handled automatically
    result = await client.run_flow("my_flow", {"input": "data"})
```

### Callback Signature

```python
async def elicitation_callback(
    context,  # Request context from MCP
    params: types.ElicitRequestParams,
) -> types.ElicitResult | types.ErrorData:
    """
    Args:
        context: Request context from MCP (contains session info)
        params: Elicitation parameters with:
            - mode: str - The elicitation mode ("form", "url", etc.)
            - message: str - Description of what is requested
            - elicitationId: str - Unique ID for this elicitation
            - requestSchema or schema: dict - Form schema (if applicable)
            - Additional mode-specific fields
    
    Returns:
        types.ElicitResult: Success response with action and optional content
        types.ErrorData: Error response if request cannot be handled
    
    Note:
        The 'content' dict in ElicitResult must have simple values only:
        str, int, float, bool, list[str], or None. Use json.dumps() for dicts.
    """
    pass
```

### Response Types

#### Accept with Data
```python
return types.ElicitResult(
    action="accept",
    content={
        "form_data": json.dumps({"field": "value"}),  # JSON string, not dict
        "response_type": "form_operation",
        "form_operation": "submit"
    }
)
```

#### Accept without Data
```python
return types.ElicitResult(action="accept")
```

#### Decline
```python
return types.ElicitResult(action="decline")
```

#### Cancel
```python
return types.ElicitResult(action="cancel")
```

#### Error
```python
return types.ErrorData(
    code=types.INVALID_REQUEST,
    message="Cannot handle this request"
)
```

## Elicitation Modes

### Form Mode (`mode="form"`)

Used when a flow needs form input from the user.

**Parameters:**
- `message`: Description of the form
- Additional form schema information

**Response:**
```python
types.ElicitResult(
    action="accept",
    content={
        "form_data": json.dumps({
            "field1": "value1",
            "field2": "value2"
        }),
        "response_type": "form_operation",
        "form_operation": "submit"  # or "cancel"
    }
)
```

### URL Mode (`mode="url"`)

Used when a flow needs the user to visit a URL (e.g., OAuth, payment).

**Parameters:**
- `message`: Description of why URL visit is needed
- `url`: The URL to visit

**Response:**
```python
# After user completes action at URL
types.ElicitResult(action="accept")

# If user declines
types.ElicitResult(action="decline")
```

## Integration with instantiate_client

To use `FlowMCPClient` with elicitation support and credentials from your active environment:

```python
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.tools.flow_mcp_client import FlowMCPClient

# Create client with authentication from active environment
client = instantiate_client(FlowMCPClient)

# Set elicitation callback before connecting
client.set_elicitation_callback(handle_elicitation)

async with client:
    result = await client.run_flow("my_flow", {"input": "data"})
```

**Important Notes:**

1. **MCP SDK Required**: The MCP SDK must be installed (`pip install ibm-watsonx-orchestrate[mcp]`). If not installed, `instantiate_client(FlowMCPClient)` will raise an `ImportError`.

2. **Set Callback Before Connecting**: Call `set_elicitation_callback()` before entering the async context manager. If you set it after the session is established, you'll need to reconnect for the change to take effect.

3. **Alternative Approach**: You can also pass `elicitation_callback` during initialization if creating the client manually:
   ```python
   client = FlowMCPClient(
       base_url="https://your-server.com",
       api_key="your-api-key",
       elicitation_callback=handle_elicitation
   )
   ```

## Offline Elicitation Handling

If your client disconnects during an elicitation, you can handle it offline:

1. **Reconnect** to the MCP server
2. **Replay** pending elicitations:
   ```python
   result = await client.replay_flow_pending_elicitation(instance_id)
   ```
3. **Submit** response manually:
   ```python
   await client.submit_flow_elicitation(
       instance_id=instance_id,
       elicitation_id=elicitation_id,
       response={
           "action": "accept",
           "content": {...}
       }
   )
   ```

## Best Practices

1. **Error Handling**: Always handle errors gracefully in your callback
2. **Timeout**: Consider implementing timeouts for user input
3. **Validation**: Validate form data before submitting
4. **Security**: For URL mode, validate URLs before opening them
5. **Logging**: Log elicitation requests for debugging
6. **User Experience**: Provide clear messages to users about what's needed

## Example: Interactive CLI Handler

```python
async def interactive_cli_handler(
    context,
    params: types.ElicitRequestParams,
) -> types.ElicitResult | types.ErrorData:
    """Interactive CLI handler for elicitations."""
    
    print("\n" + "="*60)
    print("USER INPUT REQUIRED")
    print("="*60)
    print(f"Type: {params.mode}")
    print(f"Message: {params.message}")
    print()
    
    if params.mode == "form":
        # Display form and collect input
        form_data = {}
        # ... collect form fields interactively ...
        
        return types.ElicitResult(
            action="accept",
            content={
                "form_data": json.dumps(form_data),  # Convert to JSON string
                "response_type": "form_operation",
                "form_operation": "submit"
            }
        )
    
    elif params.mode == "url":
        url = getattr(params, "url", None)
        print(f"Please visit: {url}")
        
        # Optionally open browser
        import webbrowser
        webbrowser.open(url)
        
        input("Press Enter when completed...")
        return types.ElicitResult(action="accept")
    
    else:
        print(f"Unsupported elicitation mode: {params.mode}")
        return types.ErrorData(
            code=types.INVALID_REQUEST,
            message=f"Unsupported mode: {params.mode}"
        )
```

## Important Notes

### Content Structure
The `content` parameter in `ElicitResult` must be a flat dictionary with simple values:
- **Allowed types**: `str`, `int`, `float`, `bool`, `list[str]`, `None`
- **NOT allowed**: Nested dicts, complex objects

**Correct:**
```python
content={"form_data": json.dumps({...}), "response_type": "form_operation"}
```

**Incorrect:**
```python
content={"form_data": {...}, "response_type": "form_operation"}  # Dict not allowed!
```

### Multiple Elicitations
Flows can have multiple elicitation points. Your callback will be invoked for each one:
1. First elicitation → callback invoked → respond → flow continues
2. Second elicitation → callback invoked → respond → flow continues
3. And so on...

### CLI Limitations
When using synchronous CLI prompts (like `input()` or `Prompt.ask()`):
- Elicitation output may be buffered if you're at another prompt
- Use terminal bell (`\a`) to alert users
- Consider waiting at result screen instead of navigating menus
- See `README.md` for detailed workarounds

## See Also

- `elicitation_example.py` - Complete working example
- `flow_mcp_tester.py` - Interactive MCP client tester with elicitation support
- `README.md` - Usage guide and limitations
- MCP SDK Documentation - For detailed protocol information