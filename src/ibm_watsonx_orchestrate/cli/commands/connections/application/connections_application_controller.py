import json
from rich.table import Table
from rich.console import Console
import logging

import requests
import typer

from ibm_watsonx_orchestrate.client.connections import CreateBasicAuthConnection, BasicAuthCredentials, ConnectionType, \
    BearerTokenAuthCredentials, CreateBearerTokenAuthConnection, APIKeyAuthCredentials, CreateAPIKeyAuthConnection, \
    OAuth2AuthCodeCredentials, CreateOAuth2AuthCodeConnection, CreateOAuth2ImplicitConnection, \
    OAuth2ImplicitCredentials, OAuth2ClientCredentials, CreateOAuth2ClientCredentialsConnection, \
    CreateOAuth2PasswordConnection, OAuth2PasswordCredentials, ApplicationConnectionsClient, CreateConnectionResponse, CreateKeyValueConnection, KeyValueConnectionCredentials
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.cli.commands.connections.application.types import ApplicationConnectionType
from ibm_watsonx_orchestrate.utils.request import BadRequest

logger = logging.getLogger(__name__)

_outh_connection_types = {
    ApplicationConnectionType.oauth_auth_code_flow,
    ApplicationConnectionType.oauth_auth_implicit_flow,
    ApplicationConnectionType.oauth_auth_password_flow,
    ApplicationConnectionType.oauth_auth_client_credentials_flow
}

def _parse_entry(entry: str) -> dict[str,str]:
    split_entry = entry.split('=')
    if len(split_entry) != 2:
        message = f"The entry '{entry}' is not in the expected form '<key>=<value>'"
        logger.error(message)
        exit(1)
    return {split_entry[0]: split_entry[1]}


def _validate_create_params(type: ApplicationConnectionType, **args) -> None:
    if type in {ApplicationConnectionType.basic, ApplicationConnectionType.oauth_auth_password_flow} and (
            args.get('username') is None or args.get('password') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --username (-u) and --password (-p) are both required for type {type}"
        )

    if type == ApplicationConnectionType.bearer and (
            args.get('token') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --token is required for type {type}"
        )

    if type == ApplicationConnectionType.api_key and (
            args.get('api_key') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --api-key is required for type {type}"
        )

    if type in _outh_connection_types and args.get('client_id') is None:
        raise typer.BadParameter(
            f"Missing flags --client-id is required for type {type}"
        )

    if type in _outh_connection_types and args.get('client_secret') is None:
        raise typer.BadParameter(
            f"Missing flags --client-secret is required for type {type}"
        )

    if type in _outh_connection_types and args.get('well_known_url') is None:
        raise typer.BadParameter(
            f"Missing flags --well-known-url is required for type {type}"
        )


