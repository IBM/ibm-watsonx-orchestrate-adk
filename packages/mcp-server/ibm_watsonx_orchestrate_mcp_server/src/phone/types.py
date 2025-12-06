from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.phone.types import PhoneChannelType


class BasePhoneConfigOptions(BaseModel):
    """Base options for phone config operations requiring config identification."""
    config_id: Optional[str] = Field(
        default=None,
        description="Phone config ID. Either config_id or config_name must be provided."
    )
    config_name: Optional[str] = Field(
        default=None,
        description="Phone config name. Either config_id or config_name must be provided."
    )


class ListPhoneConfigsOptions(BaseModel):
    """Options for listing phone configs."""
    channel_type: Optional[PhoneChannelType] = Field(
        default=None,
        description="Optional filter to list only configs of a specific type (e.g., 'genesys_audio_connector')"
    )
    verbose: bool = Field(
        default=False,
        description="If True, return full config details in raw format"
    )


class CreatePhoneConfigOptions(BaseModel):
    """Options for creating or updating a phone config."""
    name: str = Field(
        description="Phone config name. If a config with this name exists, it will be updated."
    )
    channel_type: PhoneChannelType = Field(
        description="The type of phone channel (e.g., 'genesys_audio_connector')"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the phone config"
    )
    channel_config: Dict[str, Any] = Field(
        description="Channel-specific configuration. For Genesys Audio Connector: {'security': {'api_key': '...', 'client_secret': '...'}}"
    )


class GetPhoneConfigOptions(BasePhoneConfigOptions):
    """Options for getting a specific phone config."""
    verbose: bool = Field(
        default=False,
        description="If True, return full config details in raw format"
    )


class DeletePhoneConfigOptions(BasePhoneConfigOptions):
    """Options for deleting a phone config."""
    pass


class ImportPhoneConfigOptions(BaseModel):
    """Options for importing phone config(s) from a file."""
    file_path: str = Field(
        description="The path to the phone config specification file. Supports YAML (.yaml, .yml), JSON (.json), or Python (.py) files."
    )


class ExportPhoneConfigOptions(BasePhoneConfigOptions):
    """Options for exporting a phone config to a YAML file."""
    output_path: str = Field(
        description="The file path where the phone config YAML should be saved. Must end with .yaml or .yml extension."
    )


class AttachAgentOptions(BasePhoneConfigOptions):
    """Options for attaching an agent to a phone config."""
    agent_name: str = Field(
        description="The name of the agent to attach"
    )
    environment: Literal["draft", "live"] = Field(
        description="The environment (draft or live) to attach"
    )


class DetachAgentOptions(BasePhoneConfigOptions):
    """Options for detaching an agent from a phone config."""
    agent_name: str = Field(
        description="The name of the agent to detach"
    )
    environment: Literal["draft", "live"] = Field(
        description="The environment (draft or live) to detach"
    )


class ListAttachmentsOptions(BasePhoneConfigOptions):
    """Options for listing attachments for a phone config."""
    pass
