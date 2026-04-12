from unittest.mock import patch, MagicMock

from mocks.mock_typer import get_mock_typer
from utils.matcher import MatchAny



def test_should_register_observability_command():
    MockTyper, add_typer, add_command = get_mock_typer()
    with patch(
        'ibm_watsonx_orchestrate.cli.commands.settings.observability.observability_command.settings_observability_app'
    ) as settings_observability_app,\
    patch(
        'ibm_watsonx_orchestrate.cli.commands.settings.docker.docker_settings_app'
    ) as docker_settings_app:
        with patch('typer.Typer', MockTyper):
            import ibm_watsonx_orchestrate.cli.commands.settings.settings_command

            add_typer.assert_any_call(
                settings_observability_app,
                name='observability',
                help=MatchAny(str)
            )
            add_typer.assert_any_call(
                docker_settings_app,
                name='docker',
                help=MatchAny(str)
            )
