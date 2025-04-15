import os
import logging
from typing import Union, TypeVar, List
from ibm_watsonx_orchestrate.client.connections import (
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2AuthCodeCredentials,
    OAuth2ImplicitCredentials,
    OAuth2PasswordCredentials,
    OAuth2ClientCredentials,
    KeyValueConnectionCredentials,
    ConnectionType
)

from ibm_watsonx_orchestrate.utils.utils import sanatize_app_id
from ibm_watsonx_orchestrate.utils.request import BadRequest

logger = logging.getLogger(__name__)

CREDENTIALS = Union[
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2AuthCodeCredentials,
    OAuth2ImplicitCredentials,
    OAuth2PasswordCredentials,
    OAuth2ClientCredentials,
    KeyValueConnectionCredentials
]

T = TypeVar("T", bound=CREDENTIALS)

connection_type_mapping = {
    ConnectionType.BASIC_AUTH: BasicAuthCredentials,
    ConnectionType.BEARER_TOKEN: BearerTokenAuthCredentials,
    ConnectionType.API_KEY_AUTH: APIKeyAuthCredentials,
    ConnectionType.OAUTH2_AUTH_CODE: OAuth2AuthCodeCredentials,
    ConnectionType.OAUTH2_IMPLICIT: OAuth2ImplicitCredentials,
    ConnectionType.OAUTH2_PASSWORD: OAuth2PasswordCredentials,
    ConnectionType.OAUTH2_CLIENT_CREDS: OAuth2ClientCredentials,
    ConnectionType.KEY_VALUE: KeyValueConnectionCredentials
}

_PREFIX_TEMPLATE = "WXO_CONNECTION_{app_id}_"
_BASE_OAUTH_REQUIREMENTS = ["client_id", "client_secret", "well_known_url"]

connection_type_requirements_mapping = {
    BasicAuthCredentials: ["username", "password"],
    BearerTokenAuthCredentials: ["token"],
    APIKeyAuthCredentials: ["api_key"],
    OAuth2AuthCodeCredentials: _BASE_OAUTH_REQUIREMENTS,
    OAuth2ImplicitCredentials: _BASE_OAUTH_REQUIREMENTS,
    OAuth2PasswordCredentials: _BASE_OAUTH_REQUIREMENTS + ["username", "password"],
    OAuth2ClientCredentials: _BASE_OAUTH_REQUIREMENTS,
    KeyValueConnectionCredentials: None
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
    
    if len(missing_requirements) > 0:
        missing_requirements_str = ", ".join(missing_requirements)
        message = f"Missing requirement environment variables '{missing_requirements_str}' for connection '{app_id}'"
        logger.error(message)
        raise BadRequest(message)
    
    return required_env_vars

def _build_credentials_model(credentials_type: type[T], vars: dict[str,str], base_prefix: str) -> type[T]:
    requirements = connection_type_requirements_mapping[credentials_type]

    if requirements:
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


def _validate_schema_type(requested_type: type[T], expected_type: ConnectionType) -> bool:
        return connection_type_mapping.get(expected_type) == requested_type

def _get_credentials_model(credentials_type: type[T], app_id: str) -> type[T]:
    base_prefix = _PREFIX_TEMPLATE.format(app_id=app_id)
    variables = {}
    for key, value in os.environ.items():
        if key.startswith(base_prefix):
            variables[key] = value

    requirements = connection_type_requirements_mapping.get(credentials_type)
    if requirements:
        variables = _clean_env_vars(vars=variables, requirements=requirements, app_id=app_id)

    return _build_credentials_model(credentials_type=credentials_type, vars=variables, base_prefix=base_prefix)

def get_application_connection_credentials(type: type[T], app_id: str) -> T:
    sanitized_app_id = sanatize_app_id(app_id=app_id)
    expected_schema_key = f"WXO_SECURITY_SCHEMA_{sanitized_app_id}"
    expected_schema = os.environ.get(expected_schema_key)

    if not expected_schema:
        message = f"No credentials found for connections '{app_id}'"
        logger.error(message)
        raise BadRequest(message)

    if not _validate_schema_type(requested_type=type, expected_type=expected_schema):
        message = f"The requested type '{type.__name__}' does not match the type '{expected_schema}' for the connection '{app_id}'"
        logger.error(message)
        raise BadRequest(message)

    return _get_credentials_model(credentials_type=type, app_id=sanitized_app_id)