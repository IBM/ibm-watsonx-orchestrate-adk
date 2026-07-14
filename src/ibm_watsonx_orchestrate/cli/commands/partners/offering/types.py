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
    EMBEDDED = 'embedded'

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
    ibmcloud: Optional[str] = CATALOG_PLACEHOLDERS['form_factor']
    cp4d: Optional[str] = CATALOG_PLACEHOLDERS['form_factor']

class OfferingPartNumber(BaseModel):
    aws: Optional[str] = None
    ibmcloud: Optional[str] = None
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
    
TOOL_CATALOG_ONLY_PLACEHOLDERS = {
    'icon': "inline-svg-of-icon",
    'change_log': ["Initial release"],
    'version': "1.0.0",
}

class ToolCatalogExtras(BaseModel):
    """Fields injected into a tool YAML during `offering create` if absent."""
    category: Optional[str] = None
    kind: Optional[str] = None
    version: Optional[str] = None
    change_log: Optional[List[str]] = None
    bundled: Optional[bool] = None
    delete_by: Optional[str] = None
    publisher: Optional[str] = None
    language_support: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    icon: Optional[str] = None
    hidden: Optional[bool] = None

    @staticmethod
    def from_tool_details(tool_data: dict, publisher_name: str) -> 'ToolCatalogExtras':
        extras = ToolCatalogExtras()
        if "category" not in tool_data:
            extras.category = "tool"
        if "kind" not in tool_data:
            extras.kind = "native"
        if "publisher" not in tool_data:
            extras.publisher = publisher_name
        if "language_support" not in tool_data:
            extras.language_support = ["English"]
        if "tags" not in tool_data:
            extras.tags = []
        if "icon" not in tool_data:
            extras.icon = TOOL_CATALOG_ONLY_PLACEHOLDERS['icon']
        if "change_log" not in tool_data:
            extras.change_log = TOOL_CATALOG_ONLY_PLACEHOLDERS['change_log']
        if "bundled" not in tool_data:
            extras.bundled = False
        if "version" not in tool_data:
            extras.version = TOOL_CATALOG_ONLY_PLACEHOLDERS['version']
        if "delete_by" not in tool_data:
            extras.delete_by = None
        if "hidden" not in tool_data:
            extras.hidden = False
        return extras

AGENT_CATALOG_ONLY_PLACEHOLDERS = {
    'icon': "inline-svg-of-icon",
    'scope': OfferingAgentScope(),
    'change_log': ["Initial release"],
    'version': "1.0.0",
    'related_links': [
        OfferingRelatedLink(
            key="Support",
            value="",
            type=OfferingRelatedLinkTypes.HYPERLINK.value
        ),
        OfferingRelatedLink(
            key="Demo",
            value="",
            type=OfferingRelatedLinkTypes.EMBEDDED.value
        ),
        OfferingRelatedLink(
            key="Documentation",
            value="",
            type=OfferingRelatedLinkTypes.HYPERLINK.value
        ),
        OfferingRelatedLink(
            key="Training",
            value="",
            type=OfferingRelatedLinkTypes.EMBEDDED.value
        ),
        OfferingRelatedLink(
            key="Terms and Conditions",
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
    change_log: Optional[List[str]] = None
    bundled: Optional[bool] = None
    version: Optional[str] = None
    delete_by: Optional[str] = None

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
            extras.part_number = OfferingPartNumber()  # all-null: free agent default
        if "scope" not in agent_data:
            extras.scope = AGENT_CATALOG_ONLY_PLACEHOLDERS["scope"]
        if "channels" not in agent_data:
            extras.channels = []
        if "related_links" not in agent_data:
            extras.related_links = AGENT_CATALOG_ONLY_PLACEHOLDERS["related_links"]
        if "billing" not in agent_data:
            extras.billing = OfferingAgentBilling()
        if "change_log" not in agent_data:
            extras.change_log = AGENT_CATALOG_ONLY_PLACEHOLDERS["change_log"]
        if "bundled" not in agent_data:
            extras.bundled = False
        if "version" not in agent_data:
            extras.version = AGENT_CATALOG_ONLY_PLACEHOLDERS["version"]
        if "delete_by" not in agent_data:
            extras.delete_by = None
        
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




