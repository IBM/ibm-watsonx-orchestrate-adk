import yaml
import json
import logging
from typing import Annotated
from json import loads

import typer
from yaml.representer import Representer

from ibm_watsonx_orchestrate.agent_builder.agents import SpecVersion
from ibm_watsonx_orchestrate.client.analytics.llm.analytics_llm_client import AnalyticsLLMClient, AnalyticsLLMConfig, \
    AnalyticsLLMResponse
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.utils.file_manager import safe_open

settings_observability_langfuse_app = typer.Typer(no_args_is_help=True)

logger = logging.getLogger(__name__)

def _validate_langfuse_input(**kwargs) -> AnalyticsLLMConfig:
    config = {}
    if kwargs['config_file'] is not None:
        file = kwargs['config_file']
        with safe_open(file, 'r') as fp:
            if file.endswith('.yaml') or file.endswith('.yml'):
                content = yaml_safe_load(fp)
            elif file.endswith('.json'):
                content = json.load(fp)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

        config.update(content)

    keys = ['url', 'project_id', 'api_key', 'mask_pii', 'kind', 'spec_version', 'host_health_uri']
    for key in keys:
        if kwargs.get(key) is not None:
            config[key] = kwargs[key]

    if config.get('project_id') is None:
        logger.warning('The --project-id was not specified, defaulting to "default"')

    if config.get('api_key', None) is None:
        logger.error(f"The --api-key argument is required when an api_key is not specified via a config file")
        exit(1)

    if config.get('url', None) is None:
        logger.error(f"The --url argument is required when a url field is not specified via a config file")
        exit(1)
    
    if config.get('host_health_uri', None) is None:
        logger.error(f"The --health-url argument is required when a host_health_uri field is not specified via a config file")
        exit(1)

    if kwargs.get('config_json'):
        config["config_json"] = kwargs["config_json"]

    res = AnalyticsLLMConfig(
        project_id=config.get('project_id', 'default'),
        host_uri=config.get('url'),
        api_key=config.get('api_key'),
        tool_identifier="langfuse",
        mask_pii=config.get('mask_pii', False),
        config_json=config.get("config_json", {}),
        host_health_uri=config.get('host_health_uri')
    )

    return res


def _reformat_output(cfg: AnalyticsLLMConfig) -> dict:
    config = {}
    config['spec_version'] = str(SpecVersion.V1.value)
    config['kind'] = 'langfuse'
    config['active'] = cfg.active
    config['mask_pii'] = cfg.mask_pii
    if cfg.config_json:
        config.update(cfg.config_json)

    return config

@settings_observability_langfuse_app.command(name="get", help="Get the current configuration settings for langfuse")
def get_langfuse(
    output: Annotated[
        str,
        typer.Option("--output", "-o",
                     help="File to output the results to (file extension can be either .yml, .yaml, or .json)"),
    ] = None,
):
    client: AnalyticsLLMClient = instantiate_client(AnalyticsLLMClient)
    config = _reformat_output(client.get())

    if output:
        with safe_open(output, 'w') as f:
            if output.endswith('.yaml') or output.endswith('.yml'):
                yaml.safe_dump(config, f, sort_keys=False)
                logger.info(f"Langfuse configuration written to {output}")
            elif output.endswith('.json'):
                json.dump(config, f, indent=2)
                logger.info(f"Langfuse configuration written to {output}")
            else:
                raise ValueError('--output file must end in .json, .yaml, or .yml')
    else:
        print(yaml.safe_dump(config, sort_keys=False))



@settings_observability_langfuse_app.command(name="configure", help='Configure an integration with langfuse')
def configure_langfuse(
        url: Annotated[
            str,
            typer.Option("--url", "-u",
                         help="URL of the langfuse instance (required if not specified in --config-file)"
            ),
        ] = None,
        host_health_uri: Annotated[
            str,
            typer.Option("--health-uri",
                         help="Health URI of the langfuse instance (required if not specified in --config-file)"
            ),
        ] = None,
        project_id: Annotated[
            str,
            typer.Option(
                        "--project-id", "-p",
                         help="The langfuse project id (required if not specified in --config-file)"
            )
        ] = None,
        api_key: Annotated[
            str,
            typer.Option("--api-key", help="The langfuse api key (required if not specified in --config-file)"),
        ] = None,
        mask_pii: Annotated[  # not currently supported by the runtime
            bool,
            typer.Option(
                        "--mask-pii",
                            help="Whether or not PII should be masked from traces before sending them to langfuse",
                            hidden=True
                         ),
        ] = None,
        config_file: Annotated[
            str,
            typer.Option('--config-file',
                         help="A config file for the langfuse integration (can be fetched using orchestrate settings )")
        ] = None,
        config_json: Annotated[
            str,
            typer.Option('--config-json',
                         help="A config json object for the langfuse integration")
        ] = None
):
    config_json_dict = json.loads(config_json) if config_json else {}
    client: AnalyticsLLMClient = instantiate_client(AnalyticsLLMClient)
    config = _validate_langfuse_input(
        url=url,
        project_id=project_id,
        tool_identifier='langfuse',
        api_key=api_key,
        mask_pii=mask_pii,
        config_file=config_file,
        host_health_uri=host_health_uri,
        config_json=config_json_dict
    )

    try:
        client.update(config)
        logger.info(f"Langfuse integration updated")
    except ClientAPIException as e:
        logger.error(f"Failed to update langfuse integration")
        logger.error(AnalyticsLLMResponse.model_validate(e.response.text).status)
        parsed_error = loads(e.response.text)
        logger.error(AnalyticsLLMResponse.model_validate(parsed_error).status)



