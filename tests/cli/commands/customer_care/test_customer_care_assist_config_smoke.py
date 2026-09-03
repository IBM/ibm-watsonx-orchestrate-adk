"""Smoke test: verify CLI entry point shows correct help output."""
import pytest
from typer.testing import CliRunner
from ibm_watsonx_orchestrate.cli.commands.customer_care.customer_care_command import customer_care_app


@pytest.fixture
def runner():
    return CliRunner()


def test_assist_config_hidden_from_customer_care_help(runner):
    result = runner.invoke(customer_care_app, ["--help"])
    assert result.exit_code == 0
    assert "platform" in result.output
    assert "assist-config" not in result.output


def test_assist_config_subcommands_visible(runner):
    result = runner.invoke(customer_care_app, ["assist-config", "--help"])
    assert result.exit_code == 0
    for cmd in ["list", "set", "remove", "reset"]:
        assert cmd in result.output
