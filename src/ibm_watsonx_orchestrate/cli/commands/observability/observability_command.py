"""Observability commands for Watson Orchestrate CLI."""

import typer

from ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_command import traces_app


observability_app = typer.Typer(no_args_is_help=True, help="Observability commands")

# Add traces as a subcommand
observability_app.add_typer(traces_app, name="traces", help="Trace management commands")
