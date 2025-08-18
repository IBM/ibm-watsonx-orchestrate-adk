import sys
from typing import Annotated
import typer
import logging

from ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_controller import VoiceConfigurationsController

logger = logging.getLogger(__name__)

voice_configurations_app = typer.Typer(no_args_is_help=True)

@voice_configurations_app.command(name="import", help="Import a voice configuration into the active environment from a file")
def import_voice_config(
  file: Annotated[
    str,
    typer.Option(
      "--file",
      "-f",
      help="YAML file with voice configuraton definition"
    )
  ],
):
  voice_config_controller = VoiceConfigurationsController()
  imported_config = voice_config_controller.import_voice_config(file)
  voice_config_controller.publish_or_update_voice_config(imported_config)

@voice_configurations_app.command(name="remove", help="Remove a voice configuration from the active environment")
def remove_voice_config(
  voice_config_name: Annotated[
    str,
    typer.Option(
      "--name",
      "-n",
      help="name of the voice configuration to remove"
    )
  ] = None,
):
  voice_config_controller = VoiceConfigurationsController()
  if voice_config_name:
    voice_config_controller.remove_voice_config_by_name(voice_config_name)
  else:
    raise TypeError("You must specify the name of a voice configuration")
    
    

@voice_configurations_app.command(name="list", help="List all voice configurations in the active environment")
def list_voice_configs(
  verbose: Annotated[
    bool,
    typer.Option(
      "--verbose",
      "-v",
      help="List full details of all voice configurations in json format"
    )
  ] = False,
):
  voice_config_controller = VoiceConfigurationsController()
  voice_config_controller.list_voice_configs(verbose)