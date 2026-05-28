import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def patch_models_controller():
    mock_model = MagicMock()
    mock_model.name = "watsonx/default/llm"
    mock_model.is_default = True

    with patch(
        "ibm_watsonx_orchestrate.agent_builder.agents.types.ModelsController"
    ) as mock_cls:
        mock_cls.return_value.formatted_list_all.return_value = [mock_model]
        yield
