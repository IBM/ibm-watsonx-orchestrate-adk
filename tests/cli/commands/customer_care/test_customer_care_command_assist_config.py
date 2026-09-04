import sys
from unittest.mock import patch

try:
    from mocks.mock_typer import get_mock_typer
except ImportError:
    from tests.mocks.mock_typer import get_mock_typer

try:
    from utils.matcher import MatchAny
except ImportError:
    from tests.utils.matcher import MatchAny

_MODULE = "ibm_watsonx_orchestrate.cli.commands.customer_care.customer_care_command"


def test_should_register_assist_config_command():
    MockTyper, add_typer, add_command = get_mock_typer()
    # Evict the module so the import statement below actually re-executes it.
    sys.modules.pop(_MODULE, None)
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
        ".customer_care_assist_config_command.customer_care_assist_config"
    ) as customer_care_assist_config, \
    patch("typer.Typer", MockTyper):
        import ibm_watsonx_orchestrate.cli.commands.customer_care.customer_care_command  # noqa: F401
        add_typer.assert_any_call(
            typer_instance=customer_care_assist_config,
            name="assist-config",
            help=MatchAny(str),
            hidden=True,
        )
