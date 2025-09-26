from enum import Enum
from typing import Optional
import logging

from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)

CATALOG_PLACEHOLDERS = {
    'domain' : 'HR',
    'version' : '1.0',
    'part_number': 'my-part-number',
    'form_factor': 'free',
    'tenant_type': {
        'trial': 'free'
    }
}

CATALOG_ONLY_FIELDS = [
    'publisher',
    'language_support',
    'icon',
    'category',
    'supported_apps'
]

AGENT_CATALOG_ONLY_PLACEHOLDERS = {
    'icon': "inline-svg-of-icon",
}

class AgentKind(str, Enum):
    NATIVE = "native"
    EXTERNAL = "external"

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)

class OfferingFormFactor(BaseModel):
    aws: Optional[str] = CATALOG_PLACEHOLDERS['form_factor']
    ibm_cloud: Optional[str] = CATALOG_PLACEHOLDERS['form_factor']
    cp4d: Optional[str] = CATALOG_PLACEHOLDERS['form_factor']

class OfferingPartNumber(BaseModel):
    aws: Optional[str] = CATALOG_PLACEHOLDERS['part_number']
    ibm_cloud: Optional[str] = CATALOG_PLACEHOLDERS['part_number']
    cp4d: Optional[str] = None

class OfferingScope(BaseModel):
    form_factor: Optional[OfferingFormFactor] = OfferingFormFactor()
    tenant_type: Optional[dict] = CATALOG_PLACEHOLDERS['tenant_type']
    
class Offering(BaseModel):
    name: str
    display_name: str
    domain: Optional[str] = CATALOG_PLACEHOLDERS['domain']
    publisher: str
    version: Optional[str] = CATALOG_PLACEHOLDERS['version']
    description: str
    assets: dict
    part_number: Optional[OfferingPartNumber] = OfferingPartNumber()
    scope: Optional[OfferingScope] = OfferingScope()

    def __init__(self, *args, **kwargs):
        # set asset details
        if not kwargs.get('assets'):
            kwargs['assets'] = {
                kwargs.get('publisher','default_publisher'): {
                    "agents": kwargs.get('agents',[]),
                    "tools": kwargs.get('tools',[])
                }
            }
        super().__init__(**kwargs)

    @model_validator(mode="before")
    def validate_values(cls,values):
        publisher = values.get('publisher')
        if not publisher:
            raise ValueError(f"An offering cannot be packaged without a publisher")
        
        assets = values.get('assets')
        if not assets or not assets.get(publisher):
            raise ValueError(f"An offering cannot be packaged without assets")
        
        agents = assets.get(publisher).get('agents')
        if not agents:
            raise ValueError(f"An offering requires at least one agent to be provided")
        
        return values
    
    def validate_ready_for_packaging(self):
        # Leaving this fn here in case we want to reintroduce validation
        pass




