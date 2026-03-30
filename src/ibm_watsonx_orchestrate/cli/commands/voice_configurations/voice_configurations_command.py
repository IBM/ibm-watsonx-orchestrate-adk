import sys
from typing import Annotated, Optional
import typer
import logging
import rich

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


@voice_configurations_app.command(name="get", help="Get a voice configuration by ID or name")
def get_voice_config(
  config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Voice config ID to retrieve (Either ID or name is required)"),
  config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Voice config name to retrieve (Either ID or name is required)"),
):
  """Get and display a voice configuration."""
  voice_config_controller = VoiceConfigurationsController()

  # Get the config by ID or name
  if config_id and config_name:
    logger.error("Please specify either --id or --name, not both")
    sys.exit(1)

  if not config_id and not config_name:
    logger.error("Please specify either --id or --name")
    sys.exit(1)

  if config_id:
    voice_config = voice_config_controller.get_voice_config(config_id)
    if not voice_config:
      logger.error(f"Voice config with ID '{config_id}' not found")
      sys.exit(1)
  else:
    voice_config = voice_config_controller.get_voice_config_by_name(config_name)
    if not voice_config:
      logger.error(f"Voice config with name '{config_name}' not found")
      sys.exit(1)

  rich.print_json(voice_config.dumps_spec())


@voice_configurations_app.command(name="export", help="Export a voice configuration to a YAML file by ID or name")
def export_voice_config(
  config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Voice config ID to export (Either ID or name is required)"),
  config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Voice config name to export (Either ID or name is required)"),
  output: str = typer.Option(..., "--output", "-o", help="Path where the YAML file should be saved"),
):
  """Export a voice configuration to a YAML file."""
  voice_config_controller = VoiceConfigurationsController()
  resolved_id = voice_config_controller.resolve_config_id(config_id, config_name)
  voice_config_controller.export_voice_config(resolved_id, output)