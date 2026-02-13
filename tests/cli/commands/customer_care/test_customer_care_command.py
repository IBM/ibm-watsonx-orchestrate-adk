from unittest.mock import patch
from tests.mocks.mock_typer import get_mock_typer
from tests.utils.matcher import MatchAny


def test_should_register_platform_command():
    MockTyper, add_typer, add_command = get_mock_typer()
    with patch(
        'ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.customer_care_platform'
    ) as customer_care_platform, \
    patch('typer.Typer', MockTyper):
        import ibm_watsonx_orchestrate.cli.commands.customer_care.customer_care_command
        add_typer.assert_any_call(
            typer_instance=customer_care_platform,
            name='platform',
            help=MatchAny(str)
        )