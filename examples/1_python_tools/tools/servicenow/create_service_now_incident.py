import base64
import json
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

from pydantic import Field, BaseModel

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.run import connections

from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType

CONNECTION_SNOW = 'service-now'

class ServiceNowIncidentResponse(BaseModel):
    """Represents the response received after creating a ServiceNow incident.
    """
    incident_number: str = Field(..., description='The incident number assigned by ServiceNow')
    sys_id: str = Field(..., description='The system ID of the created incident')


class ServiceNowIncident(BaseModel):
    """Represents the details of a ServiceNow incident.
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
def create_service_now_incident(
        short_description: str,
        description: Optional[str] = None,
        urgency: Optional[int] = 3
):
    """Create a new ServiceNow incident.

    Args:
        short_description (str): A brief summary of the incident.
        description (Optional[str], optional): Detailed information about the incident. Defaults to None.
        urgency (Optional[int], optional): Urgency level (1 - High, 2 - Medium, 3 - Low). Defaults to 3.

    Returns:
        str: The created incident details including incident number and system ID.
    """
    try:
        creds = connections.basic_auth(CONNECTION_SNOW)
        base_url = creds.url
        url = f"{base_url}/api/now/table/incident"

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        payload = {
            'short_description': short_description,
            'description': description,
            'urgency': urgency
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            auth=HTTPBasicAuth(creds.username, creds.password)
        )
        response.raise_for_status()
        data = response.json()['result']

        number, sys_id = data['number'], data['sys_id']

        url = f"{base_url}/api/now/table/incident/{sys_id}"
        response = requests.get(
            url,
            headers=headers,
            json=payload,
            auth=HTTPBasicAuth(creds.username, creds.password)
        )
        response.raise_for_status()
        data = response.json()['result']

        return ServiceNowIncident(
            incident_number=data['number'],
            sys_id=data['sys_id'],
            short_description=data['short_description'],
            description=data.get('description', ''),
            state=data['state'],
            urgency=data['urgency'],
            created_on=data['opened_at']
        ).model_dump_json()
    except Exception as e:
        return f"Error: {e}"

# if __name__ == '__main__':
#     incident = create_service_now_incident(short_description='Test Incident', description='This is a test incident')
#     print(json.dumps(incident.dict(), indent=2))
