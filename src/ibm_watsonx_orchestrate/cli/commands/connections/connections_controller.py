import logging
import requests
import json
import rich
import yaml
import sys
import typer

from typing import List
from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.agent_builder.connections.types import (
    ConnectionEnvironment,
    ConnectionConfiguration,
    ConnectionSecurityScheme,
    ConnectionType,
    IdpConfigData,
    IdpConfigDataBody,
    AppConfigData,
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    # OAuth2AuthCodeCredentials,
    OAuth2ClientCredentials,
    # OAuth2ImplicitCredentials,
    # OAuth2PasswordCredentials,
    OAuthOnBehalfOfCredentials,
    KeyValueConnectionCredentials,
    CREDENTIALS,
    IdentityProviderCredentials,
    OAUTH_CONNECTION_TYPES, OAuth2AuthCodeCredentials

)

from ibm_watsonx_orchestrate.client.connections import get_connections_client, get_connection_type

logger = logging.getLogger(__name__)

def _validate_connections_spec_content(content: dict) -> None:
    spec_version = content.get("spec_version")
    kind = content.get("kind")
    app_id = content.get("app_id")
    environments = content.get("environments")

    if not spec_version:
        logger.error("No 'spec_version' found in provided spec file. Please ensure the spec file is in the correct format")
        sys.exit(1)
    if not kind:
        logger.error("No 'kind' found in provided spec file. Please ensure the spec file is in the correct format")
        sys.exit(1)
    if not app_id:
        logger.error("No 'app_id' found in provided spec file. Please ensure the spec file is in the correct format")
        sys.exit(1)
    if not environments or not len(environments):
        logger.error("No 'environments' found in provided spec file. Please ensure the spec file is in the correct format")
        sys.exit(1)
    
    if kind != "connection":
        logger.error("Field 'kind' must have a value of 'connection'. Please ensure the spec file is a valid connection spec.")
        sys.exit(1)

def _create_connection_from_spec(content: dict) -> None:
    if not content:
        logger.error("No spec content provided. Please verify the input file is not empty")
        sys.exit(1)
    
    client = get_connections_client()
    
    _validate_connections_spec_content(content=content)

    app_id = content.get("app_id")
    existing_app = client.get(app_id=app_id)
    if not existing_app:
        add_connection(app_id=app_id)

    environments = content.get("environments")
    for environment in environments:
        if is_local_dev() and environment != ConnectionEnvironment.DRAFT:
            logger.warning(f"Local development does not support any environments other than 'draft'. The provided '{environment}' environment configuration will be ignored.")
            continue
        config = environments.get(environment)
        config["environment"] = environment
        config["app_id"] = app_id
        config = ConnectionConfiguration.model_validate(config)
        add_configuration(config)
    
def _parse_file(file: str) -> None:
    if file.endswith('.yaml') or file.endswith('.yml') or file.endswith(".json"):
        with open(file, 'r') as f:
            if file.endswith(".json"):
                content = json.load(f)
            else:
                content = yaml.load(f, Loader=yaml.SafeLoader)
        _create_connection_from_spec(content=content)
    else:
        raise ValueError("file must end in .json, .yaml or .yml")

def _format_token_headers(header_list: List) -> dict:
    if not header_list or len(header_list) == 0:
        return None
    
    header = dict()
    
    for header_string in header_list:
        split_header = header_string.split(":")
        if len(split_header) != 2:
            logger.error(f"Provided header '{header_string}' is not in the correct format. Please format headers as 'key: value'")
            sys.exit(1)
        header_key, header_value = split_header
        header_key = header_key.strip()
        header_value = header_value.strip()

        header[header_key] = header_value
    
    return header

def _validate_connection_params(type: ConnectionType, **args) -> None:

    if type == ConnectionType.BASIC_AUTH and (
            args.get('username') is None or args.get('password') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --username (-u) and --password (-p) are both required for type {type}"
        )

    if type == ConnectionType.BEARER_TOKEN and (
            args.get('token') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --token is required for type {type}"
        )

    if type == ConnectionType.API_KEY_AUTH and (
            args.get('api_key') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --api-key is required for type {type}"
        )

    if type in {ConnectionType.OAUTH2_CLIENT_CREDS, ConnectionType.OAUTH2_AUTH_CODE} and args.get('client_secret') is None:
        raise typer.BadParameter(
            f"Missing flags --client-secret is required for type {type}"
        )
    
    if type in {ConnectionType.OAUTH2_AUTH_CODE} and args.get('auth_url') is None:
        raise typer.BadParameter(
            f"Missing flags --auth-url is required for type {type}"
        )

    if type in {ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, ConnectionType.OAUTH2_CLIENT_CREDS, ConnectionType.OAUTH2_AUTH_CODE} and (
            args.get('client_id') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --client-id is required for type {type}"
        )
    
    if type in {ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, ConnectionType.OAUTH2_CLIENT_CREDS, ConnectionType.OAUTH2_AUTH_CODE} and (
            args.get('token_url') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --token-url is required for type {type}"
        )


    if type == ConnectionType.OAUTH_ON_BEHALF_OF_FLOW and (
            args.get('grant_type') is None
    ):
        raise typer.BadParameter(
            f"Missing flags --grant-type is required for type {type}"
        )

