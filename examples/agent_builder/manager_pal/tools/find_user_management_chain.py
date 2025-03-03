import json
from typing import List, Any

import requests
from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.agent_builder.tools import ToolPermission, tool

GET_W3_USER_TEAM_OPERATION_ID = 'userTeam'
GET_W3_USER_TEAM_QUERY = """
query userTeam($userId: ID) {
  userTeam(userId: $userId) {
    functional {
      leadership {
        ...TeamUserFields
      }
    }
  }
}

fragment TeamUserFields on TeamUser {
  role
  userId: uid
  name: nameFull
  slackId: preferredSlackId
  slackUsername: preferredSlackUsername
  email: preferredIdentity
  telephone {
    office
    mobile
  }
}
"""


class UserLeaderTelephone(BaseModel):
    office: str = Field(None, desc='The office phone number of the leader')
    mobile: str = Field(None, desc='The mobile phone number of the leader')


class UserLeader(BaseModel):
    role: str = Field(None, desc='The job role of this leader')
    userId: str = Field(None, desc='The w3 userId of this leader')
    name: str = Field(None, desc='The full name of the leader')
    slackId: str = Field(None, desc='The user id of the leader on slack')
    slackUsername: str = Field(None, desc='The user name of the leader on slack')
    email: str = Field(None, desc='The email address of the leader')
    telephone: UserLeaderTelephone


@tool(
    permission=ToolPermission.READ_ONLY
)
def find_users_management_chain(userId: str) -> List[UserLeader]:
    """
    Search for all managers of a person given their w3 userId. This will include the name, role and contact information
    of those managers. The list will first include the person's manager, then the manager of that manager and so on.
    You should first call find_w3_userId_for_name to find the userId for this request if you are only given a name.
    :param userId: The w3 userId of the user to fetch the peers of
    :returns: The list of managers of the user with the given w3 userId
    """
    resp = requests.post(
        url='https://w3-graph-w3-graph.w3-globals.dal.app.cirrus.ibm.com/graphql?searchPeople',
        verify=False,
        json={
            'operationName': GET_W3_USER_TEAM_OPERATION_ID,
            'query': GET_W3_USER_TEAM_QUERY,
            'variables': {'userId': userId}
        }
    )
    resp.raise_for_status()
    return resp.json()['data'][GET_W3_USER_TEAM_OPERATION_ID]['functional']['leadership']


# if __name__ == '__main__':
#     people = find_users_management_chain(userId='4G0344897')
#     print(json.dumps(people, indent=2))

