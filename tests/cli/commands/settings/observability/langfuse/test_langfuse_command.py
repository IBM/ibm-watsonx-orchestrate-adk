import os
import unittest
from unittest.mock import patch

import pytest

from ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command import configure_langfuse, \
    get_langfuse
from ibm_watsonx_orchestrate.client.analytics.llm.analytics_llm_client import AnalyticsLLMConfig, \
    AnalyticsLLMUpsertToolIdentifier
from mocks.mock_base_api import get_analytics_llm_mock
from utils.matcher import MatchesObjectContaining

DIRNAME = os.path.dirname(os.path.realpath(__file__))

class TestObservabilityConfiguration:
    def test_configure_should_update_langfuse_without_config_file(self,snapshot):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            from pathlib import Path

            path = str(Path(DIRNAME, '../../../../resources/yaml_samples/sample_langfuse_minimal.yml').resolve())
            configure_langfuse(
                url='https://cloud.langfuse.com',
                project_id='projectId',
                api_key='api_key',
                mask_pii=True,
                config_file=path,
                host_health_uri='https://cloud.langfuse.com//api/public/otel'
            )
            update.assert_called_once()
            request = update.call_args.args[0]
            snapshot.assert_match(request.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True))
            logger.info.assert_called_once_with("Langfuse integration updated")



    def test_configure_should_update_langfuse_with_config_file(self, snapshot):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            from pathlib import Path
            path = str(Path(DIRNAME, '../../../../resources/yaml_samples/sample_langfuse_full.yml').resolve())
            configure_langfuse(
                config_file=path
            )
            update.assert_called_once()
            request = update.call_args.args[0]
            snapshot.assert_match(request.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True))
            logger.info.assert_called_once_with("Langfuse integration updated")


    def test_configure_should_update_langfuse_with_config_file_mixed(self, snapshot):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            from pathlib import Path
            path = str(Path(DIRNAME, '../../../../resources/yaml_samples/sample_langfuse_minimal.yml').resolve())
            configure_langfuse(
                url='https://cloud.langfuse.com',
                project_id='projectId',
                api_key='api_key',
                config_file=path,
                host_health_uri='https://cloud.langfuse.com//api/public/otel'
            )
            update.assert_called_once()
            request = update.call_args.args[0]
            snapshot.assert_match(request.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True))
            logger.info.assert_called_once_with("Langfuse integration updated")


    def test_configure_should_show_warning_if_project_id_missing(self, snapshot):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
                patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            from pathlib import Path
            path = str(Path(DIRNAME, '../../../../resources/yaml_samples/sample_langfuse_minimal.yml').resolve())
            configure_langfuse(
                url='https://cloud.langfuse.com',
                api_key='api_key',
                host_health_uri='https://cloud.langfuse.com//api/public/otel'
            )
            update.assert_called_once()
            request = update.call_args.args[0]
            snapshot.assert_match(request.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True))
            logger.warning.assert_called_once_with("The --project-id was not specified, defaulting to \"default\"")


    def test_configure_should_error_if_api_key_missing(self):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger, \
            pytest.raises(SystemExit) as exit_code
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            configure_langfuse(
                url='https://cloud.langfuse.com',
                host_health_uri='https://cloud.langfuse.com//api/public/otel',
            )
            update.assert_not_called()
            logger.error.assert_called_once_with("The --api-key argument is required when an api_key is not specified via a config file")
            assert exit_code.value.code == 1


    def test_configure_should_error_if_url_missing(self):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger, \
            pytest.raises(SystemExit) as exit_code
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            configure_langfuse(
                api_key='my-key',
                host_health_uri='https://cloud.langfuse.com//api/public/otel'
            )
            update.assert_not_called()
            logger.error.assert_called_once_with("The --url argument is required when an api_key is not specified via a config file")
            assert exit_code.value.code == 1

    def test_configure_should_error_if_host_health_uri_missing(self):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger, \
            pytest.raises(SystemExit) as exit_code
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            configure_langfuse(
                api_key='my-key',
            )
            update.assert_not_called()
            logger.error.assert_called_once_with("The --health-url argument is required when a host_health_uri field is not specified via a config file")
            assert exit_code.value.code == 1

    def test_configure_should_set_defaults(self):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            configure_langfuse(
                url='https://cloud.langfuse.com',
                api_key='my-key',
                host_health_uri='https://cloud.langfuse.com//api/public/otel'
            )
            update.assert_called_once()
            logger.info.assert_called_once_with("Langfuse integration updated")
            update.assert_called_once_with(MatchesObjectContaining(
                project_id='default',
                mask_pii=False
            ))

class TestObservabilityPrintToConsole:
    def test_get_should_print_to_console(self, capsys, snapshot):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            get.return_value = AnalyticsLLMConfig(
                project_id='my-project',
                host_uri='host_uri',
                toolIdentifier=AnalyticsLLMUpsertToolIdentifier.LANGFUSE,
                mask_pii=True,
                config_json={},
                active=True
            )
            get_langfuse()
            get.assert_called_once()
            snapshot.assert_match(capsys.readouterr().out)


    def test_get_should_print_to_console_with_extras(self, capsys, snapshot):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            get.return_value = AnalyticsLLMConfig(
                project_id='my-project',
                host_uri='host_uri',
                toolIdentifier=AnalyticsLLMUpsertToolIdentifier.LANGFUSE,
                mask_pii=True,
                config_json={"extra": 3},
                active=True
            )
            get_langfuse()
            get.assert_called_once()
            snapshot.assert_match(capsys.readouterr().out)



    def test_get_should_output_to_yaml(self, snapshot):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger,
            patch('builtins.open', unittest.mock.mock_open()) as o
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            get.return_value = AnalyticsLLMConfig(
                project_id='my-project',
                host_uri='host_uri',
                toolIdentifier=AnalyticsLLMUpsertToolIdentifier.LANGFUSE,
                mask_pii=True,
                config_json={"extra": 3},
                active=True
            )
            get_langfuse(output='my-file.yaml')
            get.assert_called_once()
            logger.info.assert_called_once_with('Langfuse configuration written to my-file.yaml')
            o.assert_called_once_with('my-file.yaml', 'w')
            handle = o()
            methods = handle.write.call_args_list
            output = ''.join([m.args[0] for m in methods])
            snapshot.assert_match(output)




    def test_get_should_output_to_json(self, snapshot):
        with (
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.instantiate_client") as instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command.logger") as logger,
            patch('builtins.open', unittest.mock.mock_open()) as o
        ):
            AnalyticsLLMClientMock, update, delete, get = get_analytics_llm_mock()
            instantiate_client.return_value = AnalyticsLLMClientMock(base_url='')
            get.return_value = AnalyticsLLMConfig(
                project_id='my-project',
                host_uri='host_uri',
                toolIdentifier=AnalyticsLLMUpsertToolIdentifier.LANGFUSE,
                mask_pii=True,
                config_json={"extra": 3},
                active=True
            )
            get_langfuse(output='my-file.json')
            get.assert_called_once()
            logger.info.assert_called_once_with('Langfuse configuration written to my-file.json')
            o.assert_called_once_with('my-file.json', 'w')
            handle = o()
            methods = handle.write.call_args_list
            output = ''.join([m.args[0] for m in methods])
            snapshot.assert_match(output)




