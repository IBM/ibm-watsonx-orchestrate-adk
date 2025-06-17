import logging
import sys
from enum import Enum
from pydantic import BaseModel, model_validator, ConfigDict

logger = logging.getLogger(__name__)

class WoAuthType(str, Enum):
    MCSP="mcsp"
    IBM_IAM="ibm_iam"
    CPD="cpd"

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)

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


class WatsonXAIEnvConfig(BaseModel):
    WATSONX_SPACE_ID: str
    WATSONX_APIKEY: str
    USE_SAAS_ML_TOOLS_RUNTIME: bool

    @model_validator(mode="before")
    def validate_wxai_config(values):
        relevant_fields = WatsonXAIEnvConfig.model_fields.keys()
        config = {k: values.get(k) for k in relevant_fields}

        if not config.get("WATSONX_SPACE_ID") and not config.get("WATSONX_APIKEY"):
             raise ValueError("Missing configuration requirements 'WATSONX_SPACE_ID' and 'WATSONX_APIKEY'")
        
        if config.get("WATSONX_SPACE_ID") and not config.get("WATSONX_APIKEY"):
            logger.error("Cannot use env var 'WATSONX_SPACE_ID' without setting the corresponding 'WATSONX_APIKEY'")
            sys.exit(1)
        
        if not config.get("WATSONX_SPACE_ID") and config.get("WATSONX_APIKEY"):
            logger.error("Cannot use env var 'WATSONX_APIKEY' without setting the corresponding 'WATSONX_SPACE_ID'")
            sys.exit(1)
        
        config["USE_SAAS_ML_TOOLS_RUNTIME"] = False
        return config


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
        # Fake (but valid) UUIDv4 for knowledgebase check
        config["WATSONX_SPACE_ID"] = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
        return config