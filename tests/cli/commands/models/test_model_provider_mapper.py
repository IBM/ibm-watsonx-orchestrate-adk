import pytest

from ibm_watsonx_orchestrate.agent_builder.models.types import ProviderConfig, ModelProvider
from ibm_watsonx_orchestrate.cli.commands.models.model_provider_mapper import validate_ProviderConfig


class TestModelProviderEnum:
    """Test ModelProvider enum values"""

    def test_redhat_ai_provider_enum_value(self):
        """Test that REDHAT_AI enum value is correctly defined"""
        assert ModelProvider.REDHAT_AI == 'redhat-ai'
        assert str(ModelProvider.REDHAT_AI) == 'redhat-ai'
        assert ModelProvider.has_value('redhat-ai')


class TestRedhatAIProviderValidation:
    """Test validation for REDHAT_AI provider configuration"""

    def test_redhat_ai_missing_custom_host_raises(self, caplog):
        """Test that missing custom_host raises SystemExit for REDHAT_AI provider"""
        cfg = ProviderConfig.model_validate({
            'provider': 'redhat-ai',
            'api_key': 'test-key'
        })

        with pytest.raises(SystemExit):
            validate_ProviderConfig(cfg, app_id='')

        # Verify error message mentions the missing field
        assert 'custom_host' in caplog.text
        assert 'redhat-ai' in caplog.text

    def test_redhat_ai_missing_api_key_raises(self, caplog):
        """Test that missing api_key raises SystemExit for REDHAT_AI provider"""
        cfg = ProviderConfig.model_validate({
            'provider': 'redhat-ai',
            'custom_host': 'https://my-host.com'
        })

        with pytest.raises(SystemExit):
            validate_ProviderConfig(cfg, app_id='')

        # Verify error message mentions the missing field
        assert 'api_key' in caplog.text
        assert 'redhat-ai' in caplog.text

    def test_redhat_ai_missing_both_fields_raises(self, caplog):
        """Test that missing both required fields raises SystemExit for REDHAT_AI provider"""
        cfg = ProviderConfig.model_validate({'provider': 'redhat-ai'})

        with pytest.raises(SystemExit):
            validate_ProviderConfig(cfg, app_id='')

        # Verify error message mentions both missing fields
        assert 'custom_host' in caplog.text
        assert 'api_key' in caplog.text
        assert 'redhat-ai' in caplog.text

    def test_redhat_ai_valid_config_passes(self):
        """Test that valid REDHAT_AI config with both required fields passes validation"""
        cfg = ProviderConfig.model_validate({
            'provider': 'redhat-ai',
            'custom_host': 'https://my-host.com',
            'api_key': 'test-key'
        })

        # Should not raise any exception
        validate_ProviderConfig(cfg, app_id='')

    def test_redhat_ai_valid_config_with_app_id_passes(self, caplog):
        """Test that REDHAT_AI config with app_id shows info message instead of error"""
        cfg = ProviderConfig.model_validate({
            'provider': 'redhat-ai',
            'custom_host': 'https://my-host.com'
            # api_key missing but app_id provided
        })

        # Should not raise when app_id is provided (connection will provide the key)
        validate_ProviderConfig(cfg, app_id='test-connection-id')

        # Should log info message about required fields in connection
        assert 'test-connection-id' in caplog.text

