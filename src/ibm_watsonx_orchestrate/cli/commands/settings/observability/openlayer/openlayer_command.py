import yaml
import json
import logging
from typing import Annotated
from json import loads

import typer

from ibm_watsonx_orchestrate_core.types.spec.types import SpecVersion
from ibm_watsonx_orchestrate.client.analytics.llm.analytics_llm_client import AnalyticsLLMClient, AnalyticsLLMConfig, \
    AnalyticsLLMResponse
from ibm_watsonx_orchestrate_clients.common.utils import instantiate_client, handle_error
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.utils.file_manager import safe_open

settings_observability_openlayer_app = typer.Typer(no_args_is_help=True)

logger = logging.getLogger(__name__)

# Openlayer's OTLP ingest endpoint and API host are well-known, so unlike the
# langfuse integration we default them and only require --api-key/--pipeline-id.
DEFAULT_OPENLAYER_OTLP_URL = "https://api.openlayer.com/v1/otel/v1/traces"
DEFAULT_OPENLAYER_HEALTH_URI = "https://api.openlayer.com"


def _validate_openlayer_input(**kwargs) -> AnalyticsLLMConfig:
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

    keys = ['url', 'project_id', 'api_key', 'pipeline_id', 'mask_pii', 'kind', 'spec_version', 'host_health_uri']
    for key in keys:
        if kwargs.get(key) is not None:
            config[key] = kwargs[key]

    # The pipeline id is non-secret routing data; the runtime maps it onto the
    # Openlayer `x-bt-parent: pipeline_id:<id>` header, so it travels in
    # config_json. Accept it from the --pipeline-id flag, a top-level
    # `pipeline_id` field, or a nested `config_json.pipeline_id` (round-trip).
    config_json = {}
    if isinstance(config.get('config_json'), dict):
        config_json.update(config['config_json'])
    if kwargs.get('config_json'):
        config_json.update(kwargs['config_json'])
    pipeline_id = config.get('pipeline_id') or config_json.get('pipeline_id')

    # Openlayer's endpoint is well-known; default it when not provided.
    if config.get('url') is None:
        config['url'] = DEFAULT_OPENLAYER_OTLP_URL
    if config.get('host_health_uri') is None:
        config['host_health_uri'] = DEFAULT_OPENLAYER_HEALTH_URI

    if config.get('project_id') is None:
        logger.warning('The --project-id was not specified, defaulting to "default"')

    if config.get('api_key', None) is None:
        logger.error("The --api-key argument is required when an api_key is not specified via a config file")
        exit(1)

    if pipeline_id is None:
        logger.error("The --pipeline-id argument is required when a pipeline_id is not specified via a config file")
        exit(1)

    config_json['pipeline_id'] = pipeline_id

    res = AnalyticsLLMConfig(
        project_id=config.get('project_id', 'default'),
        host_uri=config.get('url'),
        api_key=config.get('api_key'),
        tool_identifier="openlayer",
        mask_pii=config.get('mask_pii', False),
        config_json=config_json,
        host_health_uri=config.get('host_health_uri')
    )

    return res


def _reformat_output(cfg: AnalyticsLLMConfig) -> dict:
    config = {}
    config['spec_version'] = str(SpecVersion.V1.value)
    config['kind'] = 'openlayer'
    config['active'] = cfg.active
    config['mask_pii'] = cfg.mask_pii
    if cfg.config_json:
        config.update(cfg.config_json)

    return config


@settings_observability_openlayer_app.command(name="get", help="Get the current configuration settings for openlayer")
def get_openlayer(
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
                logger.info(f"Openlayer configuration written to {output}")
            elif output.endswith('.json'):
                json.dump(config, f, indent=2)
                logger.info(f"Openlayer configuration written to {output}")
            else:
                raise ValueError('--output file must end in .json, .yaml, or .yml')
    else:
        print(yaml.safe_dump(config, sort_keys=False))


@settings_observability_openlayer_app.command(name="configure", help='Configure an integration with openlayer')
def configure_openlayer(
        api_key: Annotated[
            str,
            typer.Option("--api-key", help="The Openlayer API key, used as the OTLP Bearer token (required if not specified in --config-file)"),
        ] = None,
        pipeline_id: Annotated[
            str,
            typer.Option(
                        "--pipeline-id", "-P",
                         help="The Openlayer inference pipeline id traces are routed to (required if not specified in --config-file)"
            )
        ] = None,
        url: Annotated[
            str,
            typer.Option("--url", "-u",
                         help=f"OTLP ingest endpoint of the Openlayer instance (defaults to {DEFAULT_OPENLAYER_OTLP_URL})"
            ),
        ] = None,
        host_health_uri: Annotated[
            str,
            typer.Option("--health-uri",
                         help=f"Health URI of the Openlayer instance (defaults to {DEFAULT_OPENLAYER_HEALTH_URI})"
            ),
        ] = None,
        project_id: Annotated[
            str,
            typer.Option(
                        "--project-id", "-p",
                         help="The project id label to associate with the configuration"
            )
        ] = None,
        mask_pii: Annotated[  # not currently supported by the runtime
            bool,
            typer.Option(
                        "--mask-pii",
                            help="Whether or not PII should be masked from traces before sending them to openlayer",
                            hidden=True
                         ),
        ] = None,
        config_file: Annotated[
            str,
            typer.Option('--config-file',
                         help="A config file for the openlayer integration (can be fetched using orchestrate settings )")
        ] = None,
        config_json: Annotated[
            str,
            typer.Option('--config-json',
                         help="A config json object for the openlayer integration")
        ] = None
):
    config_json_dict = json.loads(config_json) if config_json else {}
    client: AnalyticsLLMClient = instantiate_client(AnalyticsLLMClient)
    config = _validate_openlayer_input(
        url=url,
        project_id=project_id,
        tool_identifier='openlayer',
        api_key=api_key,
        pipeline_id=pipeline_id,
        mask_pii=mask_pii,
        config_file=config_file,
        host_health_uri=host_health_uri,
        config_json=config_json_dict
    )

    try:
        client.update(config)
        logger.info(f"Openlayer integration updated")
    except ClientAPIException as e:
        logger.error("Failed to update openlayer integration")
        try:
            parsed_error = loads(e.response.text)
        except Exception:
            parsed_error = None
        # The backend returns {"status": ...} on a handled failure, but FastAPI
        # request validation (e.g. an unsupported tool_identifier) returns
        # {"detail": [...]}. Handle both so the CLI surfaces a useful message.
        if isinstance(parsed_error, dict) and 'status' in parsed_error:
            logger.error(AnalyticsLLMResponse.model_validate(parsed_error).status)
        elif isinstance(parsed_error, dict) and 'detail' in parsed_error:
            logger.error(parsed_error['detail'])
        else:
            logger.error(e.response.text)


@settings_observability_openlayer_app.command(name="remove", help="Remove the current configuration settings for openlayer")
def remove_openlayer_config():
    client: AnalyticsLLMClient = instantiate_client(AnalyticsLLMClient)
    try:
        client.delete()
    except Exception as e:
        handle_error("An error occured while attempting to remove the Openlayer configuration.", e)
    logger.info("Successfully removed Openlayer configuration")
