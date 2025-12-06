import os
import logging
from copy import deepcopy
from typing import List
from ibm_watsonx_orchestrate.agent_builder.connections.types import (
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2TokenCredentials,
    KeyValueConnectionCredentials,
    ConnectionType,
    ConnectionSecurityScheme,
    CREDENTIALS,
    CONNECTION_TYPE_CREDENTIAL_MAPPING
)

from ibm_watsonx_orchestrate.utils.utils import sanitize_app_id
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)

_PREFIX_TEMPLATE = "WXO_CONNECTION_{app_id}_"

connection_type_requirements_mapping = {
    BasicAuthCredentials: ["username", "password"],
    BearerTokenAuthCredentials: ["token"],
    APIKeyAuthCredentials: ["api_key"],
    OAuth2TokenCredentials: ["access_token"],
    KeyValueConnectionCredentials: None
}

connection_type_security_schema_map = {
    ConnectionType.API_KEY_AUTH: ConnectionSecurityScheme.API_KEY_AUTH,
    ConnectionType.BASIC_AUTH: ConnectionSecurityScheme.BASIC_AUTH,
    ConnectionType.BEARER_TOKEN: ConnectionSecurityScheme.BEARER_TOKEN,
    ConnectionType.KEY_VALUE: ConnectionSecurityScheme.KEY_VALUE,
    ConnectionType.OAUTH2_AUTH_CODE: ConnectionSecurityScheme.OAUTH2,
    ConnectionType.OAUTH2_CLIENT_CREDS: ConnectionSecurityScheme.OAUTH2,
    ConnectionType.OAUTH_ON_BEHALF_OF_FLOW: ConnectionSecurityScheme.OAUTH2,
    # ConnectionType.OAUTH2_IMPLICIT: ConnectionSecurityScheme.OAUTH2,
    ConnectionType.OAUTH2_PASSWORD: ConnectionSecurityScheme.OAUTH2,
    ConnectionType.OAUTH2_TOKEN_EXCHANGE: ConnectionSecurityScheme.OAUTH2
}

def _clean_env_vars(vars: dict[str:str], requirements: List[str], app_id: str) -> dict[str,str]:
    base_prefix = _PREFIX_TEMPLATE.format(app_id=app_id)

    required_env_vars = {}
    missing_requirements = []
    for requirement in requirements:
        key = base_prefix + requirement
        value = vars.get(key)
        if value:
            required_env_vars[key] = value
        else:
            missing_requirements.append(key)
    
    # Get value from optional url env var
    key = base_prefix + "url"
    value = vars.get(key)
    required_env_vars[key] = value
    
    if len(missing_requirements) > 0:
        missing_requirements_str = ", ".join(missing_requirements)
        message = f"Missing requirement environment variables '{missing_requirements_str}' for connection '{app_id}'"
        logger.error(message)
        raise BadRequest(message)
    
    return required_env_vars

def _build_credentials_model(credentials_type: type[CREDENTIALS], vars: dict[str,str], base_prefix: str) -> type[CREDENTIALS]:
    requirements_lut = deepcopy(connection_type_requirements_mapping)
    requirements = requirements_lut[credentials_type]

    if requirements:
        requirements.append("url")
        model_dict={}

        for requirement in requirements:
            model_dict[requirement] = vars[base_prefix+requirement]
        return credentials_type(
            **model_dict
        )
    else:
        # Strip the default prefix
        model_dict = {}
        for key in vars:
            new_key = key.removeprefix(base_prefix)
            model_dict[new_key] = vars[key]
        return credentials_type(
            model_dict
        )


def _validate_schema_type(requested_type: ConnectionSecurityScheme, expected_type: ConnectionSecurityScheme) -> bool:
        return expected_type == requested_type

def _get_credentials_model(connection_type: ConnectionSecurityScheme, app_id: str) -> type[CREDENTIALS]:
    base_prefix = _PREFIX_TEMPLATE.format(app_id=app_id)
    variables = {}
    for key, value in os.environ.items():
        if key.startswith(base_prefix):
            variables[key] = value
    
    credentials_type = CONNECTION_TYPE_CREDENTIAL_MAPPING[connection_type]

    requirements_lut = deepcopy(connection_type_requirements_mapping)
    requirements = requirements_lut.get(credentials_type)
    if requirements:
        variables = _clean_env_vars(vars=variables, requirements=requirements, app_id=app_id)

    return _build_credentials_model(credentials_type=credentials_type, vars=variables, base_prefix=base_prefix)

def get_connection_type(app_id: str) -> ConnectionSecurityScheme:
    sanitized_app_id = sanitize_app_id(app_id=app_id)
    expected_schema_key = f"WXO_SECURITY_SCHEMA_{sanitized_app_id}"
    expected_schema = os.environ.get(expected_schema_key)

    if not expected_schema:
        message = f"No credentials found for connections '{app_id}'"
        logger.error(message)
        raise BadRequest(message)

    auth_types = {e.value for e in ConnectionSecurityScheme}
    if expected_schema not in auth_types:
        message = f"The expected type '{expected_schema}' cannot be resolved into a valid connection auth type ({', '.join(list(auth_types))})"
        logger.error(message)
        raise ValueError(message)

    return expected_schema

def get_application_connection_credentials(type: ConnectionType, app_id: str) -> CREDENTIALS:
    sanitized_app_id = sanitize_app_id(app_id=app_id)
    expected_schema = get_connection_type(app_id=app_id)
    requested_schema = connection_type_security_schema_map.get(type)

    if not _validate_schema_type(requested_type=requested_schema, expected_type=expected_schema):
        message = f"The requested type '{requested_schema}' does not match the type '{expected_schema}' for the connection '{app_id}'"
        logger.error(message)
        raise BadRequest(message)

    return _get_credentials_model(connection_type=requested_schema, app_id=sanitized_app_id)