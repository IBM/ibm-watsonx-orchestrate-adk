

import json
from typing import Optional

import requests
from pydantic import Field, BaseModel
import base64

from requests.auth import HTTPBasicAuth

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.run import connections

from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType

CONNECTION_SNOW = 'service-now'

class ServiceNowIncident(BaseModel):
    """
    Represents the details of a ServiceNow incident.
    """
    incident_number: str = Field(..., description='The incident number assigned by ServiceNow')
    short_description: str = Field(..., description='A brief summary of the incident')
    description: Optional[str] = Field(None, description='Detailed information about the incident')
    state: str = Field(..., description='Current state of the incident')
    urgency: str = Field(..., description='Urgency level of the incident')
    created_on: str = Field(..., description='The date and time the incident was created')

@tool(
    expected_credentials=[
        {"app_id": CONNECTION_SNOW, "type": ConnectionType.BASIC_AUTH}
    ]
)
def get_service_now_incident_by_number(incident_number: str):
    """
    Fetch a ServiceNow incident based on incident ID, creation date, or other filters.
    
    :param incident_number: The uniquely identifying incident number of the ticket.
    :returns: The incident details including number, system ID, description, state, and urgency.
    """
    creds = connections.basic_auth('service-now')
    base_url = creds.url
    url = f"{base_url}/api/now/table/incident"

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    query_params = {}
    if incident_number:
        query_params['number'] = incident_number
    
    response = requests.get(
        url,
        headers=headers,
        params=query_params,
        auth=HTTPBasicAuth(creds.username, creds.password)
    )
    response.raise_for_status()
    data = response.json()['result']
    data = data[0]  # Assuming only one incident is returned
    
    return ServiceNowIncident(
        incident_number=data['number'],
        short_description=data['short_description'],
        description=data.get('description', ''),
        state=data['state'],
        urgency=data['urgency'],
        created_on=data['opened_at']
    ).model_dump_json()

# if __name__ == '__main__':
#     incident = fetch_service_now_incident(incident_number='INC0010311')
#     print(json.dumps(incident.dict(), indent=2))

