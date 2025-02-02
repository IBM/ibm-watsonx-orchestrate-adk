import json

import requests

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
    matches
    results {
      ...PeopleFields
      __typename
    }
    facetResults {
      facetResultsMatches {
        dept_code
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment PeopleFields on People {
  address_business_location
  assistant_name_first
  assistant_name_last
  assistant_preferredIdentity
  assistant_uid
  co
  conferenceUrl
  dept_code
  employeeType_title
  hrOrganizationCode
  mail
  nameFull
  nameDisplay
  notesEmail
  org_title
  offering_name
  partnershipExecutivePrograms
  preferredIdentity
  preferredSlackId
  preferredSlackUsername
  resultLevel
  role
  serial
  telephone_mobile
  telephone_office
  uid
  workLocation_office
  contractorCompany
  contractorRecordExpiration
  __typename
}
"""

def search_w3_people(query: str, rows: int = 10):
    resp = requests.post(
        url='https://w3-graph-w3-graph.dal1a.cirrus.ibm.com/graphql?op=searchPeople',
        json={
            'operationName': SEARCH_PEOPLE_QUERY_OPERATION_ID,
            'query': SEARCH_PEOPLE_QUERY,
            'variables': {'query': query, 'rows': rows}
        }
    )
    resp.raise_for_status()
    return resp.json()['data'][SEARCH_PEOPLE_QUERY_OPERATION_ID]['results']



GET_W3_PROFILE_OPERATION_ID = 'peopleProfile'
GET_W3_PROFILE_QUERY = """
query peopleProfile($userId: ID) {
  peopleProfile(userId: $userId) {
    profile {
      ...ProfileFields
      __typename
    }
    expertise {
      ...ExpertiseFields
      __typename
    }
    __typename
  }
}

fragment ExpertiseFields on Expertise {
  aot {
    aotGood
    aotRole
    __typename
  }
  aotMember
  certifications {
    certs
    badges {
      badgeDescription
      badgeId
      badgeImageUrl
      badgeName
      badgeUrl
      issueDate
      issueId
      order
      publicUrl
      __typename
    }
    __typename
  }
  expertiseSummary
  jobRoles {
    jobRole
    JR_ID
    primary
    skillSets {
      skillSet
      primary
      __typename
    }
    __typename
  }
  patentCollaboration
  patents {
    country
    date
    num
    title
    __typename
  }
  patentRoles
  patentWork
  publications {
    booksPapers
    links {
      name
      url
      __typename
    }
    __typename
  }
  resume
  customLinks {
    github
    linkedIn
    __typename
  }
  offerings {
    name
    link
    __typename
  }
  primaryJobCategory {
    name
    __typename
  }
  secondaryJobCategory {
    name
    __typename
  }
  __typename
}

fragment ProfileFields on Profile {
  address {
    business {
      address
      country
      locality
      location
      state
      stateCo
      zip
      __typename
    }
    preferred {
      address
      address1
      address2
      country
      locality
      state
      zip
      __typename
    }
    __typename
  }
  alternateBackups {
    name {
      first
      last
      __typename
    }
    nameDisplay
    preferredIdentity
    responsibilities
    role
    uid
    nameFull
    isManager
    preferredSlackUsername
    preferredSlackId
    __typename
  }
  alternateLastName
  alternateNode
  alternateUserId
  assistant {
    name {
      first
      last
      __typename
    }
    preferredIdentity
    role
    uid
    nameFull
    nameDisplay
    isManager
    preferredSlackUsername
    preferredSlackId
    __typename
  }
  backup {
    name {
      first
      last
      __typename
    }
    backupCountryCode
    backupSerialNumber
    preferredIdentity
    nameDisplay
    uid
    role
    responsibilities
    nameFull
    isManager
    preferredSlackUsername
    preferredSlackId
    __typename
  }
  bpPronoun
  c
  co
  costCenter
  contractorCompany
  contractorRecordExpiration
  courtesyTitle
  createdDate
  dept {
    title
    code
    __typename
  }
  div
  divestitureFlag
  divestitureEmpTitle
  employeeType {
    title
    isManager
    isEmployee
    code
    __typename
  }
  entryType
  hideSerial
  hrCountryCode
  hrOrganizationCode
  importantContactInfo
  iot
  legalEntity {
    groupId
    name
    __typename
  }
  mail
  mailDrop
  managerPSC
  name {
    native {
      first
      last
      __typename
    }
    __typename
  }
  nameDisplay
  nameFull
  notesEmail
  notesShortName
  notesMailDomain
  oooSettings {
    message
    date
    __typename
  }
  org {
    group
    title
    code
    unit
    __typename
  }
  partnershipExecutivePrograms
  practiceAlignment
  preferredContactMethod
  preferredIdentity
  preferredSlackId
  preferredSlackUsername
  profileDateTime
  pronoun
  pronunciation
  psc
  role
  sAMAccountName
  serial
  signLanguages
  slackProfiles {
    slackId
    slackUsername
    __typename
  }
  telephone {
    mobile
    alternate
    fax
    office
    voice
    __typename
  }
  timeZoneCode
  uid
  ventureCode
  ventureDescription
  workLocation {
    building
    campusID
    code
    floor
    office
    __typename
  }
  workplaceIndicator
  mailboxType
  concurProfiles {
    id
    name
    __typename
  }
  __typename
}
"""


def get_w3_profile(userId: str):
    resp = requests.post(
        url='https://w3-graph-w3-graph.dal1a.cirrus.ibm.com/graphql?op=searchPeople',
        json={
            'operationName': GET_W3_PROFILE_OPERATION_ID,
            'query': GET_W3_PROFILE_QUERY,
            'variables': {'userId': userId}
        }
    )
    resp.raise_for_status()
    return resp.json()['data'][GET_W3_PROFILE_OPERATION_ID]


GET_W3_USER_TEAM_OPERATION_ID = 'userTeam'
GET_W3_USER_TEAM_QUERY = """
query userTeam($userId: ID) {
  userTeam(userId: $userId) {
    uid
    deptsManaged {
      code
      name
      __typename
    }
    bosses {
      ...TeamUserFields
      __typename
    }
    functional {
      leadership {
        ...TeamUserFields
        __typename
      }
      peers {
        ...TeamUserFields
        __typename
      }
      reports {
        ...TeamUserFields
        __typename
      }
      nonPersonReports {
        ...TeamUserFields
        __typename
      }
      __typename
    }
    incountry {
      leadership {
        ...TeamUserFields
        __typename
      }
      peers {
        ...TeamUserFields
        __typename
      }
      reports {
        ...TeamUserFields
        __typename
      }
      nonPersonReports {
        ...TeamUserFields
        __typename
      }
      __typename
    }
    __typename
  }
  userSites(userId: $userId) {
    name
    description
    url
    pushToSearch
    __typename
  }
}

fragment TeamUserFields on TeamUser {
  role
  preferredIdentity
  uid
  nameFull
  nameDisplay
  preferredSlackId
  preferredSlackUsername
  notesEmail
  isEmployee
  isManager
  legalEntity {
    name
    code
    groupId
    groupCode
    __typename
  }
  name {
    first
    last
    __typename
  }
  telephone {
    office
    mobile
    __typename
  }
  dept {
    title
    code
    __typename
  }
  employeeType {
    title
    isManager
    isEmployee
    code
    __typename
  }
  address {
    business {
      country
      location
      __typename
    }
    __typename
  }
  assistant {
    uid
    preferredIdentity
    nameDisplay
    name {
      first
      last
      __typename
    }
    __typename
  }
  org {
    title
    code
    __typename
  }
  contractorCompany
  contractorRecordExpiration
  __typename
}
"""


def get_w3_users_team(userId: str):
    resp = requests.post(
        url=f"https://w3-graph-w3-graph.dal1a.cirrus.ibm.com/graphql?op={GET_W3_USER_TEAM_OPERATION_ID}",
        json={
            'operationName': GET_W3_USER_TEAM_OPERATION_ID,
            'query': GET_W3_USER_TEAM_QUERY,
            'variables': {'userId': userId}
        }
    )
    resp.raise_for_status()
    return resp.json()['data'][GET_W3_USER_TEAM_OPERATION_ID]




if __name__ == '__main__':
    person = search_w3_people(query='eric marcoux', rows=1)[0]
    userId = person['uid']
    profile = get_w3_profile(userId)
    print(json.dumps(profile, indent=2))
    team = get_w3_users_team(userId)
    print(json.dumps(team, indent=2))