def _parse_entry(entry: str) -> dict[str,str]:
    split_entry = entry.split('=')
    if len(split_entry) != 2:
        message = f"The entry '{entry}' is not in the expected form '<key>=<value>'"
        logger.error(message)
        exit(1)
    return {split_entry[0]: split_entry[1]}

def _get_credentials(type: ConnectionType, **kwargs):
    match type:
        case ConnectionType.BASIC_AUTH:
            return BasicAuthCredentials(
                username=kwargs.get("username"),
                password=kwargs.get("password")
            )
        case ConnectionType.BEARER_TOKEN:
            return BearerTokenAuthCredentials(
                token=kwargs.get("token")
            )
        case ConnectionType.API_KEY_AUTH:
            return APIKeyAuthCredentials(
                api_key=kwargs.get("api_key")
            )
        case ConnectionType.OAUTH2_AUTH_CODE:
            return OAuth2AuthCodeCredentials(
                authorization_url=kwargs.get("auth_url"),
                client_id=kwargs.get("client_id"),
                client_secret=kwargs.get("client_secret"),
                token_url=kwargs.get("token_url"),
                scopes=kwargs.get("scopes")
            )
        case ConnectionType.OAUTH2_CLIENT_CREDS:
            return OAuth2ClientCredentials(
                client_id=kwargs.get("client_id"),
                client_secret=kwargs.get("client_secret"),
                token_url=kwargs.get("token_url"),
                scopes=kwargs.get("scopes")
            )
        # case ConnectionType.OAUTH2_IMPLICIT:
        #     return OAuth2ImplicitCredentials(
        #         authorization_url=kwargs.get("auth_url"),
        #         client_id=kwargs.get("client_id"),
        #     )
        # case ConnectionType.OAUTH2_PASSWORD:
        #     return OAuth2PasswordCredentials(
        #         authorization_url=kwargs.get("auth_url"),
        #         client_id=kwargs.get("client_id"),
        #         client_secret=kwargs.get("client_secret"),
        #         token_url=kwargs.get("token_url")
        #     )
        case ConnectionType.OAUTH_ON_BEHALF_OF_FLOW:
            return OAuthOnBehalfOfCredentials(
                client_id=kwargs.get("client_id"),
                access_token_url=kwargs.get("token_url"),
                grant_type=kwargs.get("grant_type")
            )
        case ConnectionType.KEY_VALUE:
            env = {}
            for entry in kwargs.get('entries', []):
                env.update(_parse_entry(entry))

            return KeyValueConnectionCredentials(
                env
            )
        case _:
            raise ValueError(f"Invalid type '{type}' selected")


def add_configuration(config: ConnectionConfiguration) -> None:
    client = get_connections_client()
    app_id = config.app_id
    environment = config.environment

    try:
        existing_configuration = client.get_config(app_id=app_id, env=environment)
        if existing_configuration:
            logger.info(f"Existing connection '{app_id}' with environment '{environment}' found. Updating configuration")
            should_delete_credentials = False

            if existing_configuration.security_scheme != config.security_scheme:
                should_delete_credentials = True
                logger.warning(f"Detected a change in auth type from '{existing_configuration.security_scheme}' to '{config.security_scheme}'. The associated credentials will be removed.")
            elif existing_configuration.auth_type != config.auth_type:
                should_delete_credentials = True
                logger.warning(f"Detected a change in oauth flow from '{existing_configuration.auth_type}' to '{config.auth_type}'. The associated credentials will be removed.")
            elif existing_configuration.preference != config.preference:
                should_delete_credentials = True
                logger.warning(f"Detected a change in preference/type from '{existing_configuration.preference}' to '{config.preference}'. The associated credentials will be removed.")
            elif existing_configuration.sso != config.sso:
                logger.warning(f"Detected a change in sso from '{existing_configuration.sso}' to '{config.sso}'. The associated credentials will be removed.")
                should_delete_credentials = True

            existing_conn_type = get_connection_type(security_scheme=existing_configuration.security_scheme, auth_type=existing_configuration.auth_type)
            use_app_credentials = existing_conn_type in OAUTH_CONNECTION_TYPES

            if should_delete_credentials:
                try:
                    existing_credentials = client.get_credentials(app_id=app_id, env=environment, use_app_credentials=use_app_credentials)
                    if existing_credentials:
                        client.delete_credentials(app_id=app_id, env=environment, use_app_credentials=use_app_credentials)
                except:
                    logger.error(f"Error removing credentials for connection '{app_id}' in environment '{environment}'. No changes have been made to the configuration.")
                    sys.exit(1)
            
            client.update_config(app_id=app_id, env=environment, payload=config.model_dump(exclude_none=True))
            logger.info(f"Configuration successfully updated for '{environment}' environment of connection '{app_id}'.")
        else:
            logger.info(f"Creating configuration for connection '{app_id}' in the '{environment}' environment")
            client.create_config(app_id=app_id, payload=config.model_dump())
            logger.info(f"Configuration successfully created for '{environment}' environment of connection '{app_id}'.")

    except requests.HTTPError as e:
        response = e.response
        response_text = response.text
        logger.error(response_text)
        exit(1)

