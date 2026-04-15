"""
Comprehensive flow to test masking functionality across different node types.

This flow demonstrates masking of sensitive data across:
- Input schema fields
- Private variables (with nested object)
- Script node outputs
- User flow fields
- Tool node inputs/outputs
- OpenAPI tool responses
- ForEach loop data
"""

from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.masking_utils import MaskingPolicy
from ibm_watsonx_orchestrate.flow_builder.types import ForeachPolicy, UserFieldKind
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap, Assignment

# Commented out Python tool imports - tools can be uncommented when import issues are resolved
from .process_user_data import process_user_data
from .validate_credentials import validateCredentials

class UserInput(BaseModel):
    """Input schema with one sensitive field to be masked."""
    username: str = Field(description="User's username")
    ssn: str = Field(description="Social Security Number (sensitive)")

class Credentials(BaseModel):
    """Nested object for private credentials."""
    auth_token: str = Field(description="Authentication token")

class PrivateData(BaseModel):
    """Private schema with nested sensitive data."""
    user_id: str = Field(description="Internal user ID")
    credentials: Credentials = Field(description="User credentials")

class ProcessedUser(BaseModel):
    """Output schema with masked field."""
    user_id: str = Field(description="Generated user ID")
    username: str = Field(description="Username")
    masked_ssn: str = Field(description="Masked SSN for display")
    processing_notes: List[str] = Field(description="Processing notes")

class EmailRecord(BaseModel):
    """Schema for forEach loop items."""
    recipient: str = Field(description="Email recipient")
    api_token: str = Field(description="API token for sending (sensitive)")

