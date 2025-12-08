from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelType


class BaseChannelOptions(BaseModel):
    """Base options for channel operations requiring agent and environment."""
    agent_name: str = Field(
        description="The name of the agent to operate on"
    )
    environment: Literal["draft", "live"] = Field(
        description="The environment (draft or live) to operate in"
    )


class ListChannelsOptions(BaseChannelOptions):
    """Options for listing channels."""
    channel_type: Optional[ChannelType] = Field(
        default=None,
        description="Optional filter to list only channels of a specific type"
    )
    verbose: bool = Field(
        default=False,
        description="If True, return full channel details in raw format"
    )


class CreateChannelOptions(BaseChannelOptions):
    """Options for creating or updating a channel."""
    channel_type: ChannelType = Field(
        description="The type of channel to create (e.g., 'twilio_whatsapp', 'twilio_sms', 'byo_slack'). Note: 'webchat' cannot be created via this tool."
    )
    name: str = Field(
        description="The name of the channel. If a channel with this name already exists, it will be updated."
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the channel"
    )
    channel_config: Dict[str, Any] = Field(
        description="Channel-specific configuration. For Twilio WhatsApp: {'account_sid': '...', 'auth_token': '...', 'from_number': '...'}. For Twilio SMS: {'account_sid': '...', 'auth_token': '...', 'from_number': '...'}. For Slack: {'bot_token': '...', 'signing_secret': '...'}"
    )


class GetChannelOptions(BaseChannelOptions):
    """Options for getting a specific channel."""
    channel_type: ChannelType = Field(
        description="The type of channel to retrieve"
    )
    channel_id: Optional[str] = Field(
        default=None,
        description="The ID of the channel to retrieve. Either channel_id or channel_name must be provided."
    )
    channel_name: Optional[str] = Field(
        default=None,
        description="The name of the channel to retrieve. Either channel_id or channel_name must be provided."
    )
    verbose: bool = Field(
        default=False,
        description="If True, return full channel details in raw format"
    )


class DeleteChannelOptions(BaseChannelOptions):
    """Options for deleting a channel."""
    channel_type: ChannelType = Field(
        description="The type of channel to delete"
    )
    channel_id: Optional[str] = Field(
        default=None,
        description="The ID of the channel to delete. Either channel_id or channel_name must be provided."
    )
    channel_name: Optional[str] = Field(
        default=None,
        description="The name of the channel to delete. Either channel_id or channel_name must be provided."
    )


class ExportChannelOptions(BaseChannelOptions):
    """Options for exporting a channel to a YAML file."""
    channel_type: ChannelType = Field(
        description="The type of channel to export"
    )
    channel_id: Optional[str] = Field(
        default=None,
        description="The ID of the channel to export. Either channel_id or channel_name must be provided."
    )
    channel_name: Optional[str] = Field(
        default=None,
        description="The name of the channel to export. Either channel_id or channel_name must be provided."
    )
    output_path: str = Field(
        description="The file path where the channel YAML should be saved. Must end with .yaml or .yml extension."
    )


class ImportChannelOptions(BaseChannelOptions):
    """Options for importing channel(s) from a file."""
    file_path: str = Field(
        description="The path to the channel specification file. Supports YAML (.yaml, .yml), JSON (.json), or Python (.py) files."
    )


class WebchatEmbedOptions(BaseChannelOptions):
    """Options for generating webchat embed code."""
    pass  # Only needs agent_name and environment from base class
