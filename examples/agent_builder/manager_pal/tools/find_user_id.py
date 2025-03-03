import json
from typing import List

import requests
from pydantic import Field, BaseModel

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

SEARCH_PEOPLE_QUERY_OPERATION_ID = 'searchPeople'
SEARCH_PEOPLE_QUERY = """
query searchPeople($query: String, $rows: Int, $start: Int, $searchConfig: String, $ffqValues: FFQValues) {
  searchPeople(
    query: $query
    rows: $rows
    start: $start
    searchConfig: $searchConfig
    ffqValues: $ffqValues
  ) {
    results {
      ...PeopleFields
    }
  }
}

fragment PeopleFields on People {
  name: nameFull
  userId: uid
}
"""


class W3UserNameAndId(BaseModel):
    """
    A collection of a users full name and the userId on w3
    """
    name: str = Field(None, desc='The full name of the person')
    userId: str = Field(None, desc='The w3 userId of the user to query w3 apis with')


@tool(
    permission=ToolPermission.READ_ONLY
)
def find_w3_userId_for_name(name: str, rows: int = 10) -> List[W3UserNameAndId]:
    """
    Search for all people with a name similar to name and fetch their associated w3 userId
    :param name: The name of the user to fetch the userId for
    :returns: A list of users and their associated userId
    """
    resp = requests.post(
        url='https://w3-graph-w3-graph.w3-globals.dal.app.cirrus.ibm.com/graphql?searchPeople',
        verify=False,
        json={
            'operationName': SEARCH_PEOPLE_QUERY_OPERATION_ID,
            'query': SEARCH_PEOPLE_QUERY,
            'variables': {'query': name, 'rows': rows}
        }
    )
    resp.raise_for_status()
    return resp.json()['data'][SEARCH_PEOPLE_QUERY_OPERATION_ID]['results']


# if __name__ == '__main__':
#     people = find_w3_userId_for_name(name='eric marcoux')
#     print(json.dumps(people, indent=2))