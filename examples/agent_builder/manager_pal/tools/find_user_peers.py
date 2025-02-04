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
      peers {
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


class UserPeerTelephone(BaseModel):
    office: str = Field(None, desc='The office phone number of the peer')
    mobile: str = Field(None, desc='The mobile phone number of the peer')


class UserPeer(BaseModel):
    role: str = Field(None, desc='The job role of this peer')
    userId: str = Field(None, desc='The w3 userId of this peer')
    name: str = Field(None, desc='The full name of the peer')
    slackId: str = Field(None, desc='The user id of the peer on slack')
    slackUsername: str = Field(None, desc='The user name of the peer on slack')
    email: str = Field(None, desc='The email address of the peer')
    telephone: UserPeerTelephone


@tool(
    permission=ToolPermission.READ_ONLY
)
def find_users_peers(userId: str) -> List[Any]:
    """
    Search for all peers of a person given their w3 userId. This will include the name, role and contact information
    of those peers. You should first call find_w3_userId_for_name to find the userId for this request if you are only
    given a name.
    :param userId: W3 id of the user to search for
    :returns: A list of users and their associated userId
    """
    resp = requests.post(
        url='https://w3-graph-w3-graph.dal1a.cirrus.ibm.com/graphql?op=searchPeople',
        json={
            'operationName': GET_W3_USER_TEAM_OPERATION_ID,
            'query': GET_W3_USER_TEAM_QUERY,
            'variables': {'userId': userId}
        }
    )
    resp.raise_for_status()
    return resp.json()['data'][GET_W3_USER_TEAM_OPERATION_ID]['functional']['peers']


# if __name__ == '__main__':
#     people = find_peers(userId='4G0344897')
#     print(json.dumps(people, indent=2))

