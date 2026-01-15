from typing import Optional, Literal, Union, ClassVar
from pydantic import BaseModel, Field, ConfigDict, model_validator
import json
from enum import Enum

from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion

class ChannelType(str, Enum):
    """Supported channel types for agent integrations."""
    WEBCHAT = "webchat"
    TWILIO_WHATSAPP = "twilio_whatsapp"
    TWILIO_SMS = "twilio_sms"
    SLACK = "byo_slack"
    GENESYS_BOT_CONNECTOR = "genesys_bot_connector"
    FACEBOOK = "facebook"
    TEAMS = "teams"

    def __str__(self):
        return self.value

    def __repr__(self):
        return repr(self.value)


class ChannelKind(str, Enum):
    CHANNEL = "channel"

    def __str__(self):
        return self.value

    def __repr__(self):
        return repr(self.value)

class BaseChannel(BaseModel):
    """Base class for all channel types.

    This class defines common fields and behaviors for all channel implementations.
    Response-only fields (marked in SERIALIZATION_EXCLUDE) should not be sent to the API
    when creating or updating channels.
    """

    # Fields to exclude when serializing for API requests (response-only fields)
    SERIALIZATION_EXCLUDE: ClassVar[set] = {
        "channel_id", "tenant_id", "agent_id", "environment_id",
        "created_on", "created_by", "updated_at", "updated_by"
    }

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # User-editable fields
    name: str = Field(..., max_length=64, description="Channel name (required)")
    description: Optional[str] = Field(None, max_length=1024)
    channel: str = Field(..., description="Channel type identifier")
    spec_version: SpecVersion = SpecVersion.V1
    kind: ChannelKind = ChannelKind.CHANNEL

    # Response-only fields
    channel_id: Optional[str] = Field(None, description="Channel ID (response only)")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (response only)")
    agent_id: Optional[str] = Field(None, description="Agent ID (response only)")
    environment_id: Optional[str] = Field(None, description="Environment ID (response only)")
    created_on: Optional[str] = Field(None, description="Creation timestamp (response only)")
    created_by: Optional[str] = Field(None, description="Creator user ID (response only)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (response only)")
    updated_by: Optional[str] = Field(None, description="Last updater user ID (response only)")

    def dumps_spec(self, exclude_none: bool = True, exclude_unset: bool = False) -> str:
        """Serialize channel to JSON string for API submission.

        Args:
            exclude_none: Exclude fields with None values
            exclude_unset: Exclude fields that were not explicitly set

        Returns:
            JSON string representation
        """
        data = self.model_dump(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            exclude=self.SERIALIZATION_EXCLUDE
        )
        return json.dumps(data, indent=2)

    def get_api_path(self) -> str:
        """Get the API endpoint path for this channel type.

        By default, returns the channel type as-is. Subclasses can override
        this if the API path differs from the channel type value.

        Returns:
            API endpoint path segment (e.g., 'slack', 'twilio_whatsapp')
        """
        return self.channel

class WebchatChannel(BaseChannel):
    """Webchat channel configuration.

    Enables integration with watsonx Orchestrate webchat.
    This channel is primarily managed through the embed command
    which generates embed code snippets for web integration.

    Attributes:
        channel: Always "webchat"
    """

    channel: Literal["webchat"] = "webchat"