def add_credentials(app_id: str, environment: ConnectionEnvironment, use_app_credentials: bool, credentials: CREDENTIALS) -> None:
    client = get_connections_client()
    try:
        existing_credentials = client.get_credentials(app_id=app_id, env=environment, use_app_credentials=use_app_credentials)
        if use_app_credentials:
            payload = {
                "app_credentials": credentials.model_dump(exclude_none=True)
            }
        else:
            payload = {
                "runtime_credentials": credentials.model_dump(exclude_none=True)
            }
        
        logger.info(f"Setting credentials for environment '{environment}' on connection '{app_id}'")
        if existing_credentials:
            client.update_credentials(app_id=app_id, env=environment, use_app_credentials=use_app_credentials, payload=payload)
        else:
            client.create_credentials(app_id=app_id,env=environment, use_app_credentials=use_app_credentials, payload=payload)
        logger.info(f"Credentials successfully set for '{environment}' environment of connection '{app_id}'")
    except requests.HTTPError as e:
        response = e.response
        response_text = response.text
        logger.error(response_text)
        exit(1)

def add_identity_provider(app_id: str, environment: ConnectionEnvironment, idp: IdentityProviderCredentials):
    client = get_connections_client()

    try:
        existing_credentials = client.get_credentials(app_id=app_id, env=environment, use_app_credentials=True)
        
        payload = {
            "idp_credentials": idp.model_dump()
        }

        logger.info(f"Setting identity provider for environment '{environment}' on connection '{app_id}'")
        if existing_credentials:
            client.update_credentials(app_id=app_id, env=environment, use_app_credentials=True, payload=payload)
        else:
            client.create_credentials(app_id=app_id,env=environment, use_app_credentials=True, payload=payload)
        logger.info(f"Identity provider successfully set for '{environment}' environment of connection '{app_id}'")
    except requests.HTTPError as e:
        response = e.response
        response_text = response.text
        logger.error(response_text)
        exit(1)

def add_connection(app_id: str) -> None:
    client = get_connections_client()

    try:
        logger.info(f"Creating connection '{app_id}'")
        request = {"app_id": app_id}
        client.create(payload=request)
        logger.info(f"Successfully created connection '{app_id}'")
    except requests.HTTPError as e:
        response = e.response
        response_text = response.text
        status_code = response.status_code
        try:
            if status_code == 409:
                response_text = f"Failed to create connection. A connection with the App ID '{app_id}' already exists. Please select a different App ID or delete the existing resource."
            else:
                resp = json.loads(response_text)
                response_text = resp.get('detail')
        except:
            pass
        logger.error(response_text)
        exit(1)

def remove_connection(app_id: str) -> None:
    client = get_connections_client()

    try:
        logger.info(f"Removing connection '{app_id}'")
        client.delete(app_id=app_id)
        logger.info(f"Connection '{app_id}' successfully removed")
    except requests.HTTPError as e:
        response = e.response
        response_text = response.text
        logger.error(response_text)
        exit(1)

