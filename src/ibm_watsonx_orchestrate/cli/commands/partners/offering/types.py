from enum import Enum
from typing import Optional, List
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
    'supported_apps',
    'part_number',
    'scope',
    'related_links',
    'billing',
    "channels"
]

class OfferingRelatedLinkTypes(str, Enum):
    HYPERLINK = 'hyperlink'
    EMBEDED = 'embeded'

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

class OfferingRelatedLink(BaseModel):
    key: Optional[str]
    value: Optional[str]
    type: Optional[str]


    def __eq__(self, other):
            if isinstance(other, dict):
                return self.model_dump() == other
            return super().__eq__(other)



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

class OfferingAgentScope(BaseModel):
    form_factor: Optional[OfferingFormFactor] = OfferingFormFactor()

class OfferingAgentBilling(BaseModel):
    metered: bool = False

class OfferingAgentRole(str, Enum):
    MANAGER = 'manager'
    COLLABORATOR = 'collaborator'

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)
    
AGENT_CATALOG_ONLY_PLACEHOLDERS = {
    'icon': "inline-svg-of-icon",
    'part_number': OfferingPartNumber(),
    'scope': OfferingAgentScope(),
    'related_links': [
        OfferingRelatedLink(
            key="support",
            value="",
            type=OfferingRelatedLinkTypes.HYPERLINK.value
        ),
        OfferingRelatedLink(
            key="demo",
            value="",
            type=OfferingRelatedLinkTypes.EMBEDED.value
        ),
        OfferingRelatedLink(
            key="documentation",
            value="",
            type=OfferingRelatedLinkTypes.HYPERLINK.value
        ),
        OfferingRelatedLink(
            key="training",
            value="",
            type=OfferingRelatedLinkTypes.EMBEDED.value
        ),
        OfferingRelatedLink(
            key="terms_and_conditions",
            value="",
            type=OfferingRelatedLinkTypes.HYPERLINK.value
        )
    ]
}

class AgentKind(str, Enum):
    NATIVE = "native"
    EXTERNAL = "external"

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)

class OfferingAgentExtras(BaseModel):
    tags: Optional[List[str]] = None
    publisher: Optional[str] = None
    language_support: Optional[List[str]] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    supported_apps: Optional[List[str]] = None
    agent_role: Optional[str] = None
    part_number: Optional[OfferingPartNumber] = None
    scope: Optional[OfferingAgentScope] = None
    channels: Optional[List[str]] = None
    related_links: Optional[List[OfferingRelatedLink]] = None
    billing: Optional[OfferingAgentBilling] = None

    @staticmethod
    def from_agent_details(agent_data: dict, publisher_name: str, parent_agent_name: str) -> 'OfferingAgentExtras':
        extras = OfferingAgentExtras()
        if "tags" not in agent_data:
            extras.tags = []
        if "publisher" not in agent_data:
            extras.publisher = publisher_name
        if "language_support" not in agent_data:
            extras.language_support = ["English"]
        if "icon" not in agent_data:
            extras.icon = AGENT_CATALOG_ONLY_PLACEHOLDERS['icon']
        if "category" not in agent_data:
            extras.category = "agent"
        if "supported_apps" not in agent_data:
            extras.supported_apps = []
        if "agent_role" not in agent_data:
            extras.agent_role = OfferingAgentRole.MANAGER.value if agent_data.get("name") == parent_agent_name else OfferingAgentRole.COLLABORATOR.value
        if "part_number" not in agent_data:
            extras.part_number = AGENT_CATALOG_ONLY_PLACEHOLDERS["part_number"]
        if "scope" not in agent_data:
            extras.scope = AGENT_CATALOG_ONLY_PLACEHOLDERS["scope"]
        if "channels" not in agent_data:
            extras.channels = []
        if "related_links" not in agent_data:
            extras.related_links = AGENT_CATALOG_ONLY_PLACEHOLDERS["related_links"]
        if "billing" not in agent_data:
            extras.billing = OfferingAgentBilling()
        
        return extras
    
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