class TwilioWhatsappChannel(BaseChannel):
    """Twilio WhatsApp channel configuration.

    Enables integration with WhatsApp through Twilio API.

    Required credentials:
        - Twilio Account SID
        - Twilio Authentication Token

    Attributes:
        channel: Always "twilio_whatsapp"
        account_sid: Twilio Account SID
        twilio_authentication_token: Twilio Auth Token
    """

    channel: Literal["twilio_whatsapp"] = "twilio_whatsapp"
    account_sid: Optional[str] = Field(
        None,
        min_length=34,
        max_length=34,
        pattern=r"^AC[a-zA-Z0-9]{32}$",
        description="Twilio Account SID"
    )
    twilio_authentication_token: Optional[str] = Field(
        None,
        min_length=1,
        description="Twilio Authentication Token"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Twilio credentials are provided."""
        if not self.account_sid:
            raise ValueError("account_sid is required for twilio_whatsapp channels")
        if not self.twilio_authentication_token:
            raise ValueError("twilio_authentication_token is required for twilio_whatsapp channels")
        return self

class TwilioSMSChannel(BaseChannel):
    """Twilio SMS channel configuration.

    Enables integration with SMS through Twilio API.

    Required credentials:
        - Twilio Account SID
        - Twilio Authentication Token

    Attributes:
        channel: Always "twilio_sms"
        account_sid: Twilio Account SID
        twilio_authentication_token: Twilio Auth Token
        phone_number: Optional phone number for SMS
    """

    channel: Literal["twilio_sms"] = "twilio_sms"
    account_sid: Optional[str] = Field(
        None,
        min_length=34,
        max_length=34,
        pattern="^AC[0-9a-fA-F]{32}$",
        description="Twilio Account SID"
    )
    twilio_authentication_token: Optional[str] = Field(
        None,
        min_length=1,
        description="Twilio Authentication Token"
    )
    phone_number: Optional[str] = Field(
        None,
        description="Phone number for SMS"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Twilio credentials are provided."""
        if not self.account_sid:
            raise ValueError("account_sid is required for twilio_sms channels")
        if not self.twilio_authentication_token:
            raise ValueError("twilio_authentication_token is required for twilio_sms channels")
        return self

class SlackTeam(BaseModel):
    """Slack team/workspace configuration.

    Attributes:
        id: Slack team/workspace ID
        bot_access_token: Bot user OAuth token for this team
    """
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str = Field(..., min_length=1, description="Slack team/workspace ID")
    bot_access_token: str = Field(..., min_length=1, description="Bot user OAuth token")


class SlackChannel(BaseChannel):
    """Slack channel configuration.

    Enables integration with Slack using the BYO (Bring Your Own) Slack app model.

    Required credentials:
        - client_id: Slack API client ID
        - client_secret: Slack API client secret
        - signing_secret: Slack API signing secret
        - teams: List of Slack teams with bot access tokens

    Attributes:
        channel: Always "byo_slack"
        client_id: Slack API client ID
        client_secret: Slack API client secret
        signing_secret: Slack API signing secret
        teams: List of Slack teams/workspaces with their bot tokens
    """

    channel: Literal["byo_slack"] = "byo_slack"

    def get_api_path(self) -> str:
        """Get the API endpoint path for this channel type.

        Note: The API uses 'slack' in the URL path but 'byo_slack' in the payload.
        """
        return "slack"

    client_id: Optional[str] = Field(
        None,
        min_length=1,
        description="Slack API client ID"
    )
    client_secret: Optional[str] = Field(
        None,
        min_length=1,
        description="Slack API client secret"
    )
    signing_secret: Optional[str] = Field(
        None,
        min_length=1,
        description="Slack API signing secret"
    )
    teams: Optional[list[SlackTeam]] = Field(
        None,
        description="List of Slack teams/workspaces with their bot access tokens"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Slack credentials are provided."""
        if not self.client_id:
            raise ValueError("client_id is required for byo_slack channels")
        if not self.client_secret:
            raise ValueError("client_secret is required for byo_slack channels")
        if not self.signing_secret:
            raise ValueError("signing_secret is required for byo_slack channels")
        if not self.teams or len(self.teams) == 0:
            raise ValueError("at least one team with bot_access_token is required for byo_slack channels")
        return self
    
class GenesysBotConnectorChannel(BaseChannel):
    """Genesys Bot Connector channel configuration.

    Required credentials:
        - client_id
        - client_secret
        - verification_token
        - bot_connector_id

    Attributes:
        channel: Always "genesys_bot_connector"
        client_id: Genesys cloud client id
        client_secret: Genesys cloud client secret
        verification_token: The secret value defined in the Genesys Credentials tab
        bot_connector_id: The integration ID from your Genesys Bot Connector
        api_url: Genesys API Server URI
    """

    channel: Literal["genesys_bot_connector"] = "genesys_bot_connector"
    client_id: Optional[str] = Field(
        None,
        min_length=36,
        max_length=36,
        pattern="^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        description="Genesys cloud client id"
    )
    client_secret: Optional[str] = Field(
        None,
        min_length=1,
        description="Genesys cloud client secret"
    )
    verification_token: Optional[str] = Field(
        None,
        min_length=1,
        description="The secret value defined in the Genesys Credentials tab"
    )
    bot_connector_id: Optional[str] = Field(
        None,
        min_length=36,
        max_length=36,
        pattern="^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        description="The integration ID from your Genesys Bot Connector"
    )
    api_url: Optional[str] = Field(
        None,
        min_length=1,
        max_length=64,
        pattern="^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$",
        description="Genesys API Server URI"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Genesys credentials are provided."""
        if not self.client_id:
            raise ValueError("client_id is required for genesys_bot_connector channels")
        if not self.client_secret:
            raise ValueError("client_secret is required for genesys_bot_connector channels")
        if not self.verification_token:
            raise ValueError("verification_token is required for genesys_bot_connector channels")
        if not self.bot_connector_id:
            raise ValueError("bot_connector_id is required for genesys_bot_connector channels")
        if not self.api_url:
            raise ValueError("api_url is required for genesys_bot_connector channels")
        return self

class FacebookChannel(BaseChannel):
    """Facebook Messenger channel configuration.

    Enables integration with Facebook Messenger.

    Required credentials:
        - application_secret
        - verification_token
        - page_access_token

    Attributes:
        channel: Always "facebook"
        application_secret: Facebook application secret
        verification_token: Token for webhook verification
        page_access_token: Facebook page access token
    """

    channel: Literal["facebook"] = "facebook"
    application_secret: Optional[str] = Field(
        None,
        min_length=1,
        description="Facebook app secret"
    )
    verification_token: Optional[str] = Field(
        None,
        min_length=1,
        description="Token for webhook verification"
    )
    page_access_token: Optional[str] = Field(
        None,
        min_length=1,
        description="Page-specific access token"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Facebook credentials are provided."""
        if not self.application_secret:
            raise ValueError("application_secret is required for facebook channels")
        if not self.verification_token:
            raise ValueError("verification_token is required for facebook channels")
        if not self.page_access_token:
            raise ValueError("page_access_token is required for facebook channels")
        return self

class TeamsChannel(BaseChannel):
    """Microsoft Teams channel configuration.

    Enables integration with Microsoft Teams.

    Required credentials:
        - app_password
        - app_id

    Attributes:
        channel: Always "teams"
        app_password: Microsoft App Client secret
        app_id: Microsoft Application (client) ID
        teams_tenant_id: Microsoft Teams tenant ID
    """

    channel: Literal["teams"] = "teams"
    app_password: Optional[str] = Field(
        None,
        min_length=1,
        description="Microsoft App Client secret"
    )
    app_id: Optional[str] = Field(
        None,
        min_length=1,
        description="Microsoft Application (client) ID"
    )
    teams_tenant_id: Optional[str] = Field(
        None,
        min_length=1,
        description="Microsoft Teams tenant ID"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Teams credentials are provided."""
        if not self.app_password:
            raise ValueError("app_password is required for teams channels")
        if not self.app_id:
            raise ValueError("app_id is required for teams channels")
        return self

# Union type for all channel types
Channel = Union[WebchatChannel, TwilioWhatsappChannel, TwilioSMSChannel, SlackChannel, GenesysBotConnectorChannel, FacebookChannel, TeamsChannel]