def list_connections(environment: ConnectionEnvironment | None, verbose: bool = False) -> None:
    client = get_connections_client()
    connections = client.list()
    is_local = is_local_dev()

    if verbose:
        connections_list = []
        for conn in connections:
            if is_local and  conn.environment == ConnectionEnvironment.LIVE:
                continue
            connections_list.append(json.loads(conn.model_dump_json()))

        rich.print_json(json.dumps(connections_list, indent=4))
    else:
        non_configured_table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True, title="*Non-Configured")
        draft_table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True, title="Draft")
        live_table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True, title="Live")
        default_args = {"justify": "center", "no_wrap": True}
        column_args = {
            "App ID": {"overflow": "fold"}, 
            "Auth Type": {}, 
            "Type": {}, 
            "Credentials Set/ Connected": {}
        }
        for column in column_args:
            draft_table.add_column(column,**default_args, **column_args[column])
            live_table.add_column(column,**default_args, **column_args[column])
            non_configured_table.add_column(column,**default_args, **column_args[column])
        
        for conn in connections:
            if conn.environment is None:
                non_configured_table.add_row(
                    conn.app_id,
                    "n/a",
                    "n/a",
                    "❌"
                )
                continue

            connection_type = get_connection_type(security_scheme=conn.security_scheme, auth_type=conn.auth_type)

            if conn.environment == ConnectionEnvironment.DRAFT:
                draft_table.add_row(
                    conn.app_id,
                    connection_type,
                    conn.preference,
                    "✅" if conn.credentials_entered else "❌"
                )
            elif conn.environment == ConnectionEnvironment.LIVE and not is_local:
                live_table.add_row(
                    conn.app_id,
                    connection_type,
                    conn.preference,
                    "✅" if conn.credentials_entered else "❌"
                )
        if environment is None and len(non_configured_table.rows):
            rich.print(non_configured_table)
        if environment == ConnectionEnvironment.DRAFT or (environment == None and len(draft_table.rows)):
            rich.print(draft_table)
        if environment == ConnectionEnvironment.LIVE or (environment == None and len(live_table.rows)):
            rich.print(live_table)
        if environment == None and not len(draft_table.rows) and not len(live_table.rows) and not len(non_configured_table.rows):
            logger.info("No connections found. You can create connections using `orchestrate connections add`")

def import_connection(file: str) -> None:
    _parse_file(file=file)

def configure_connection(**kwargs) -> None:
    if is_local_dev() and kwargs.get("environment") != ConnectionEnvironment.DRAFT:
        logger.error(f"Cannot create configuration for environment '{kwargs.get('environment')}'. Local development does not support any environments other than 'draft'.")
        sys.exit(1)

    
    idp_config_body = None
    if kwargs.get("idp_token_type") or kwargs.get("idp_token_use"):
        idp_config_body = IdpConfigDataBody(
                requested_token_type=kwargs.get("idp_token_type"),
                requested_token_use=kwargs.get("idp_token_use")
        )
    

    idp_config_data = None
    if idp_config_body or kwargs.get("idp_token_header"):
        idp_config_data = IdpConfigData(
            header=_format_token_headers(kwargs.get("idp_token_header")),
            body=idp_config_body
        )

    app_config_data = AppConfigData() if kwargs.get("sso", False) else None
    if kwargs.get("app_token_header"):
        app_config_data = AppConfigData(
            header=_format_token_headers(kwargs.get("app_token_header"))
        )

    kwargs["idp_config_data"] = idp_config_data
    kwargs["app_config_data"] = app_config_data

    config = ConnectionConfiguration.model_validate(kwargs)

    add_configuration(config)

def set_credentials_connection(
    app_id: str,
    environment: ConnectionEnvironment,
    **kwargs
) -> None:
    client = get_connections_client()

    config = client.get_config(app_id=app_id, env=environment)
    if not config:
        logger.error(f"No configuration '{environment}' found for connection '{app_id}'. Please create the connection using `orchestrate connections add --app-id {app_id}` then add a configuration `orchestrate connections configure --app-id {app_id} --environment {environment} ...`")
        sys.exit(1)

    sso_enabled = config.sso
    conn_type = get_connection_type(security_scheme=config.security_scheme, auth_type=config.auth_type)
    use_app_credentials = conn_type in OAUTH_CONNECTION_TYPES

    _validate_connection_params(type=conn_type, **kwargs)
    credentials = _get_credentials(type=conn_type, **kwargs)

    add_credentials(app_id=app_id, environment=environment, use_app_credentials=use_app_credentials, credentials=credentials)

def set_identity_provider_connection(
    app_id: str,
    environment: ConnectionEnvironment,
    **kwargs
) -> None:
    client = get_connections_client()

    config = client.get_config(app_id=app_id, env=environment)
    if not config:
        logger.error(f"No configuration '{environment}' found for connection '{app_id}'. Please create the connection using `orchestrate connections add --app-id {app_id}` then add a configuration `orchestrate connections configure --app-id {app_id} --environment {environment} ...`")
        sys.exit(1)

    sso_enabled = config.sso
    security_scheme = config.security_scheme

    if security_scheme != ConnectionSecurityScheme.OAUTH2:
        logger.error(f"Identity providers cannot be set for non-OAuth connection types. The connections specified is of type '{security_scheme}'")
        sys.exit(1)

    if not sso_enabled:
        logger.error(f"Cannot set Identity Provider when 'sso' is false in configuration. Please enable sso for connection '{app_id}' in environment '{environment}' and try again.")
        sys.exit(1)

    idp = IdentityProviderCredentials.model_validate(kwargs)
    add_identity_provider(app_id=app_id, environment=environment, idp=idp)
