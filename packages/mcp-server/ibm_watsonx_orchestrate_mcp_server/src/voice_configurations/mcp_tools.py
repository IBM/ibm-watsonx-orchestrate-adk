from typing import Any, List, Literal
from ibm_watsonx_orchestrate.agent_builder.voice_configurations import VoiceConfiguration
from ibm_watsonx_orchestrate.agent_builder.voice_configurations.types import VoiceConfigurationListEntry
from ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_controller import VoiceConfigurationsController
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call
from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path

def list_voice_configs(verbose: bool = False) -> List[VoiceConfigurationListEntry] | List[dict[str, Any]]:
    """
    List voice configurations in the watsonx Orchestrate platform

    Args:
        verbose (bool, optional):  Return verbose information without processing. Should only be used for getting extra details. Defaults to False.
    
    Returns:
        List[VoiceConfigurationListEntry]: A list of voice configurations.
    """
    vcc: VoiceConfigurationsController = VoiceConfigurationsController()
    format: Literal[ListFormats.JSON] | None = ListFormats.JSON if not verbose else None
    voice_configs = silent_call(fn=vcc.list_voice_configs, format=format, verbose=verbose)
    return voice_configs

def import_voice_config(file_path: str) -> VoiceConfiguration:
    """
    Imports voice configurations from a spec file into the watsonx Orchestrate platform.

    Args:
        file_path (str): The path to the voice configuration spec file.

    Returns:
        VoiceConfiguration: The voice configuration imported from the spec file.
    """
    working_directory_file_path: str = get_working_directory_path(file_path)
    vcc: VoiceConfigurationsController = VoiceConfigurationsController()
    voice_config = silent_call(fn=vcc.import_voice_config, file=working_directory_file_path)
    silent_call(fn=vcc.publish_or_update_voice_config, voice_config=voice_config)
    return voice_config

def remove_voice_config(voice_config_name: str) -> str:
    """
    Removes a voice configuration from the watsonx Orchestrate platform.
    Args:
        voice_config_name (str): The name of the voice configuration to be removed. 
    Returns:
        str: A success message indicating the voice configuration was removed successfully.
    """
    vcc: VoiceConfigurationsController = VoiceConfigurationsController()
    silent_call(fn=vcc.remove_voice_config_by_name, voice_config_name=voice_config_name)
    return f"Voice configuration '{voice_config_name}' removed successfully." 

__tools__ = [list_voice_configs, import_voice_config, remove_voice_config]
