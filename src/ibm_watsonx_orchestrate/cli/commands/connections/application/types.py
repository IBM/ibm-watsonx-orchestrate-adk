from enum import Enum


class ApplicationConnectionType(str, Enum):
    basic = 'basic'
    bearer = 'bearer'
    api_key = 'api_key'
    oauth_auth_code_flow = 'oauth_auth_code_flow'
    oauth_auth_implicit_flow = 'oauth_auth_implicit_flow'
    oauth_auth_password_flow = 'oauth_auth_password_flow'
    oauth_auth_client_credentials_flow = 'oauth_auth_client_credentials_flow'
    key_value = 'key_value'
    kv = 'kv'

    def __str__(self):
        return self.value

