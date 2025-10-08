import logging
import sys
from pathlib import Path

import typer

from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.utils.docker_utils import DockerUtils, WoDockerBlobCacheService, DockerComposeCore
from ibm_watsonx_orchestrate.utils.environment import EnvService, EnvSettingsService
from ibm_watsonx_orchestrate.utils.utils import parse_string_safe


logger = logging.getLogger(__name__)

images_app = typer.Typer(no_args_is_help=True)


@images_app.command(
    name="prune",
    help="Trim CPD docker image layer cache. When set, the system will find and clear CPD docker image layer digest caches which are deemed as not required based on configuration provided in .env file."
)
def server_images_command(
        user_env_file: str = typer.Option(
            None,
            "--env-file", '-e',
            help="Path to a .env file that overrides default.env. Then environment variables override both. Required when not clearing all layers in the CPD docker image layer cache."
        ),
        should_prune_all: bool = typer.Option(
            False,
            "--all", "-a",
            help="Clears all layers in the CPD docker image layer cache."
        )
):
    DockerUtils.ensure_docker_installed()

    user_env_file = parse_string_safe(value=user_env_file, override_empty_to_none=True)
    if user_env_file is not None:
        user_env_file = Path(user_env_file)

        if not user_env_file.exists() or not user_env_file.is_file():
            logger.error(f"Provided .env file does not exist or cannot be accessed: {user_env_file}")
            sys.exit(1)

    if should_prune_all is not True and user_env_file is None:
        logger.error("The system needs to connect to upstream CPD docker registry. Please provide a CPD .env file.")
        sys.exit(1)

    cli_config = Config()
    env_service = EnvService(cli_config)

    if user_env_file is not None:
        user_env = env_service.get_user_env(user_env_file=user_env_file, fallback_to_persisted_env=False)
        merged_env_dict = env_service.prepare_server_env_vars(user_env=user_env, should_drop_auth_routes=False)

    else:
        default_env_path = EnvService.get_default_env_file()
        merged_env_dict = EnvService.merge_env(default_env_path, None)

    merged_env_dict['WATSONX_SPACE_ID'] = 'X'
    merged_env_dict['WATSONX_APIKEY'] = 'X'

    env_service.apply_llm_api_key_defaults(merged_env_dict)
    final_env_file = EnvService.write_merged_env_file(merged_env_dict)

    if should_prune_all:
        try:
            logger.info("Clearing orchestrate docker image layer cache.")
            env_settings = EnvSettingsService(final_env_file)
            blob_cacher = WoDockerBlobCacheService(env_settings=env_settings)
            if blob_cacher.clear_cache():
                logger.info("Orchestrate docker image layer cache cleared.")

            else:
                logger.info("Orchestrate docker image cache layer is already empty.")

        except Exception as ex:
            logger.error(ex)
            logger.error("Failed to clear orchestrate docker image layer cache.")

    else:
        try:
            compose_core = DockerComposeCore(env_service=env_service)
            drop_digest_count = compose_core.trim_cpd_image_layer_cache(final_env_file=final_env_file)

            if drop_digest_count > 0:
                logger.info(f"Cleared {drop_digest_count} digests in Orchestrate CPD docker image layer cache.")

            else:
                logger.info("Found no digests in Orchestrate CPD docker image layer cache which can be cleared.")

        except Exception as ex:
            logger.error(ex)
            logger.error("Failed to trim Orchestrate CPD docker image docker layer cache.")
