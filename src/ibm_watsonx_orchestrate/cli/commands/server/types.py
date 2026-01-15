import logging
import sys
import uuid
from enum import Enum
from typing import Optional
from pydantic import BaseModel, model_validator, ConfigDict
from ibm_cloud_sdk_core.authenticators import Authenticator, MCSPAuthenticator, IAMAuthenticator, CloudPakForDataAuthenticator

from ibm_watsonx_orchestrate.client.client import Client
from ibm_watsonx_orchestrate.client.credentials import Credentials
from ibm_watsonx_orchestrate.client.service_instance import ServiceInstance
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)

class WoAuthType(str, Enum):
    MCSP="mcsp"
    IBM_IAM="ibm_iam"
    CPD="cpd"

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)
    
class WxaiAuthType(str, Enum):
    MCSP="mcsp"
    IBM_IAM="ibm_iam"

AUTH_TYPE_DEFAULT_URL_MAPPING = {
    WoAuthType.MCSP: "https://iam.platform.saas.ibm.com/siusermgr/api/1.0/apikeys/token",
    WoAuthType.IBM_IAM: "https://iam.cloud.ibm.com/identity/token",
}

def _infer_auth_type_from_instance_url(instance_url: str) -> WoAuthType:
    if ".cloud.ibm.com" in instance_url:
        return WoAuthType.IBM_IAM
    if ".ibm.com" in instance_url:
        return WoAuthType.MCSP
    if "https://cpd" in instance_url:
        return WoAuthType.CPD
        
def _create_wo_authenticator(api_key: str, instance_url: str, auth_url: Optional[str] = None) -> Authenticator:
    # sanitize auth url for mcsp
    if auth_url:
        auth_url = auth_url.replace('/siusermgr/api/1.0/apikeys/token','').replace('/api/2.0/apikeys/token','')

    # create credentials & client
    creds = Credentials(url=instance_url, iam_url=auth_url, api_key=api_key)
    client = Client(creds)

    # create service instance & authenticator 
    service_instance = ServiceInstance(client)
    auth_type = service_instance._infer_auth_type()
    return service_instance._get_authenticator(auth_type)
            

def _infer_wxai_auth_type_from_wxai_url(wxai_url: str) -> WxaiAuthType:
    if "aws" in wxai_url:
        return WxaiAuthType.MCSP
    else:
        return WxaiAuthType.IBM_IAM

def _infer_wxai_auth_token_url_from_wxai_url(wxai_url: str) -> str:
    auth_type = _infer_wxai_auth_type_from_wxai_url(wxai_url)
    match auth_type:
        case WxaiAuthType.IBM_IAM:
            return "https://iam.cloud.ibm.com/identity/token"
        case WxaiAuthType.MCSP:
            return "https://account-iam.platform.saas.ibm.com/api/2.0/apikeys/token"
        
        
def _create_wxai_authenticator(api_key:str, wxai_url: str, auth_url: Optional[str] = None) -> Authenticator:
    auth_type = _infer_wxai_auth_type_from_wxai_url(wxai_url)
    auth_url = auth_url if auth_url else _infer_wxai_auth_token_url_from_wxai_url(wxai_url)
    match auth_type:
        case WxaiAuthType.IBM_IAM:
            return IAMAuthenticator(apikey=api_key,url=auth_url)
        case WxaiAuthType.MCSP:
            return MCSPAuthenticator(apikey=api_key,url=auth_url.replace('/api/2.0/apikeys/token',''))
        case _:
            raise ValueError(f"Unable to create authenticator for wxai url: {wxai_url}")


class DirectAIEnvConfig(BaseModel):
    WATSONX_SPACE_ID: Optional[str]
    WATSONX_APIKEY: Optional[str]
    GROQ_API_KEY: Optional[str]
    USE_SAAS_ML_TOOLS_RUNTIME: bool

    @model_validator(mode="before")
    def validate_wxai_config(values):
        relevant_fields = DirectAIEnvConfig.model_fields.keys()
        config = {k: values.get(k) for k in relevant_fields}

        # If all missing
        groq_key_set = bool(config.get("GROQ_API_KEY"))
        wxai_space_id_set = bool(config.get("WATSONX_SPACE_ID"))
        wxai_key_set = bool(config.get("WATSONX_APIKEY"))

        if not wxai_key_set and not groq_key_set:
            raise ValueError("Missing configuration requirements 'GROQ_API_KEY' or 'WATSONX_APIKEY'")

        # If Space id but no apikey
        
        if not wxai_space_id_set and wxai_key_set:
            logger.error("Cannot use env var 'WATSONX_APIKEY' without setting the corresponding 'WATSONX_SPACE_ID'")
            sys.exit(1)
        
        config["USE_SAAS_ML_TOOLS_RUNTIME"] = False
        return config

def is_valid_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False

class ModelGatewayEnvConfig(BaseModel):
    WO_API_KEY: str | None = None
    WO_USERNAME: str | None = None
    WO_PASSWORD: str | None = None
    WO_INSTANCE: str
    AUTHORIZATION_URL: str
    USE_SAAS_ML_TOOLS_RUNTIME: bool
    WO_AUTH_TYPE: WoAuthType
    WATSONX_SPACE_ID: str

    @model_validator(mode="before")
    def validate_model_gateway_config(values):
        relevant_fields = ModelGatewayEnvConfig.model_fields.keys()
        config = {k: values.get(k) for k in relevant_fields}

        if not config.get("WO_INSTANCE"):
            raise ValueError("Missing configuration requirements 'WO_INSTANCE'")
        
        if not config.get("WO_AUTH_TYPE"):
            inferred_auth_type = _infer_auth_type_from_instance_url(config.get("WO_INSTANCE"))
            if not inferred_auth_type:
                logger.error(f"Could not infer auth type from 'WO_INSTANCE'. Please set the 'WO_AUTH_TYPE' explictly")
                sys.exit(1)
            config["WO_AUTH_TYPE"] = inferred_auth_type
        auth_type = config.get("WO_AUTH_TYPE")
        
        if not config.get("AUTHORIZATION_URL"):
            inferred_auth_url = AUTH_TYPE_DEFAULT_URL_MAPPING.get(auth_type)
            if not inferred_auth_url:
                if auth_type == WoAuthType.CPD:
                    inferred_auth_url = config.get("WO_INSTANCE") + '/icp4d-api/v1/authorize'   
                else: 
                    logger.error(f"No 'AUTHORIZATION_URL' found. Auth type '{auth_type}' does not support defaulting. Please set the 'AUTHORIZATION_URL' explictly")
                    sys.exit(1)
            config["AUTHORIZATION_URL"] = inferred_auth_url
        
        if auth_type != WoAuthType.CPD:
            if not config.get("WO_API_KEY"):
                logger.error(f"Auth type '{auth_type}' requires 'WO_API_KEY' to be set as an env var.")
                sys.exit(1)
        else:
            if not config.get("WO_USERNAME"):
                logger.error("Auth type 'cpd' requires 'WO_USERNAME' to be set as an env var.")
                sys.exit(1)
            if not config.get("WO_API_KEY") and not config.get("WO_PASSWORD"):
                logger.error("Auth type 'cpd' requires either 'WO_API_KEY' or 'WO_PASSWORD' to be set as env vars.")
                sys.exit(1)
        
        config["USE_SAAS_ML_TOOLS_RUNTIME"] = True
        if not is_valid_uuid(config.get("WATSONX_SPACE_ID")):
            # Fake (but valid) UUIDv4 for knowledgebase check
            config["WATSONX_SPACE_ID"] = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
        return config