def _get_connection(type: ApplicationConnectionType, **args):
    match type:
        case ApplicationConnectionType.basic:
            conn = CreateBasicAuthConnection(
                appid=args.get('app_id'),
                shared=args.get('shared'),
                connection_type=ConnectionType.BASIC_AUTH,
                credentials=BasicAuthCredentials(
                    username=args.get('username'),
                    password=args.get('password')
                )
            )
        case ApplicationConnectionType.bearer:
            conn = CreateBearerTokenAuthConnection(
                appid=args.get('app_id'),
                shared=args.get('shared'),
                connection_type=ConnectionType.BEARER_TOKEN,
                credentials=BearerTokenAuthCredentials(
                    token=args.get('token')
                )
            )
        case ApplicationConnectionType.api_key:
            conn = CreateAPIKeyAuthConnection(
                appid=args.get('app_id'),
                shared=args.get('shared'),
                connection_type=ConnectionType.API_KEY_AUTH,
                credentials=APIKeyAuthCredentials(
                    api_key=args.get('api_key')
                )
            )
        case ApplicationConnectionType.oauth_auth_code_flow:
            conn = CreateOAuth2AuthCodeConnection(
                appid=args.get('app_id'),
                shared=args.get('shared'),
                connection_type=ConnectionType.OAUTH2_AUTH_CODE,
                credentials=OAuth2AuthCodeCredentials(
                    client_id=args.get('client_id'),
                    client_secret=args.get('client_secret'),
                    well_known_url=args.get('well_known_url')
                )
            )
        case ApplicationConnectionType.oauth_auth_implicit_flow:
            conn = CreateOAuth2ImplicitConnection(
                appid=args.get('app_id'),
                shared=args.get('shared'),
                connection_type=ConnectionType.OAUTH2_IMPLICIT,
                credentials=OAuth2ImplicitCredentials(
                    client_id=args.get('client_id'),
                    client_secret=args.get('client_secret'),
                    well_known_url=args.get('well_known_url')
                )
            )
        case ApplicationConnectionType.oauth_auth_password_flow:
            conn = CreateOAuth2PasswordConnection(
                appid=args.get('app_id'),
                shared=args.get('shared'),
                connection_type=ConnectionType.OAUTH2_PASSWORD,
                credentials=OAuth2PasswordCredentials(
                    client_id=args.get('client_id'),
                    client_secret=args.get('client_secret'),
                    username=args.get('username'),
                    password=args.get('password'),
                    well_known_url=args.get('well_known_url')
                )
            )
        case ApplicationConnectionType.oauth_auth_client_credentials_flow:
            conn = CreateOAuth2ClientCredentialsConnection(
                appid=args.get('app_id'),
                shared=args.get('shared'),
                connection_type=ConnectionType.OAUTH2_CLIENT_CREDS,
                credentials=OAuth2ClientCredentials(
                    client_id=args.get('client_id'),
                    client_secret=args.get('client_secret'),
                    well_known_url=args.get('well_known_url')
                )
            )
        case ApplicationConnectionType.key_value | ApplicationConnectionType.kv:
            env = {}
            for entry in args.get('entries', []):
                env.update(_parse_entry(entry))

            conn = CreateKeyValueConnection(
                appid=args.get('app_id'),
                shared=args.get('shared'),
                connection_type=ConnectionType.KEY_VALUE,
                credentials=KeyValueConnectionCredentials(env)
            )
        case _:
            raise BadRequest(f"Invalid type {type} selected")
    return conn


def create_application_connection(type: ApplicationConnectionType, **kwargs):
    _validate_create_params(type, **kwargs)
    conn = _get_connection(type, **kwargs)
    client = instantiate_client(ApplicationConnectionsClient)

    try:
        resp: CreateConnectionResponse = client.create(connection=conn)
        if resp.status == 'redirect':
            logger.info(f"Please go to the following url to complete the OAuth2 flow:\n{resp.authorization_url}")
        elif resp.status == 'success':
            logger.info(f"Successfully created application connection with app-id: {conn.appid}")
        else:
            logger.warning(f"Unexpected response status {resp.status}")
    except requests.HTTPError as e:
        response = e.response
        response_text = response.text
        status_code = response.status_code
        try:
            # Remove when we are able to upsert connection details
            if status_code == 409:
                response_text = f"Failed to create connection. A connection with the App ID '{conn.appid}' already exists. Please select a diffrent App ID or delete the existing resource."
            else:
                resp = json.loads(response_text)
                response_text = resp['detail']
        except:
            pass
        logger.error(response_text)
        exit(1)


def remove_application_connection(app_id: str):
    client: ApplicationConnectionsClient = instantiate_client(ApplicationConnectionsClient)
    try:
        existing = client.get_draft_by_app_id(app_id=app_id)
        if len(existing) == 0:
            logger.error(f"Connection with app-id: {app_id} not found")
            exit(1)
        elif len(existing) > 1:
            logger.error(f"Internal error, ambiguious request, multiple Connection IDs found for app-id {', '.join(list(map(lambda e: e.connection_id, existing)))}")
            exit(1)

        client.delete(connection_id=existing[0].connection_id)
        logger.info(f"Successfully removed application connection with app-id: {app_id}")
    except requests.HTTPError as e:
        logger.error(e.response.text)
        exit(1)

def list_application_connections():
    client = instantiate_client(ApplicationConnectionsClient)

    table = Table(show_header=True, header_style="bold white", show_lines=True)
    columns = ["App ID", "Connection Type", "Shared", "Connected", "Connection ID"]
    for column in columns:
        table.add_column(column)

    try:
        connections = client.get()

        for conn in connections:
            table.add_row(
                conn.appid,
                conn.connection_type,
                str(conn.shared),
                str(conn.is_connected),
                conn.connection_id
            )

        
        Console().print(table)

    except requests.HTTPError as e:
        if e.response.status_code == 404 and "Connections not found" in e.response.text:
                Console().print(table)
        else:
            logger.error(e.response.text)
        exit(1)
