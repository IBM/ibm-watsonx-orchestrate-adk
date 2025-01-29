from unittest.mock import patch, MagicMock

from mocks.mock_typer import get_mock_typer
from utils.matcher import MatchAny



def test_should_register_application_connections_command():
    MockTyper, add_typer = get_mock_typer()
    with patch(
            # Note this is different from how we normally patch. Normally you patch what the variable would become
            # within the module you're importing. But in this case we haven't imported the module yet, so we instead
            # have to patch the thing the module will import.
            'ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_command.connections_application_app'
    ) as connections_application_app:
        with patch('typer.Typer', MockTyper):
            # We cannot have the import at the root or there's no way to test the side effects of importing the file
            import ibm_watsonx_orchestrate.cli.commands.connections.connections_command
            add_typer.assert_called_once_with(
                connections_application_app,
                name='application',
                help=MatchAny(str)
            )