@flow(
    name="masking_test_flow",
    display_name="Comprehensive Masking Test Flow",
    description="Tests masking functionality across all node types",
    input_schema=UserInput,
    output_schema=ProcessedUser,
    private_schema=PrivateData
)
def build_masking_test_flow(aflow: Flow) -> Flow:
    """
    Build a comprehensive flow to test masking across different node types.
    
    This flow includes:
    1. Input masking (SSN)
    2. Private variable masking (nested credentials)
    3. Script node with masked outputs
    4. User flow with masked field
    5. Python tool with masked parameters
    6. OpenAPI tool with masked responses
    """
    
    # ============================================================
    # SCRIPT NODE
    # ============================================================
    
    # Define output schema for script with masking extensions
    class ScriptOutput(BaseModel):
        masked_ssn: str = Field(description="Masked SSN for display")
    
    # Single script node to process data
    process_data_script = aflow.script(
        name="process_data",
        display_name="Process User Data",
        output_schema=ScriptOutput,
        script="""

# Generate user ID
flow.private.user_id = f"USER-{hash(flow.input.username) % 10000}"

# Generate auth token (sensitive)
token_input = f"{flow.input.username}:{flow.input.ssn}"
flow.private.credentials.auth_token = '123456789000'

# Create masked SSN for output
self.output.masked_ssn = flow.input.ssn
"""
    )
    
    # ============================================================
    # PYTHON TOOL NODES 
    # ============================================================
    
    # Tool node with masked input/output
    process_tool_node = aflow.tool(process_user_data)
    process_tool_node.map_input(input_variable="username", expression="flow.input.username")
    process_tool_node.map_input(input_variable="ssn", expression="flow.input.ssn")
    
    # Python tool for credential validation
    validate_creds_node = aflow.tool(validateCredentials)
    
    # ============================================================
    # USER FLOW NODE
    # ============================================================
    
    user_flow_form = aflow.userflow()
    user_flow_form.spec.display_name= "Application"

    # Create form with default submit button and visible cancel button
    user_node_with_form = user_flow_form.form(
        name="ApplicationForm",
        display_name="Application",
        cancel_button_label="Cancel"
    )

    user_node_with_form.text_input_field(name="lastName", label="Last name", required=True, placeholder_text="Enter your name here", help_text="Enter name", 
        regex="^[a-zA-Z0-9\s]+$", regex_error_message="No special characters allowed")
    
    user_flow_form.edge(START, user_node_with_form)
    user_flow_form.edge(user_node_with_form, END)
 
    user_flow = aflow.userflow()
    
    # User input field for sensitive data
    user_input_field = user_flow.field(
        direction="input",
        name="additional_ssn",
        display_name="Additional SSN",
        kind=UserFieldKind.Text,
        text="Enter additional SSN if needed"
    )

    user_output_lastName = user_flow.field(
        direction="output",
        name="display_lastName",
        display_name="Last name (from field input) ",
        kind=UserFieldKind.Text,
        text="Last name (masked all ) {flow.Application.Application.output[\"Last name\"]}",
    )

    user_output_ssn = user_flow.field(
        direction="output",
        name="display_masked_ssn",
        display_name="Masked SSN (from input) ",
        kind=UserFieldKind.Text,
        text="SSN from input (masked all ) {flow.input.ssn}",
    )

    user_output_health_insurance = user_flow.field(
        direction="output",
        name="display_health_insurance",
        display_name="Health insurance (from tool) ",
        kind=UserFieldKind.Text,
        text="Health insurance (masked first 4 ) {flow.process_user_data.output.health_insurance}",
    )
    
    user_output_token = user_flow.field(
        direction="output",
        name="display_masked_token",
        display_name="Masked Auth Token (from private)",
        kind=UserFieldKind.Text,
        text="Auth token from private credentials (masked first 4) {flow.private.credentials.auth_token}",
    )

    user_output_additional_ssn = user_flow.field(
        direction="output",
        name="display_additional_ssn",
        display_name="Masked SSN (from user input)",
        kind=UserFieldKind.Text,
        text="SSN from user input (masked): {flow.userflow_4.additional_ssn.output.value}",
    )

    user_output_codeblock = user_flow.field(
        direction="output",
        name="display_script_ssn",
        display_name="Masked SSN from script",
        kind=UserFieldKind.Text,
        text="Masked SSN from script: {flow.process_data.output.masked_ssn}",
    )

    validate_credentials = user_flow.field(
        direction="output",
        name="validate_credentials_token",
        display_name="Validate credentials client token",
        kind=UserFieldKind.Text,
        text="Masked Validate credentials client token: {flow.validateCredentials.output.token}",
    )
    
    # User flow edges
    user_flow.edge(START, user_input_field)
    user_flow.edge(user_input_field, user_output_lastName)
    user_flow.edge(user_output_lastName, user_output_ssn)
    user_flow.edge(user_output_ssn, user_output_token)
    user_flow.edge(user_output_token, user_output_codeblock)
    user_flow.edge(user_output_codeblock, user_output_additional_ssn)
    user_flow.edge(user_output_additional_ssn, user_output_health_insurance)
    user_flow.edge(user_output_health_insurance, validate_credentials)
    user_flow.edge(validate_credentials, END)
    
    # Create email records with sensitive tokens
    create_emails_script = aflow.script(
        name="create_email_records",
        display_name="Create Email Records",
        script="""
# Create list of email records with API tokens
self.output.emails = [
    {
        "recipient": flow.input.username + "@example.com",
        "api_token": f"TOKEN-{flow.private.credentials.auth_token[:16]}"
    }
]
"""
    )
    
    # ============================================================
    # FINAL OUTPUT SCRIPT
    # ============================================================
    
    # Final script to prepare output
    prepare_output_script = aflow.script(
        name="prepare_output",
        display_name="Prepare Output",
        script="""
self.output.user_id = flow.private.user_id
self.output.username = flow.input.username
self.output.masked_ssn = flow.nodes['process_user_data'].output.masked_ssn
self.output.processing_notes = [
    "User data processed successfully",
    "Sensitive fields masked"
]
"""
    )
    
    # ============================================================
    # FLOW EDGES
    # ============================================================
    
    # Main flow sequence (Python tool nodes commented out)
    aflow.edge(START, process_data_script)
    aflow.edge(process_data_script, user_flow_form)
    aflow.edge(user_flow_form, process_tool_node)
    aflow.edge(process_tool_node, validate_creds_node)
    aflow.edge(validate_creds_node, user_flow)
    aflow.edge(user_flow, create_emails_script)
    aflow.edge(create_emails_script, prepare_output_script)
    aflow.edge(prepare_output_script, END)


    # ============================================================
    # MASKING CONFIGURATION
    # ============================================================
    
    # Mask input field
    aflow.mask_property("flow.input.ssn", masking_policy=MaskingPolicy.MASK_ALL)
    
    # Mask nested private variable
    aflow.mask_property("flow.private.credentials.auth_token", masking_policy=MaskingPolicy.MASK_FIRST4)
        
    # Mask script node output
    aflow.mask_property(f"flow.{process_data_script.spec.name}.output.masked_ssn", masking_policy=MaskingPolicy.MASK_FIRST4)

    # Mask user flow field
    aflow.mask_property(f"flow.userflow_4.additional_ssn.output", masking_policy=MaskingPolicy.MASK_LAST4)
    # Mask form field 
    aflow.mask_property(f"flow.userflow_3.ApplicationForm.output.lastName", masking_policy=MaskingPolicy.MASK_ALL)

    # Mask tool outputs (commented out - uncomment when Python tools are enabled)
    aflow.mask_property(f"flow.{process_tool_node.spec.name}.output.health_insurance", masking_policy=MaskingPolicy.MASK_FIRST4)
    aflow.mask_property(f"flow.{validate_creds_node.spec.name}.output.token", masking_policy=MaskingPolicy.MASK_ALL)

    return aflow
