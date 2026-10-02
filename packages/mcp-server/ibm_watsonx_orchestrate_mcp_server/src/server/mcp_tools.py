from typing import Optional

from ibm_watsonx_orchestrate.cli.commands.server.server_command import (
    server_start,
    server_stop,
    server_reset,
    server_eject,
)


def start_developer_edition_server(
    env_file: Optional[str] = None,
    accept_terms_and_conditions: bool = False,
    with_doc_processing: bool = False,
    with_voice: bool = False,
    with_langflow: bool = False,
    with_ai_builder: bool = False,
) -> str:
    """
    Start the watsonx Orchestrate Developer Edition local server.
    Equivalent to: orchestrate server start

    Args:
        env_file (str, optional): Path to a .env file that overrides default.env.
        accept_terms_and_conditions (bool): Accept the terms and conditions required to start the server. (default: False)
        with_doc_processing (bool): Enable IBM Document Processing. (default: False)
        with_voice (bool): Enable voice controller. (default: False)
        with_langflow (bool): Enable Langflow UI at http://localhost:7861. (default: False)
        with_ai_builder (bool): Enable AI Builder features. (default: False)

    Returns:
        str: Status message indicating the server has started.
    """
    server_start(
        user_env_file=env_file,
        accept_terms_and_conditions=accept_terms_and_conditions,
        with_doc_processing=with_doc_processing,
        with_voice=with_voice,
        with_langflow=with_langflow,
        with_ai_builder=with_ai_builder,
        experimental_with_langfuse=False,
        experimental_with_ibm_telemetry=False,
        persist_env_secrets=False,
        custom_compose_file=None,
        with_connections_ui=False,
        with_ingestion_from_external_source=False,
        sequential_image_pull=False,
        cert_bundle_path=None,
        service_username=None,
        service_password=None,
    )
    return "Developer Edition server started successfully."


def stop_developer_edition_server(
    env_file: Optional[str] = None,
    keep_vm: bool = False,
) -> str:
    """
    Stop the watsonx Orchestrate Developer Edition local server.
    Equivalent to: orchestrate server stop

    Args:
        env_file (str, optional): Path to a .env file that overrides default.env.
        keep_vm (bool): Keep the underlying VM running after stopping the server. (default: False)

    Returns:
        str: Status message indicating the server has stopped.
    """
    server_stop(
        user_env_file=env_file,
        keep_vm=keep_vm,
    )
    return "Developer Edition server stopped successfully."


def reset_developer_edition_server(
    env_file: Optional[str] = None,
    keep_vm: bool = False,
) -> str:
    """
    Reset the watsonx Orchestrate Developer Edition local server, wiping all data.
    Equivalent to: orchestrate server reset

    Args:
        env_file (str, optional): Path to a .env file that overrides default.env.
        keep_vm (bool): Keep the underlying VM running after the reset. (default: False)

    Returns:
        str: Status message indicating the server has been reset.
    """
    server_reset(
        user_env_file=env_file,
        keep_vm=keep_vm,
    )
    return "Developer Edition server reset successfully."


def eject_developer_edition_server(
    env_file: str,
) -> str:
    """
    Export the docker-compose and env files used to run the Developer Edition server.
    Equivalent to: orchestrate server eject

    Args:
        env_file (str): Path to a .env file that overrides default.env. Required.

    Returns:
        str: Status message indicating the files have been exported.
    """
    server_eject(
        user_env_file=env_file,
    )
    return "Developer Edition server configuration ejected successfully."


__tools__ = [
    start_developer_edition_server,
    stop_developer_edition_server,
    reset_developer_edition_server,
    eject_developer_edition_server,
]
