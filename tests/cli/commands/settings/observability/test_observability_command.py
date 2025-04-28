from unittest.mock import patch, MagicMock

from mocks.mock_typer import get_mock_typer
from utils.matcher import MatchAny



def test_should_register_langfuse_command():
    MockTyper, add_typer, add_command = get_mock_typer()
    with patch(
            'ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.settings_observability_langfuse_app'
    ) as settings_observability_langfuse_app:
        with patch('typer.Typer', MockTyper):
            import ibm_watsonx_orchestrate.cli.commands.settings.observability.observability_command

            add_typer.assert_called_once_with(
                settings_observability_langfuse_app,
                name='langfuse',
                help=MatchAny(str)
            )
