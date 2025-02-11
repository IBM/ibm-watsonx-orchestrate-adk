import json
from pathlib import Path
import logging
import pytest
import re
import requests

from ibm_watsonx_orchestrate.cli.commands.models import models_command

class DummyResponse:
    def __init__(self, status_code, json_data, content=b""):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content

    def json(self):
        return self._json_data


def test_no_models_found(monkeypatch, caplog):
    fake_env = {"WATSONX_URL": "http://dummy"}
    monkeypatch.setattr(models_command, "merge_env", lambda default, user: fake_env)
    monkeypatch.setattr(models_command, "get_default_env_file", lambda: Path("dummy.env"))

    def dummy_requests_get(url):
        return DummyResponse(200, {"resources": []})

    monkeypatch.setattr(requests, "get", dummy_requests_get)

    caplog.set_level(logging.INFO)
    models_command.model_list()

    assert "No models found." in caplog.text


def test_models_list_with_preferred_and_incompatible(monkeypatch, caplog, capsys):
    fake_env = {
        "WATSONX_URL": "http://dummy",
        "PREFERRED_MODELS": "preferred",
        "INCOMPATIBLE_MODELS": "incomp"
    }
    monkeypatch.setattr(models_command, "merge_env", lambda default, user: fake_env)
    monkeypatch.setattr(models_command, "get_default_env_file", lambda: Path("dummy.env"))

    dummy_models = {
        "resources": [
            {"model_id": "incomp-model", "short_description": "Should be filtered out"},
            {"model_id": "preferred-model", "short_description": "This is preferred"},
            {"model_id": "other-model", "short_description": "Regular model"}
        ]
    }

    def dummy_requests_get(url):
        return DummyResponse(200, dummy_models)

    monkeypatch.setattr(requests, "get", dummy_requests_get)
    caplog.set_level(logging.INFO)

    models_command.model_list()

    text = capsys.readouterr().out

    assert "Available Models" in text
    assert "watsonx/incomp-model" not in text
    assert "★ indicates a supported and preferred model" in text
    assert "watsonx/other-model" in text
    assert "Regular model" in text
    preferred_regex = re.compile(r"\★ watsonx\/preferred-model.*This is preferred")
    preferred_match = re.search(preferred_regex, text)
    other_regex = re.compile(r"watsonx\/other-model.*Regular model")
    other_match = re.search(other_regex, text)
    assert preferred_match and other_match
    assert preferred_match.span()[0] < other_match.span()[0]
    assert preferred_match.span()[1] < other_match.span()[1]
    assert preferred_match.span()[1] < other_match.span()[0]

def test_models_list_raw_with_preferred_and_incompatible(monkeypatch, caplog, capsys):
    fake_env = {
        "WATSONX_URL": "http://dummy",
        "PREFERRED_MODELS": "preferred",
        "INCOMPATIBLE_MODELS": "incomp"
    }
    monkeypatch.setattr(models_command, "merge_env", lambda default, user: fake_env)
    monkeypatch.setattr(models_command, "get_default_env_file", lambda: Path("dummy.env"))

    dummy_models = {
        "resources": [
            {"model_id": "incomp-model", "short_description": "Should be filtered out"},
            {"model_id": "preferred-model", "short_description": "This is preferred"},
            {"model_id": "other-model", "short_description": "Regular model"}
        ]
    }

    def dummy_requests_get(url):
        return DummyResponse(200, dummy_models)

    monkeypatch.setattr(requests, "get", dummy_requests_get)
    caplog.set_level(logging.INFO)

    models_command.model_list(print_raw=True)

    text = capsys.readouterr().out

    assert "Available Models:" in text
    assert "incomp-model" not in text
    assert "★ indicates a supported and preferred model" in text
    assert "other-model: Regular model" in text
    preferred_index = text.find("★ watsonx/preferred-model: This is preferred")
    other_index = text.find("other-model: Regular model")
    assert preferred_index != -1 and other_index != -1
    assert preferred_index < other_index