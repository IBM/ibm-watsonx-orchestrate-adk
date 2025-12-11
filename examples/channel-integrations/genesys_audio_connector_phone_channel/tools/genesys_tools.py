from ibm_watsonx_orchestrate.agent_builder.tools import tool
from typing import Dict, Optional
from pydantic import BaseModel

class GenesysBotConnector(BaseModel):
    output_variables: Dict[str, str]

class ChannelOptions(BaseModel):
    genesys_bot_connector: Optional[GenesysBotConnector]
    genesys_audio_connector: Optional[GenesysBotConnector]


class TransferMetadata(BaseModel):
    channel_options: ChannelOptions


@tool(display_name="transfer_to_human")
def transfer_to_human(reason: str, summary: str, channel_type: str) -> TransferMetadata:
    """
    Use to connect to a human representative, it provides metadata to use for transferring out the chat or call. Get the channel_type from the context. The reason should be why the transfer as initiated. The summary is for a human agent to understand the nature of the transfer and include the conversational context.

    :param reason: The complete reason for transfer - include ALL text from user input without any truncation
    :param summary: A complete summary for the human agent including full conversational context
    :param channel_type: The current channel type that the agent is in which can be accessed in the context variable.

    :returns: An object to be passed to Genesys Cloud for further routing of the chat or call.
    """
    if channel_type == "genesys_bot_connector":
        channel_options = {
            "genesys_bot_connector": {
                "output_variables": {
                    "summary": summary,
                    "reason": reason,
                    "custom variable": "your custom variable"
                }
            },
            "genesys_audio_connector": None
        }

    elif channel_type == "genesys_audio_connector":
        channel_options = {
            "genesys_bot_connector": None,
            "genesys_audio_connector": {
                "output_variables": {
                    "summary": summary,
                    "reason": reason,
                    "custom variable": "your custom variable"
                }
            }
        }
    else:
        channel_options = {
            "genesys_bot_connector": None,
            "genesys_audio_connector": None
        }

    transfer_metadata = {
        "channel_options": channel_options
    }

    return TransferMetadata.model_validate(transfer_metadata, strict=False)


class EndSessionMetadata(BaseModel):
    channel_options: ChannelOptions


@tool(display_name="end_session")
def end_session(reason: str, summary: str, channel_type: str) -> EndSessionMetadata:
    """
    Use to end the chat or call, it provides metadata to use for transferring out the chat or call. Get the channel_type from the context. The reason should be why the chat was ended. The summary is just a couple of sentences describing why the chat was disconnected or ended.

    :param reason: The complete reason for ending - include ALL text from user input without any truncation
    :param summary: A complete summary of the conversation
    :param channel_type: The current channel type that the agent is in which can be accessed in the context variable

    :returns: An object to be passed to Genesys Cloud for further routing of the chat or call.
    """
    if channel_type == "genesys_bot_connector":
        channel_options = {
            "genesys_bot_connector": {
                "output_variables": {
                    "summary": summary,
                    "reason": reason,
                    "custom variable": "your custom variable"
                }
            },
            "genesys_audio_connector": None
        }

    elif channel_type == "genesys_audio_connector":
        channel_options = {
            "genesys_bot_connector": None,
            "genesys_audio_connector": {
                "output_variables": {
                    "summary": summary,
                    "reason": reason,
                    "custom variable": "your custom variable"
                }
            }
        }
    else:
        channel_options = {
            "genesys_bot_connector": None,
            "genesys_audio_connector": None
        }

    end_session_metadata = {
        "channel_options": channel_options
    }

    return EndSessionMetadata.model_validate(end_session_metadata, strict=False)
