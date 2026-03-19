from typing import Optional, List

from pydantic import BaseModel, Field

# Not unused they are imported for backwards compatability
from ibm_watsonx_orchestrate_core.types.connections import *

class ConnectionsListEntry(BaseModel):
    app_id: str = Field(description="A unique identifier for the connection.")
    auth_type: Optional[str] = Field(default=None, description="The kind of auth used by the connections")
    type: Optional[ConnectionPreference] = Field(default=None, description="The type of the connections. If set to 'team' the credentails will be shared by all users. If set to 'member' each user will have to provide their own credentials")
    credentials_set: bool = Field(default=False, description="Are the credentials set for the current user. If using OAuth connection types this value will be False unless there isn a stored token from runtime usage")

    def get_row_details(self):
        auth_type = self.auth_type if self.auth_type else "n/a"
        type = self.type if self.type else "n/a"
        credentials_set = "✅" if self.credentials_set else "❌"
        return [self.app_id, auth_type, type, credentials_set]

class ConnectionsListResponse(BaseModel):
    non_configured: Optional[List[dict] | str] = None
    draft: Optional[List[dict] | str] = None
    live: Optional[List[dict] | str] = None