import pytest
from unittest.mock import MagicMock, patch

from ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config.customer_care_assist_config_controller import (
    coerce_value,
    list_assist_config,
    set_assist_config,
    remove_assist_config,
    reset_assist_config,
)


# ── coerce_value ────────────────────────────────────────────────────────────

class TestCoerceValue:
    @pytest.mark.parametrize("raw,expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
    ])
    def test_booleans(self, raw, expected):
        assert coerce_value(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("0", 0),
        ("10", 10),
        ("-5", -5),
    ])
    def test_integers(self, raw, expected):
        assert coerce_value(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("0.7", 0.7),
        ("1.0", 1.0),
        ("-0.5", -0.5),
    ])
    def test_floats(self, raw, expected):
        assert coerce_value(raw) == expected

    @pytest.mark.parametrize("raw", [
        "granite-3-8b",
        "some-model-name",
        "",
        "1e5",
    ])
    def test_strings(self, raw):
        result = coerce_value(raw)
        assert result == raw
        assert isinstance(result, str)

    def test_negative_int(self):
        # "-5" round-trips through str(int("-5")) == "-5" → int
        assert coerce_value("-5") == -5
        assert isinstance(coerce_value("-5"), int)

    def test_float_not_coerced_to_int(self):
        # "1.0" has a dot so it must be float, not int
        result = coerce_value("1.0")
        assert result == 1.0
        assert isinstance(result, float)

    def test_scientific_notation_stays_string(self):
        # "1e5" has no dot and fails int round-trip → str
        result = coerce_value("1e5")
        assert result == "1e5"
        assert isinstance(result, str)


# ── list_assist_config ───────────────────────────────────────────────────────

class TestListAssistConfig:
    def test_prints_overrides_table(self, capsys):
        mock_client = MagicMock()
        mock_client.get.return_value = {"min_confidence": 0.7, "llm_max_tokens": 512}

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_controller.get_customer_care_config_client",
            return_value=mock_client,
        ):
            list_assist_config()

        captured = capsys.readouterr()
        assert "Property" in captured.out
        assert "Value" in captured.out
        assert "min_confidence" in captured.out
        assert "0.7" in captured.out
        assert "llm_max_tokens" in captured.out
        assert "512" in captured.out

    def test_logs_no_overrides_when_none(self, caplog):
        mock_client = MagicMock()
        mock_client.get.return_value = None

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_controller.get_customer_care_config_client",
            return_value=mock_client,
        ):
            list_assist_config()

        assert "No configuration overrides are set." in caplog.text


# ── set_assist_config ────────────────────────────────────────────────────────

class TestSetAssistConfig:
    def test_calls_client_set_with_coerced_value(self):
        mock_client = MagicMock()

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_controller.get_customer_care_config_client",
            return_value=mock_client,
        ):
            set_assist_config(property_name="min_confidence", value="0.7")

        mock_client.set.assert_called_once_with({"min_confidence": 0.7})

    def test_coerces_bool(self):
        mock_client = MagicMock()

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_controller.get_customer_care_config_client",
            return_value=mock_client,
        ):
            set_assist_config(property_name="llm_strict_mode", value="true")

        mock_client.set.assert_called_once_with({"llm_strict_mode": True})

    def test_coerces_int(self):
        mock_client = MagicMock()

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_controller.get_customer_care_config_client",
            return_value=mock_client,
        ):
            set_assist_config(property_name="llm_max_tokens", value="512")

        mock_client.set.assert_called_once_with({"llm_max_tokens": 512})


# ── remove_assist_config ─────────────────────────────────────────────────────

class TestRemoveAssistConfig:
    def test_calls_client_remove(self):
        mock_client = MagicMock()

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_controller.get_customer_care_config_client",
            return_value=mock_client,
        ):
            remove_assist_config(property_name="min_confidence")

        mock_client.remove.assert_called_once_with("min_confidence")


# ── reset_assist_config ──────────────────────────────────────────────────────

class TestResetAssistConfig:
    def test_calls_client_reset(self):
        mock_client = MagicMock()

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_controller.get_customer_care_config_client",
            return_value=mock_client,
        ):
            reset_assist_config()

        mock_client.reset.assert_called_once()
